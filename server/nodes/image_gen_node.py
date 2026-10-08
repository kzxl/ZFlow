"""
AI Image Generator Node (Flux, SDXL, DALL-E 3 & ComfyUI Local Bridge).
Generates high-resolution images from text prompts with support for
cloud diffusion APIs and local ComfyUI WebSocket/REST servers.
"""
from typing import Dict, Any, List, Optional
import json
import os
import time
import random
import urllib.request
import urllib.parse
import urllib.error
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext

ASPECT_RATIO_DIMENSIONS: Dict[str, tuple[int, int]] = {
    "1:1": (1024, 1024),
    "16:9": (1344, 768),
    "9:16": (768, 1344),
    "4:3": (1152, 864),
    "3:2": (1216, 832)
}


@NodeRegistry.register
class ImageGenNode(BaseNode):
    node_type = "image_gen"
    name = "AI Image Generator"
    category = "media"
    description = "Tạo ảnh nghệ thuật AI chất lượng cao (Hỗ trợ DALL-E 3, Flux.1, SDXL, kết nối ComfyUI Local hoặc Simulator 0đ)."
    icon = "Image"

    inputs = [
        PortDef(name="prompt", data_type="string", label="Positive Prompt", required=True),
        PortDef(name="negative_prompt", data_type="string", label="Negative Prompt", required=False),
        PortDef(name="aspect_ratio", data_type="string", label="Aspect Ratio (1:1, 16:9...)", required=False)
    ]
    outputs = [
        PortDef(name="image_url", data_type="string", label="Generated Image URL"),
        PortDef(name="markdown_image", data_type="string", label="Markdown Image Syntax"),
        PortDef(name="revised_prompt", data_type="string", label="Revised Prompt"),
        PortDef(name="seed", data_type="number", label="Random Seed"),
        PortDef(name="aspect_ratio", data_type="string", label="Aspect Ratio"),
        PortDef(name="width", data_type="number", label="Image Width (px)"),
        PortDef(name="height", data_type="number", label="Image Height (px)"),
        PortDef(name="status", data_type="string", label="Generation Status")
    ]

    config_schema = {
        "provider": {
            "type": "select",
            "label": "Generation Provider",
            "options": ["simulator", "dalle3", "comfyui_local", "flux_pollinations"],
            "default": "simulator"
        },
        "aspect_ratio": {
            "type": "select",
            "label": "Default Aspect Ratio",
            "options": ["1:1", "16:9", "9:16", "4:3", "3:2"],
            "default": "1:1"
        },
        "comfyui_base_url": {
            "type": "string",
            "label": "ComfyUI Server Address",
            "default": "http://127.0.0.1:8188"
        },
        "quality": {
            "type": "select",
            "label": "Image Quality (DALL-E 3)",
            "options": ["standard", "hd"],
            "default": "standard"
        },
        "api_key": {
            "type": "password",
            "label": "API Key (or env OPENAI_API_KEY)",
            "default": ""
        }
    }

    async def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        prompt = str(
            inputs.get("prompt")
            or inputs.get("positive_prompt")
            or context.get_variable("positive_prompt")
            or context.get_variable("prompt")
            or context.get_variable("input", "")
        ).strip()

        neg_prompt = str(
            inputs.get("negative_prompt")
            or context.get_variable("negative_prompt", "")
        ).strip()

        ratio = str(inputs.get("aspect_ratio") or config.get("aspect_ratio", "1:1"))
        width, height = ASPECT_RATIO_DIMENSIONS.get(ratio, (1024, 1024))
        provider = config.get("provider", "simulator")
        config_seed = config.get("seed", -1)
        try:
            seed = int(config_seed) if int(config_seed) > 0 else random.randint(100000, 999999999)
        except (ValueError, TypeError):
            seed = random.randint(100000, 999999999)

        api_key = config.get("api_key") or os.environ.get("OPENAI_API_KEY", "")

        image_url = ""
        revised_prompt = prompt
        status = "success"

        # 1. DALL-E 3 Mode
        if provider == "dalle3" and api_key:
            try:
                image_url, revised_prompt = await self._generate_dalle3(prompt, ratio, config, api_key)
            except Exception as e:
                context.log("error", f"DALL-E 3 error: {e}, falling back to High-res Simulator.")
                image_url = self._generate_simulator(prompt, width, height, seed)
        # 2. Local ComfyUI Bridge
        elif provider == "comfyui_local":
            try:
                base_url = config.get("comfyui_base_url", "http://127.0.0.1:8188")
                image_url = await self._generate_comfyui_bridge(prompt, neg_prompt, width, height, seed, base_url)
            except Exception as e:
                context.log("error", f"ComfyUI bridge error: {e}, falling back to High-res Simulator.")
                image_url = self._generate_simulator(prompt, width, height, seed)
        # 3. Flux / Pollinations AI
        elif provider == "flux_pollinations":
            encoded_prompt = urllib.parse.quote(prompt)
            image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&seed={seed}&nologo=true&model=flux"
        # 4. Default Simulator (Fast, reliable, zero-config)
        else:
            image_url = self._generate_simulator(prompt, width, height, seed)

        # Record in context variables
        context.set_variable("image_url", image_url)
        context.set_variable("image_seed", seed)
        context.set_variable("image_markdown", f"![{prompt[:30]}]({image_url})")
        context.log("info", f"Generated image with seed {seed}: {image_url}")

        return {
            "image_url": image_url,
            "markdown_image": f"![Generated Image: {prompt[:30]}]({image_url})",
            "markdown": f"![Generated Image: {prompt[:30]}]({image_url})",
            "revised_prompt": revised_prompt,
            "seed": seed,
            "aspect_ratio": ratio,
            "width": width,
            "height": height,
            "is_mock": provider in ("simulator", "comfyui_local"),
            "status": status
        }

    def _generate_simulator(self, prompt: str, width: int, height: int, seed: int) -> str:
        """
        Generates realistic high-res AI image link matching keywords from prompt.
        """
        # Encode clean prompt for AI CDN or Pollinations Flux
        clean_prompt = prompt.replace("\n", " ").strip()
        encoded = urllib.parse.quote(clean_prompt[:150])
        # Pollinations Flux AI CDN endpoint (free, unlimited, instant)
        return f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&seed={seed}&nologo=true&model=flux"

    async def _generate_dalle3(self, prompt: str, ratio: str, config: Dict[str, Any], api_key: str) -> tuple[str, str]:
        size_map = {
            "1:1": "1024x1024",
            "16:9": "1792x1024",
            "9:16": "1024x1792"
        }
        req_size = size_map.get(ratio, "1024x1024")
        quality = config.get("quality", "standard")

        payload = {
            "model": "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": req_size,
            "quality": quality
        }

        req = urllib.request.Request(
            "https://api.openai.com/v1/images/generations",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            item = data["data"][0]
            return item.get("url", ""), item.get("revised_prompt", prompt)

    async def _generate_comfyui_bridge(
        self, prompt: str, neg_prompt: str, width: int, height: int, seed: int, base_url: str
    ) -> str:
        """
        Communicates with local ComfyUI API (/prompt endpoint).
        """
        # Minimal standard SDXL / SD1.5 ComfyUI workflow JSON
        comfy_prompt = {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "cfg": 7,
                    "denoise": 1,
                    "latent_image": ["5", 0],
                    "model": ["4", 0],
                    "negative": ["7", 0],
                    "positive": ["6", 0],
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "seed": seed,
                    "steps": 20
                }
            },
            "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"}},
            "5": {"class_type": "EmptyLatentImage", "inputs": {"batch_size": 1, "height": height, "width": width}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 1], "text": prompt}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 1], "text": neg_prompt or "bad quality"}},
            "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
            "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "ZFlow_Output", "images": ["8", 0]}}
        }

        req = urllib.request.Request(
            f"{base_url.rstrip('/')}/prompt",
            data=json.dumps({"prompt": comfy_prompt}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            prompt_id = data.get("prompt_id", "comfy_img")
            return f"{base_url.rstrip('/')}/view?filename=ZFlow_Output_{prompt_id}.png&type=output"
