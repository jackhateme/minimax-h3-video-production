# Prompting for continuity and native dialogue

Compose every H3 prompt from four blocks in this exact order.

## Identity and set invariants

Describe stable visual facts only: adult presenter, face/hair traits, exact wardrobe, set dimensions, recurring props, backdrop, and lighting. Keep this block unchanged across the batch.

## Shot action

Describe one five-second action arc with a starting pose, one focal action, and an ending pose suitable for a cut. State which object stays blank for post typography. Avoid simultaneous complex hand actions.

## Spoken line

Use: `Spoken dialogue, exactly once and exactly as written: "..."`

Spell difficult acronyms as separated letters. Prefer words that cannot be mistaken for product names or technical abbreviations.

## Look and sound invariants

Specify aspect ratio, era, medium, camera behavior, color, image defects, and exclusions. Then describe a natural voice performance and restrained recording defects. Require visible lip/jaw correspondence and prohibit extra dialogue, singing, and generated music.

```text
Native 4:3 low-budget 1980s television commercial recorded with an aging tube camera.
Soft detail, imperfect white balance, blown highlights, coarse tape grain, scanlines,
chroma bleed, slight frame weave, late focus correction and occasional tracking damage.
No modern objects, extra people, readable generated text, logos, subtitles, or watermark.
Generate the quoted English speech with the picture as natural synchronized dialogue through
a cheap mono studio microphone. Mild room reflection, tape hiss and limited bandwidth; never
robotic or vocoded. Match lips and jaw to every word. No extra words, singing, or music.
```

## Continuity controls

- Keep invariant blocks verbatim.
- Use 2–4 approved first-frame anchors and map each shot to one anchor.
- Lock model, encoder, VAEs, sampler, steps, fps, aspect ratio, and megapixel setting.
- Use `base_seed + shot_number` unless a shot explicitly stores another seed.
- Generate typography and end cards in post.
- Apply global film/VHS damage after editing; prompt only enough native degradation to keep sources believable.

When character consistency matters more than action variety, simplify camera motion and preserve a chest-up composition. When action matters more, use a wider matching anchor and accept slightly lower facial fidelity.
