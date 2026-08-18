# Production workflow and acceptance gates

## 1. Preproduction

Create these artifacts in the project folder:

- `project.json`: machine-readable project settings and shot list;
- `script-and-shots.md`: causal spine, beat sheet, dialogue, action, and intended payoff;
- `references/`: approved identity/set anchor frames;
- `generated/`: untouched H3 downloads;
- `work/`: normalized intermediates;
- `output/`: master, delivery, subtitle, and QA report.

Write the ending first when the film depends on a reveal, order card, punchline, or call to action. Trace every earlier beat into that ending. A prop should have one of three jobs: setup, demonstration, or payoff.

## 2. Timing

For a 60-second film, start with 10–12 shots of about five seconds. Reserve the last 2–4 seconds for a legible end card if needed. H3 clip length should match the spoken line rather than forcing long dialogue into a fixed shot.

Use this beat pattern when appropriate:

1. contradiction or hook;
2. promise;
3. structure or choices;
4. evidence for each choice;
5. one complete use-case demonstration;
6. access or purchase path;
7. comedic payoff and call to action.

## 3. Anchor-frame strategy

Approve a small reference set rather than generating every shot from a new image:

- neutral presenter/set frame;
- product/prop frame;
- wide action frame;
- optional end-card design reference.

Crop anchors to the final aspect ratio before upload. Match the anchor to the intended shot size. Repeating wardrobe and set descriptions is necessary even when a first frame is supplied.

## 4. Pilot and batch

Test one shot containing a face, speech, hand action, and recurring prop. Check identity, wardrobe, native dialogue, lip timing, hands, aspect ratio, lighting, and camera treatment. Only then generate the batch.

The batch script skips valid existing outputs, so reruns are resumable. Use `--only N --force` only for a rejected shot.

## 5. Shot QA and repairs

Record each shot as pass, conditional pass, or regenerate. Listen without subtitles once. Watch muted once to evaluate lip sync and visual storytelling. Check the final frames for unstable faces or accidental freeze artifacts.

- Mispronunciation: respell acronyms, replace homophones, shorten the sentence.
- Robotic voice: remove excessive audio adjectives; request natural speech and only mild analog limitations.
- Lip mismatch: shorten dialogue, reduce head turns, keep the face visible, and regenerate picture plus audio together.
- Style drift: reuse the same anchor, invariant prompt, model files, resolution, and seed family.
- Prop mutation: show fewer objects and make only one object active in the shot.
- Weak comedy: make the prop solve or worsen the established problem; remove it if it does neither.

## 6. Finishing and outputs

Finish in this order: normalize; assemble; subtitle; apply one global visual treatment; process dialogue and mix low music/room tone; loudness-normalize; export master; transcode delivery; decode-check both files.

Recommended defaults:

- master: H.264, yuv420p, 24 fps, CRF 10–14, AAC 192 kb/s;
- delivery: H.264, yuv420p, CRF 22–24, AAC 160 kb/s, faststart;
- speech-led online video: approximately -16 LUFS integrated, true peak no higher than -1.5 dBTP;
- subtitles: no more than two English lines plus one Chinese line, with high contrast and safe margins.

For intentional VHS work, verify that faces and subtitles survive platform recompression. Noise that looks attractive in the master can become blocky after upload.

## 7. Final report

Record duration, resolution, frame rate, codecs, bitrates, file sizes, loudness, decode result, known limitations, and which file should be uploaded. Preserve the configuration, accepted seeds, untouched H3 clips, and master.
