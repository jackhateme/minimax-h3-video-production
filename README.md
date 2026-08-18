# minimax-h3-video-production

Produce complete multi-shot videos with a locally deployed MiniMax H3 ComfyUI server:
script logic, shot planning, reference-frame continuity, H3 native synchronized dialogue,
batch generation, bilingual subtitles, optional VHS/retro grading, audio mixing, master and
delivery exports, and technical/creative QA.

This is a **redacted public copy** of the skill used with a local ComfyUI instance.

## Redaction notice

Sensitive information has been removed before publishing:

| File | Redacted value |
|------|----------------|
| `references/project.example.json` → `server_url` | Local LAN IP of the ComfyUI host replaced with `http://HOST:8188` placeholder |

No passwords, API keys, or tokens exist in this skill by design: the skill requires that
credentials never be embedded, and the ComfyUI URL is supplied at runtime via `--server`
or the `H3_COMFY_URL` environment variable.

## Layout

```
SKILL.md                        Skill entry point (workflow, rules, quality gates)
references/
  workflow.md                   Production workflow and acceptance gates
  prompting.md                  Prompting for continuity and native dialogue
  project.example.json          Configuration contract (copy and customize)
agents/
  openai.yaml                   Agent interface metadata
scripts/
  h3_batch.py                   Batch image-to-video generation via ComfyUI HTTP API
  finish_video.py               Assembly, subtitles, grading, mix, export, QA
```

## Usage

```bash
export H3_COMFY_URL="http://HOST:8188"
python3 scripts/h3_batch.py project.json --only 1   # pilot one shot first
python3 scripts/h3_batch.py project.json            # generate the batch
python3 scripts/finish_video.py project.json        # finish + QA
```

Requirements: Python 3, `requests`, Pillow, FFmpeg, FFprobe. Set `subtitle_font_path`
when the system does not provide a CJK font.
