#!/usr/bin/env python3
"""Batch MiniMax H3 image-to-video generation through the ComfyUI HTTP API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    required = ("model", "text_encoder", "video_vae", "audio_vae", "shots")
    missing = [key for key in required if not config.get(key)]
    if missing:
        raise ValueError("Missing configuration keys: " + ", ".join(missing))
    if not isinstance(config["shots"], list) or not config["shots"]:
        raise ValueError("shots must be a non-empty list")
    for index, shot in enumerate(config["shots"], 1):
        for key in ("name", "reference", "action", "dialogue"):
            if not shot.get(key):
                raise ValueError(f"Shot {index} is missing {key}")
    return config


def project_path(config_path: Path, config: dict[str, Any]) -> Path:
    value = config.get("project_root")
    if value:
        return Path(value).expanduser().resolve()
    return config_path.resolve().parent


def find_video(item: Any) -> dict[str, Any] | None:
    if isinstance(item, dict):
        filename = item.get("filename")
        if isinstance(filename, str) and filename.lower().endswith((".mp4", ".mov", ".webm", ".mkv")):
            return item
        for value in item.values():
            found = find_video(value)
            if found:
                return found
    elif isinstance(item, list):
        for value in item:
            found = find_video(value)
            if found:
                return found
    return None


def upload_reference(session: requests.Session, server: str, path: Path) -> str:
    with path.open("rb") as handle:
        response = session.post(
            server + "/upload/image",
            files={"image": (path.name, handle, "image/png")},
            data={"overwrite": "true", "type": "input"},
            timeout=120,
        )
    response.raise_for_status()
    return response.json()["name"]


def make_graph(config: dict[str, Any], prompt: str, name: str, seed: int, image: str, duration: float) -> dict[str, Any]:
    fps = float(config.get("fps", 24))
    return {
        "92": {
            "inputs": {"filename_prefix": f"video/{name}", "format": "auto", "codec": "auto", "video": ["105:91", 0]},
            "class_type": "SaveVideo",
        },
        "115": {
            "inputs": {
                "aspect_ratio": config.get("aspect_ratio", "4:3 (Standard)"),
                "megapixels": float(config.get("megapixels", 0.4)),
                "multiple": 32,
            },
            "class_type": "ResolutionSelector",
        },
        "116": {"inputs": {"image": image, "upload": "image"}, "class_type": "LoadImage"},
        "105:11": {"inputs": {"vae_name": config["video_vae"]}, "class_type": "VAELoader"},
        "105:24": {"inputs": {"vae_name": config["audio_vae"]}, "class_type": "VAELoader"},
        "105:23": {"inputs": {"samples": ["105:14", 0], "vae": ["105:24", 0]}, "class_type": "VAEDecodeAudio"},
        "105:10": {"inputs": {"samples": ["105:14", 0], "vae": ["105:11", 0]}, "class_type": "VAEDecode"},
        "105:17": {"inputs": {"sampler_name": config.get("sampler", "res_multistep")}, "class_type": "KSamplerSelect"},
        "105:9": {
            "inputs": {
                "scheduler": config.get("scheduler", "simple"),
                "steps": int(config.get("steps", 20)),
                "denoise": 1.0,
                "model": ["105:6", 0],
            },
            "class_type": "BasicScheduler",
        },
        "105:14": {
            "inputs": {
                "noise": ["105:15", 0], "guider": ["105:16", 0], "sampler": ["105:17", 0],
                "sigmas": ["105:9", 0], "latent_image": ["105:104", 1],
            },
            "class_type": "SamplerCustomAdvanced",
        },
        "105:16": {"inputs": {"model": ["105:6", 0], "conditioning": ["105:104", 0]}, "class_type": "BasicGuider"},
        "105:6": {"inputs": {"unet_name": config["model"], "weight_dtype": "default"}, "class_type": "UNETLoader"},
        "105:13": {"inputs": {"clip_name": config["text_encoder"], "type": "minimax", "device": "default"}, "class_type": "CLIPLoader"},
        "105:15": {"inputs": {"noise_seed": seed}, "class_type": "RandomNoise"},
        "105:91": {"inputs": {"fps": fps, "bit_depth": 8, "images": ["105:10", 0], "audio": ["105:23", 0]}, "class_type": "CreateVideo"},
        "105:104": {
            "inputs": {
                "prompt": prompt, "width": ["115", 0], "height": ["115", 1],
                "length": ["105:107", 1], "clip": ["105:13", 0], "vae": ["105:11", 0],
                "first_frame": ["116", 0],
            },
            "class_type": "MiniMaxH3ImageToVideo",
        },
        "105:107": {
            "inputs": {
                "expression": f"max(5, round(a * {fps:g})) + (5 - (max(5, round(a * {fps:g})) % 17)) % 17",
                "values.a": ["105:111", 0],
            },
            "class_type": "ComfyMathExpression",
        },
        "105:111": {"inputs": {"value": duration}, "class_type": "PrimitiveFloat"},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--server", help="ComfyUI URL; overrides H3_COMFY_URL and config")
    parser.add_argument("--only", type=int, help="Generate only this 1-based shot number")
    parser.add_argument("--force", action="store_true", help="Replace an existing selected output")
    parser.add_argument("--poll-seconds", type=float, default=10)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    root = project_path(args.config, config)
    reference_dir = root / config.get("reference_dir", "references")
    generated_dir = root / config.get("generated_dir", "generated")
    if args.validate_only:
        print(f"Valid configuration: {len(config['shots'])} shots, project root {root}")
        return 0

    server = (args.server or os.environ.get("H3_COMFY_URL") or config.get("server_url", "")).rstrip("/")
    if not server:
        raise ValueError("Set --server, H3_COMFY_URL, or server_url")
    generated_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    health = session.get(server + "/system_stats", timeout=15)
    health.raise_for_status()

    uploaded: dict[str, str] = {}
    manifest: list[dict[str, Any]] = []
    shots = config["shots"]
    for index, shot in enumerate(shots, 1):
        if args.only is not None and args.only != index:
            continue
        target = generated_dir / f"{shot['name']}.mp4"
        if target.exists() and target.stat().st_size > 100_000 and not args.force:
            print(f"[{index}/{len(shots)}] skip {target.name}")
            continue
        reference = reference_dir / shot["reference"]
        if not reference.is_file():
            raise FileNotFoundError(reference)
        if shot["reference"] not in uploaded:
            uploaded[shot["reference"]] = upload_reference(session, server, reference)

        duration = float(shot.get("duration", config.get("shot_duration", 5.0)))
        seed = int(shot.get("seed", int(config.get("base_seed", 0)) + index))
        prompt = (
            config.get("identity_prompt", "").strip() + "\n\n"
            + f"Action over {duration:g} seconds:\n{shot['action'].strip()}\n\n"
            + f"Spoken dialogue, exactly once and exactly as written: \"{shot['dialogue'].strip()}\"\n\n"
            + config.get("look_prompt", "").strip()
        ).strip()
        graph = make_graph(config, prompt, shot["name"], seed, uploaded[shot["reference"]], duration)
        response = session.post(
            server + "/prompt", json={"prompt": graph, "client_id": "minimax-h3-video-production"}, timeout=60
        )
        response.raise_for_status()
        prompt_id = response.json()["prompt_id"]
        print(f"[{index}/{len(shots)}] queued {shot['name']}: {prompt_id}", flush=True)

        while True:
            history_response = session.get(server + "/history/" + prompt_id, timeout=60)
            history_response.raise_for_status()
            history = history_response.json()
            if prompt_id in history:
                entry = history[prompt_id]
                if entry.get("status", {}).get("status_str") == "error":
                    print(json.dumps(entry, ensure_ascii=False, indent=2), file=sys.stderr)
                    return 1
                video = find_video(entry.get("outputs", {}))
                if not video:
                    raise RuntimeError(f"No video output for {shot['name']}")
                download = session.get(
                    server + "/view",
                    params={"filename": video["filename"], "subfolder": video.get("subfolder", ""), "type": video.get("type", "output")},
                    timeout=300,
                )
                download.raise_for_status()
                target.write_bytes(download.content)
                manifest.append({"index": index, "name": shot["name"], "seed": seed, "prompt_id": prompt_id, "prompt": prompt, "file": str(target)})
                print(f"[{index}/{len(shots)}] saved {target.name} ({target.stat().st_size / 1_000_000:.1f} MB)")
                break
            time.sleep(max(1.0, args.poll_seconds))

    manifest_path = generated_dir / "generation_manifest.json"
    previous = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
    by_name = {item["name"]: item for item in previous if isinstance(item, dict) and item.get("name")}
    by_name.update({item["name"]: item for item in manifest})
    manifest_path.write_text(json.dumps(list(by_name.values()), ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
