---
name: minimax-h3-video-production
description: Produce complete multi-shot videos with a locally deployed MiniMax H3 ComfyUI server, including script logic, shot planning, reference-frame continuity, H3 native synchronized dialogue, batch generation, bilingual subtitles, optional VHS/retro grading, audio mixing, master and delivery exports, and technical/creative QA. Use for requests to turn a script or concept into a 30–90 second H3 video, reproduce the established local H3 production workflow, keep style consistent across generated clips, diagnose lip-sync or robotic audio, or package finished videos for publishing.
---

# MiniMax H3 Video Production

Build the story before generating footage, then use deterministic scripts for generation, finishing, and validation. Treat every generated clip as replaceable; never rebuild accepted shots unnecessarily.

## Workflow

1. Inspect the assignment, reference media, available images, existing clips, fonts, music, and output requirements.
2. Write a one-sentence causal spine. Every prop and joke must either advance the promise, demonstrate it, or pay it off. Remove unexplained objects.
3. Divide the target duration into short H3 shots, normally 4–6 seconds. Give each shot one spoken line, one action beat, and one visual purpose.
4. Define a continuity bible before prompting: identity, wardrobe, set, key props, palette, lens/camera behavior, lighting, medium, aspect ratio, degradation, and audio character.
5. Create 2–4 approved anchor frames. Reuse the closest anchor as the first frame for every shot. Keep all typography blank or illegible during generation and add exact text in post.
6. Copy `references/project.example.json`, customize it, and run `scripts/h3_batch.py`. Generate one representative shot first; approve identity, voice, lip sync, hands, framing, and style before batching.
7. Review each source clip before finishing. Regenerate only failed shots, using `--only` and a changed seed or simplified dialogue/action.
8. Run `scripts/finish_video.py` to normalize, concatenate, subtitle, grade, mix, export, and decode-check the result.
9. Watch the full master at normal speed and inspect cut boundaries, subtitle safe areas, last-frame behavior, and audio transitions. Then inspect the delivery file after platform-like compression.

Read [workflow.md](references/workflow.md) for acceptance gates, failure recovery, and publishing outputs. Read [prompting.md](references/prompting.md) when designing prompts or repairing cross-shot inconsistency. Read [project.example.json](references/project.example.json) as the configuration contract.

## Generation rules

- Keep dialogue short enough for the shot. Prefer one natural sentence under roughly 14 English words per five seconds.
- Ask H3 to generate the picture and quoted dialogue together. Require the line exactly once, with no extra speech, singing, or music.
- Describe voice characteristics, recording chain, and performance energy. Do not depend on post-generated speech for visible talking shots.
- Separate invariant prompt text from per-shot action. Repeat invariants verbatim across all shots.
- Lock model files, workflow nodes, resolution, fps, steps, sampler, wardrobe, anchors, and recurring props for the full batch.
- Use deterministic seeds. Record every accepted seed and prompt in the project configuration.
- Never embed passwords in the skill or configuration. Accept the ComfyUI URL from `--server` or `H3_COMFY_URL`. If remote access needs SSH, request credentials at runtime and do not persist them.
- Do not shut down the generation host until all downloads, checksums, and final exports are complete.

## Quality gates

Reject and regenerate a shot when any of these materially harms comprehension:

- missing, duplicated, or mispronounced dialogue;
- robotic/vocoded sound when natural speech was requested;
- lips clearly disagree with the generated speech;
- identity, wardrobe, set, aspect ratio, or key prop drifts;
- extra people, modern objects, invented readable text, logos, or watermarks appear;
- a joke introduces a prop without setup or payoff;
- hands or foreground objects fail during the focal action.

Prefer rewriting ambiguous dialogue over audio surgery. Spell initials separately when needed, replace easily confused words, and reduce simultaneous action during dense lines.

## Finishing rules

- Normalize every source clip before concatenation; do not rely on mixed resolutions or time bases.
- Preserve H3's native synchronized dialogue. Apply only restrained EQ, compression, noise, room tone, and loudness normalization.
- Keep music well below speech. Avoid heavy denoising that creates metallic or robotic artifacts.
- Place bilingual subtitles in a shallow safe-area band. Do not cover the face, hands, CRT, or story-critical props.
- For 4:3 work, retain a true 4:3 master unless the publishing platform explicitly requires a 16:9 container.
- Render retro damage after editorial assembly so all shots share the same scanlines, noise, chroma behavior, and tracking defects.
- Export a high-quality master and a smaller delivery copy. Upload the master when the platform will transcode again.

## Commands

```bash
export H3_COMFY_URL="http://HOST:8188"
python3 scripts/h3_batch.py project.json --only 1
python3 scripts/h3_batch.py project.json
python3 scripts/finish_video.py project.json
```

Run from the skill directory or use absolute paths. The scripts require Python 3, `requests`, Pillow, FFmpeg, and FFprobe. Set `subtitle_font_path` when the system does not provide a CJK font.
