#!/usr/bin/env python3
"""Submit the bundled Qwen Image 2.1 workflow to a local ComfyUI server."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKFLOW = SKILL_ROOT / "assets" / "comfyui-qwen-image-2.1-t2i.json"
REQUIRED_NODES = {
    "UNETLoader", "CLIPLoader", "VAELoader", "TextEncodeQwenImage21",
    "EmptyLatentImage", "KSampler", "VAEDecode", "SaveImage",
}


class ComfyError(RuntimeError):
    pass


def json_request(base_url: str, path: str, payload: dict | None = None) -> dict:
    url = base_url.rstrip("/") + path
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise ComfyError(f"ComfyUI request failed for {url}: {error}") from error


def node_info(base_url: str, node: str) -> dict:
    data = json_request(base_url, "/object_info/" + urllib.parse.quote(node))
    if node not in data:
        raise ComfyError(f"Required ComfyUI node is unavailable: {node}")
    return data[node]


def combo_values(info: dict, input_name: str) -> list[str]:
    spec = info.get("input", {}).get("required", {}).get(input_name)
    if not isinstance(spec, list) or not spec:
        return []
    return spec[0] if isinstance(spec[0], list) else []


def preflight(base_url: str, workflow: dict) -> None:
    classes = {node.get("class_type") for node in workflow.values()}
    missing = REQUIRED_NODES - classes
    if missing:
        raise ComfyError("Workflow is missing required nodes: " + ", ".join(sorted(missing)))
    infos = {name: node_info(base_url, name) for name in REQUIRED_NODES}
    checks = (
        ("UNETLoader", "unet_name", workflow["1"]["inputs"]["unet_name"]),
        ("CLIPLoader", "clip_name", workflow["2"]["inputs"]["clip_name"]),
        ("VAELoader", "vae_name", workflow["3"]["inputs"]["vae_name"]),
    )
    for node, field, selected in checks:
        available = combo_values(infos[node], field)
        if available and selected not in available:
            raise ComfyError(f"Model not found for {node}.{field}: {selected}. Choose one of: {', '.join(available)}")


def configure_workflow(workflow: dict, args: argparse.Namespace) -> dict:
    configured = json.loads(json.dumps(workflow))
    configured["1"]["inputs"]["unet_name"] = args.unet
    configured["2"]["inputs"]["clip_name"] = args.clip
    configured["3"]["inputs"]["vae_name"] = args.vae
    configured["4"]["inputs"].update(prompt=args.prompt, negative_prompt=args.negative_prompt, resolution=args.reference_resolution)
    configured["5"]["inputs"].update(width=args.width, height=args.height)
    configured["6"]["inputs"].update(seed=args.seed, steps=args.steps, cfg=args.cfg, sampler_name=args.sampler, scheduler=args.scheduler)
    configured["8"]["inputs"]["filename_prefix"] = args.prefix
    return configured


def wait_for_result(base_url: str, prompt_id: str, poll: float, timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        record = json_request(base_url, "/history/" + urllib.parse.quote(prompt_id)).get(prompt_id)
        if record and record.get("status", {}).get("completed"):
            return record
        time.sleep(poll)
    raise ComfyError(f"Timed out waiting for ComfyUI prompt {prompt_id}")


def download_image(base_url: str, image: dict, destination: Path) -> Path:
    target = destination / Path(image["filename"]).name
    if target.exists():
        raise ComfyError(f"Refusing to overwrite existing file: {target}")
    query = urllib.parse.urlencode({"filename": image["filename"], "subfolder": image.get("subfolder", ""), "type": image.get("type", "output")})
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/view?" + query, timeout=120) as response:
            raw = response.read()
    except (urllib.error.URLError, TimeoutError) as error:
        raise ComfyError(f"Could not download {image['filename']}: {error}") from error
    destination.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return target


def build_parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("prompt", help="Final visible-image prompt")
    result.add_argument("--server", default=os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188"))
    result.add_argument("--workflow", type=Path, default=DEFAULT_WORKFLOW)
    result.add_argument("--output-dir", type=Path, help="Download outputs through /view")
    result.add_argument("--record", type=Path, help="Write a JSON generation record")
    result.add_argument("--width", type=int, default=1024)
    result.add_argument("--height", type=int, default=1024)
    result.add_argument("--steps", type=int, default=25)
    result.add_argument("--seed", type=int, default=secrets.randbelow(2**53))
    result.add_argument("--cfg", type=float, default=1.0)
    result.add_argument("--sampler", default="euler")
    result.add_argument("--scheduler", default="simple")
    result.add_argument("--negative-prompt", default="")
    result.add_argument("--reference-resolution", type=int, default=1024)
    result.add_argument("--prefix", default="qwen_image_2.1_skill")
    result.add_argument("--unet", default="qwen_image_2.1_int8_convrot.safetensors")
    result.add_argument("--clip", default="qwen3vl_8b_int8_convrot.safetensors")
    result.add_argument("--vae", default="qwen_image_2.1_vae_bf16.safetensors")
    result.add_argument("--poll-seconds", type=float, default=3.0)
    result.add_argument("--timeout-seconds", type=float, default=3600.0)
    result.add_argument("--skip-preflight", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.width < 64 or args.height < 64 or args.width % 32 or args.height % 32:
        raise ComfyError("Width and height must be at least 64 and multiples of 32")
    if not 1 <= args.steps <= 1000:
        raise ComfyError("Steps must be between 1 and 1000")
    if not 0 <= args.seed < 2**53:
        raise ComfyError("Seed must be between 0 and 2^53-1")
    if args.record and args.record.exists():
        raise ComfyError(f"Refusing to overwrite existing record: {args.record}")

    workflow = configure_workflow(json.loads(args.workflow.read_text(encoding="utf-8")), args)
    if not args.skip_preflight:
        preflight(args.server, workflow)
    queued = json_request(args.server, "/prompt", {"prompt": workflow, "client_id": "qwen-image-gen-skill"})
    if queued.get("node_errors"):
        raise ComfyError(json.dumps(queued["node_errors"], ensure_ascii=False, indent=2))
    prompt_id = queued.get("prompt_id")
    if not prompt_id:
        raise ComfyError("ComfyUI accepted no prompt_id")
    print(json.dumps({"status": "queued", "prompt_id": prompt_id}, ensure_ascii=False))

    history = wait_for_result(args.server, prompt_id, args.poll_seconds, args.timeout_seconds)
    status = history.get("status", {}).get("status_str", "unknown")
    images = [image for output in history.get("outputs", {}).values() for image in output.get("images", [])]
    downloaded = [str(download_image(args.server, image, args.output_dir)) for image in images] if args.output_dir else []
    record = {
        "status": status, "prompt_id": prompt_id, "server": args.server,
        "images": images, "downloaded": downloaded,
        "settings": {"width": args.width, "height": args.height, "steps": args.steps, "seed": args.seed, "cfg": args.cfg, "sampler": args.sampler, "scheduler": args.scheduler, "unet": args.unet, "clip": args.clip, "vae": args.vae},
        "submitted_prompt": args.prompt,
    }
    if args.record:
        args.record.parent.mkdir(parents=True, exist_ok=True)
        args.record.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0 if status == "success" and images else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ComfyError, OSError, KeyError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
