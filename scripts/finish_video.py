#!/usr/bin/env python3
"""Assemble H3 clips, burn bilingual subtitles, grade, mix, export, and QA."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


def run(command: list[str], capture: bool = False) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(command), flush=True)
    return subprocess.run(command, check=True, text=True, capture_output=capture)


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    for key in ("width", "height", "fps", "shots"):
        if not config.get(key):
            raise ValueError(f"Missing configuration key: {key}")
    if not isinstance(config["shots"], list) or not config["shots"]:
        raise ValueError("shots must be a non-empty list")
    return config


def root_path(config_path: Path, config: dict[str, Any]) -> Path:
    return Path(config.get("project_root", config_path.parent)).expanduser().resolve()


def find_font(config: dict[str, Any]) -> Path:
    configured = config.get("subtitle_font_path")
    candidates = [
        Path(configured).expanduser() if configured else None,
        Path("/System/Library/Fonts/PingFang.ttc"),
        Path("/System/Library/Fonts/STHeiti Medium.ttc"),
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            return candidate
    raise FileNotFoundError("Set subtitle_font_path to a TrueType/OpenType font, preferably one with CJK glyphs")


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int, max_lines: int) -> list[str]:
    if not text:
        return []
    tokens = text.split() if " " in text else list(text)
    separator = " " if " " in text else ""
    lines: list[str] = []
    current = ""
    for token in tokens:
        candidate = token if not current else current + separator + token
        box = draw.textbbox((0, 0), candidate, font=font, stroke_width=1)
        if current and box[2] - box[0] > max_width:
            lines.append(current)
            current = token
        else:
            current = candidate
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(" .，。") + "…"
    return lines


def centered_text(draw: ImageDraw.ImageDraw, y: int, text: str, font: ImageFont.FreeTypeFont, fill: tuple[int, int, int, int]) -> None:
    box = draw.textbbox((0, 0), text, font=font, stroke_width=2)
    x = (draw._image.size[0] - (box[2] - box[0])) // 2
    draw.text((x, y), text, font=font, fill=fill, stroke_width=2, stroke_fill=(0, 0, 0, 235))


def make_subtitle_cards(config: dict[str, Any], directory: Path) -> list[tuple[Path, float, float]]:
    width, height = int(config["width"]), int(config["height"])
    font_path = find_font(config)
    english_font = ImageFont.truetype(str(font_path), size=max(14, round(height * 0.026)))
    chinese_font = ImageFont.truetype(str(font_path), size=max(15, round(height * 0.029)))
    band_height = max(58, round(height * 0.16))
    cards: list[tuple[Path, float, float]] = []
    cursor = 0.0
    for index, shot in enumerate(config["shots"], 1):
        duration = float(shot.get("duration", config.get("shot_duration", 5.0)))
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image, "RGBA")
        top = height - band_height
        draw.rectangle((0, top, width, height), fill=(0, 0, 0, 178))
        english_lines = wrap_text(draw, str(shot.get("dialogue", "")), english_font, round(width * 0.90), 2)
        chinese_lines = wrap_text(draw, str(shot.get("chinese", "")), chinese_font, round(width * 0.90), 1)
        english_step = max(17, round(height * 0.032))
        start_y = top + max(5, round(height * 0.008))
        for line_index, line in enumerate(english_lines):
            centered_text(draw, start_y + line_index * english_step, line, english_font, (245, 245, 238, 255))
        if chinese_lines:
            centered_text(draw, height - max(22, round(height * 0.040)), chinese_lines[0], chinese_font, (255, 220, 75, 255))
        path = directory / f"subtitle_{index:03d}.png"
        image.save(path)
        cards.append((path, cursor, cursor + duration))
        cursor += duration
    return cards


def grade_filter(config: dict[str, Any]) -> str:
    width, height = int(config["width"]), int(config["height"])
    grade = config.get("grade", "none")
    if grade == "none":
        return "format=yuv420p"
    low_width = int(config.get("vhs_low_width", 384 if width * 3 == height * 4 else 480))
    low_height = max(2, round((low_width * height / width) / 2) * 2)
    if grade == "vhs-light":
        return (
            f"scale={low_width}:{low_height}:flags=bilinear,scale={width}:{height}:flags=bilinear,"
            "eq=contrast=0.96:saturation=0.82:gamma=1.02,noise=alls=7:allf=t+u,"
            "drawgrid=w=iw:h=4:t=1:c=black@0.12,vignette=PI/6,format=yuv420p"
        )
    if grade == "vhs-heavy":
        return (
            f"scale={low_width}:{low_height}:flags=bilinear,gblur=sigma=0.65,"
            f"scale={width}:{height}:flags=bilinear,eq=contrast=0.92:saturation=0.72:gamma=1.04,"
            "noise=alls=13:allf=t+u,tblend=all_mode=average:all_opacity=0.10,"
            "drawgrid=w=iw:h=4:t=1:c=black@0.19,vignette=PI/5,format=yuv420p"
        )
    raise ValueError(f"Unknown grade: {grade}")


def probe(path: Path) -> dict[str, Any]:
    result = run([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration,size,bit_rate:stream=index,codec_name,codec_type,width,height,r_frame_rate,bit_rate,sample_rate,channels",
        "-of", "json", str(path),
    ], capture=True)
    return json.loads(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    root = root_path(args.config, config)
    if args.validate_only:
        print(f"Valid finishing configuration: {len(config['shots'])} shots, {config['width']}x{config['height']} at {config['fps']} fps")
        return 0

    generated = root / config.get("generated_dir", "generated")
    work = root / config.get("work_dir", "work")
    output = root / config.get("output_dir", "output")
    work.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    width, height, fps = int(config["width"]), int(config["height"]), float(config["fps"])

    sources = [generated / f"{shot['name']}.mp4" for shot in config["shots"]]
    missing = [str(path) for path in sources if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing generated clips:\n" + "\n".join(missing))

    inputs: list[str] = []
    filter_parts: list[str] = []
    concat_labels: list[str] = []
    total_duration = 0.0
    for index, (shot, source) in enumerate(zip(config["shots"], sources)):
        duration = float(shot.get("duration", config.get("shot_duration", 5.0)))
        total_duration += duration
        inputs += ["-i", str(source)]
        filter_parts.append(
            f"[{index}:v]fps={fps:g},scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},trim=duration={duration:g},setpts=PTS-STARTPTS[v{index}]"
        )
        filter_parts.append(
            f"[{index}:a]aresample=48000,apad,atrim=duration={duration:g},asetpts=PTS-STARTPTS[a{index}]"
        )
        concat_labels.append(f"[v{index}][a{index}]")
    filter_parts.append("".join(concat_labels) + f"concat=n={len(sources)}:v=1:a=1[v][a]")
    edit = work / "assembled_native.mp4"
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", *inputs,
        "-filter_complex", ";".join(filter_parts), "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p",
        "-r", f"{fps:g}", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-t", f"{total_duration:.3f}", "-movflags", "+faststart", "-y", str(edit),
    ])

    subtitle_cards = make_subtitle_cards(config, work)
    master = output / config.get("master_name", "video_master.mp4")
    delivery = output / config.get("delivery_name", "video_delivery.mp4")
    music_value = config.get("music")
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(edit)]
    music_index: int | None = None
    if music_value:
        music = root / music_value
        if not music.is_file():
            raise FileNotFoundError(music)
        music_index = 1
        command += ["-stream_loop", "-1", "-i", str(music)]
    first_card_index = 2 if music_index is not None else 1
    for path, _, _ in subtitle_cards:
        command += ["-loop", "1", "-framerate", f"{fps:g}", "-i", str(path)]
    noise_index = first_card_index + len(subtitle_cards)
    command += ["-f", "lavfi", "-i", f"anoisesrc=color=pink:amplitude=0.006:r=48000:d={total_duration:g}"]

    video_parts = [f"[0:v]{grade_filter(config)}[vg0]"]
    for index, (_, start, end) in enumerate(subtitle_cards):
        card_index = first_card_index + index
        video_parts.append(
            f"[vg{index}][{card_index}:v]overlay=0:0:enable='between(t,{start:.3f},{max(start, end - 0.001):.3f})'[vg{index + 1}]"
        )
    video_output = f"[vg{len(subtitle_cards)}]"
    audio_parts = [
        f"[0:a]pan=mono|c0=0.5*c0+0.5*c1,highpass=f=90,lowpass=f=11000,"
        f"acompressor=threshold=0.12:ratio=2.4:attack=7:release=80:makeup=1.25[voice]",
        f"[{noise_index}:a]lowpass=f=6500,volume={float(config.get('hiss_volume', 0.03)):g}[hiss]",
    ]
    mix_labels = "[voice]"
    mix_count = 2
    if music_index is not None:
        audio_parts.append(f"[{music_index}:a]volume={float(config.get('music_volume', 0.10)):g}[music]")
        mix_labels += "[music]"
        mix_count += 1
    mix_labels += "[hiss]"
    audio_parts.append(
        mix_labels + f"amix=inputs={mix_count}:duration=first:normalize=0,"
        f"alimiter=limit=0.95,loudnorm=I={float(config.get('dialogue_lufs', -16)):g}:TP=-1.5:LRA=8[a]"
    )
    run(command + [
        "-filter_complex", ";".join(video_parts + audio_parts),
        "-map", video_output, "-map", "[a]", "-c:v", "libx264", "-preset", "slow",
        "-crf", str(config.get("master_crf", 12)), "-pix_fmt", "yuv420p", "-r", f"{fps:g}",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-t", f"{total_duration:.3f}", "-movflags", "+faststart",
        "-metadata", f"title={config.get('title', 'MiniMax H3 video')}", "-y", str(master),
    ])
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(master),
        "-c:v", "libx264", "-preset", "slow", "-crf", str(config.get("delivery_crf", 23)),
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
        "-movflags", "+faststart", "-y", str(delivery),
    ])

    report: dict[str, Any] = {"master": probe(master), "delivery": probe(delivery), "decode": {}}
    for name, path in (("master", master), ("delivery", delivery)):
        result = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"],
            text=True, capture_output=True,
        )
        report["decode"][name] = {"ok": result.returncode == 0, "errors": result.stderr.strip()}
        if result.returncode != 0:
            raise RuntimeError(f"Decode check failed for {path}: {result.stderr}")
    report_path = output / "qa_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Master: {master}\nDelivery: {delivery}\nQA: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
