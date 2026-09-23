import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_comfyui.py"
spec = importlib.util.spec_from_file_location("run_comfyui", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
WORKFLOW = json.loads((Path(__file__).resolve().parents[1] / "assets" / "comfyui-qwen-image-2.1-t2i.json").read_text())


class ComfyClientTests(unittest.TestCase):
    def args(self):
        return argparse.Namespace(prompt="A blue cup.", negative_prompt="", reference_resolution=1024, width=1152, height=2048, steps=25, seed=7, cfg=1.0, sampler="euler", scheduler="simple", prefix="test", unet="u.safetensors", clip="c.safetensors", vae="v.safetensors")

    def test_configures_prompt_canvas_models_and_sampling(self):
        configured = module.configure_workflow(WORKFLOW, self.args())
        self.assertEqual(configured["4"]["inputs"]["prompt"], "A blue cup.")
        self.assertEqual((configured["5"]["inputs"]["width"], configured["5"]["inputs"]["height"]), (1152, 2048))
        self.assertEqual(configured["6"]["inputs"]["seed"], 7)
        self.assertEqual(configured["1"]["inputs"]["unet_name"], "u.safetensors")
        self.assertEqual(WORKFLOW["5"]["inputs"]["width"], 1024)

    def test_preflight_rejects_missing_model_before_submission(self):
        configured = module.configure_workflow(WORKFLOW, self.args())
        def info(_base, node):
            fields = {"UNETLoader": ("unet_name", ["other.safetensors"]), "CLIPLoader": ("clip_name", ["c.safetensors"]), "VAELoader": ("vae_name", ["v.safetensors"])}
            if node in fields:
                name, values = fields[node]
                return {"input": {"required": {name: [values]}}}
            return {"input": {"required": {}}}
        with patch.object(module, "node_info", side_effect=info):
            with self.assertRaisesRegex(module.ComfyError, "Model not found"):
                module.preflight("http://local", configured)

    def test_download_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "image.png"
            target.write_bytes(b"existing")
            with self.assertRaisesRegex(module.ComfyError, "Refusing to overwrite"):
                module.download_image("http://local", {"filename": "image.png", "subfolder": "", "type": "output"}, Path(directory))


if __name__ == "__main__":
    unittest.main(verbosity=2)
