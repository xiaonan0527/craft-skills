# Local ComfyUI execution

Use this integration only when the user requests generation through a local or otherwise user-controlled ComfyUI server. Prompt-only tasks do not need a server.

## Supported path

The bundled client covers Qwen Image 2.1 text-to-image with API-format JSON and these ComfyUI nodes:

`UNETLoader` → `CLIPLoader` → `TextEncodeQwenImage21` → `EmptyLatentImage` → `KSampler` → `VAEDecode` → `SaveImage`.

The client calls `/object_info/<node>` before generation, submits `/prompt`, follows the same `prompt_id` through `/history/<prompt_id>`, and can download original outputs through `/view`. It uses only Python's standard library.

Reference-image editing is not bundled. The Qwen node may expose reference-image inputs, but edit sizing and latent behavior depend on the actual workflow. Inspect and adapt the user's exported API workflow instead of silently treating it as text-to-image.

## Run

ComfyUI commonly uses port 8188. Override it with `COMFYUI_URL` or `--server`:

```sh
export COMFYUI_URL=http://127.0.0.1:8188
python3 scripts/run_comfyui.py \
  "A full-length fashion portrait at blue hour." \
  --width 1152 --height 2048 --steps 25 \
  --output-dir ./outputs --record ./outputs/run.json
```

For a non-default local port:

```sh
python3 scripts/run_comfyui.py "A ceramic cup." \
  --server http://127.0.0.1:8000 --width 512 --height 512 --steps 4
```

Use low steps only for a connectivity test. Preserve the user's working sampler and model filenames when known. Override filenames with `--unet`, `--clip`, and `--vae`; preflight fails before submission if ComfyUI reports that a selected model is unavailable.

`--output-dir` downloads images without assuming the server's filesystem layout. Existing local files and records are not overwritten. When a request times out or its result is uncertain, query the recorded `prompt_id`; do not resubmit automatically.

## Custom workflows

`--workflow` accepts another API-format JSON file, but the current client expects the same stable node IDs as the bundled template for parameter injection. To support a materially different graph, copy and adapt the client rather than renaming arbitrary nodes by guesswork.
