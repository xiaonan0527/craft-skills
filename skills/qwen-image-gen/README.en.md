# Qwen Image Gen

[简体中文](README.md) | [English](README.en.md) · [Craft Skills](../../README.en.md)

**Help your deployed Qwen-Image understand what to draw and what to change.**

An experimental Agent workflow for an existing Qwen-Image setup: preserve user intent, distinguish local edits from reference-guided creation, translate aspect-ratio decisions into backend parameters, and inspect actual outputs.

**v0.3.0 experimental.** Your current Agent performs the rewrite. The package includes an optional local ComfyUI Qwen Image 2.1 text-to-image client; it still requires your own models and running ComfyUI server.

## Images and their prompts

| Rooftop satin | Strawberry cake | Noir portrait |
| --- | --- | --- |
| [![Rooftop satin](assets/examples/portraits/rooftop-green.png)](assets/examples/portraits/rooftop-green.png) | [![Strawberry cake](assets/examples/portraits/strawberry-cake.png)](assets/examples/portraits/strawberry-cake.png) | [![Noir portrait](assets/examples/portraits/noir-portrait.png)](assets/examples/portraits/noir-portrait.png) |
| [Prompt](assets/examples/portraits/rooftop-green.txt) | [Prompt](assets/examples/portraits/strawberry-cake.txt) | [Prompt](assets/examples/portraits/noir-portrait.txt) |

Local Qwen-Image text-to-image samples, each **1152×2048**, depicting fictional adults. Click for full-size images. [Generation records](assets/examples/portraits/manifest.json). These illustrate subjects and visual styles; controlled rewrite comparisons appear below.

## What it does

| Request | Workflow |
| --- | --- |
| Text-to-image and posters | Preserve subjects, actions and exact lettering; separate instructions from visible text |
| Local edits | Specify the change and the content that must remain |
| New poses or scenes | Preserve reference identity while allowing limbs, shoulders and clothing to move |
| Character series | Start from an accepted identity reference; one action and a complete prompt per image |
| Automatic aspect ratio | Choose a suitable composition, then pass actual supported canvas parameters |
| Quality corrections | Separate structural defects from taste; preserve originals and revised versions |

## Install and try

First installation in Codex; back up customizations if the destination already exists:

```sh
git clone https://github.com/ZSeven-W/craft-skills.git
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R craft-skills/skills/qwen-image-gen "${CODEX_HOME:-$HOME/.codex}/skills/"
```

Reload the Agent session and invoke `$qwen-image-gen`. Other Skill-capable agents can use their own skills directory. Prompt-only use needs no image-generation connection. For actual generation, connect your existing Qwen workflow and keep credentials in local configuration, outside prompts and source files.

```text
Use $qwen-image-gen to prepare a 3:4 tea poster prompt. Preserve the exact
Chinese headline and price. Return a prompt and canvas decision; do not generate.
```

```text
Use $qwen-image-gen to turn the reference person into a front-facing standing pose.
Preserve identity, outfit and setting. Allow shoulders, arms and fabric folds to
change with the pose. Inspect the reference before writing the edit.
```

```text
Use $qwen-image-gen to create three separate 9:16 cafe portraits from this identity
reference: seated facing camera, side-on by a window, and standing holding a cup.
Generate through my configured Qwen workflow. Save each submitted prompt,
generation settings and original output for review.
```

## Before and after rewriting

| Poster: original prompt | Poster: rewritten prompt |
| --- | --- |
| [![Original poster](assets/examples/ab/poster-A.png)](assets/examples/ab/poster-A.png) | [![Rewritten poster](assets/examples/ab/poster-B.png)](assets/examples/ab/poster-B.png) |

| Reaching for a jar: original prompt | Reaching for a jar: rewritten prompt |
| --- | --- |
| [![Original reach](assets/examples/ab/reach-A.png)](assets/examples/ab/reach-A.png) | [![Rewritten reach](assets/examples/ab/reach-B.png)](assets/examples/ab/reach-B.png) |

Research used an existing language model with public Qwen PE templates, keeping seed, steps, canvas and references fixed. Poster lettering, full-body framing and the jar/shelf relationship improved in three examples; **the backwards-stool pose still failed**. [All four comparisons](assets/examples/ab/README.md) · [Both prompts and parameters](assets/examples/ab/cases.json).

These research examples informed the Skill. They do not establish a general win rate for the final Skill or reproduce official PE weights. The package passed 22 code tests and eight offline Agent trials; a fresh image-level Skill comparison remains pending.

## Workflow and integration

Request → task selection → prompt and canvas decision → existing Qwen workflow → original-output inspection → defect-guided revision.

The current Agent rewrites prompts; reference tasks need visual understanding. No additional large model download is required. Application developers may use the optional offline request builder or shared runtime.

For local ComfyUI text-to-image, use `scripts/run_comfyui.py`. It preflights nodes and model filenames, submits the API workflow, follows the same task ID, and can download original outputs through `/view`. Configure the server with `COMFYUI_URL` or `--server`; see [Local ComfyUI execution](references/comfyui-local.md).

## Documentation and limits

- [English guide](../../docs/qwen-image-gen.md)
- [Workflow](SKILL.md)
- [Controlled research examples](assets/examples/ab/README.md)
- [Portrait examples and prompts](assets/examples/portraits/README.md)
- [Validation scope](../../evals/qwen-image-gen/VALIDATION.md)
- [Optional application runtime](references/shared-runtime.md) (Node.js 18+, offline)

The optional Python request builder is offline and targets one specific workbench protocol. Its limits are not universal Qwen limits. Official PE weights and full system prompts are not redistributed. Anatomical correctness and identity retention still require output inspection.
