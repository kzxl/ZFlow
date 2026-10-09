"""
AI Image Generator Node (Flux, SDXL, DALL-E 3 & ComfyUI Local Bridge).
Generates high-resolution images from text prompts with support for
cloud diffusion APIs and local ComfyUI WebSocket/REST servers.
"""
import asyncio
from typing import Dict, Any, List, Optional
import json
import os
import time
import random
import urllib.parse
import httpx
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext

ASPECT_RATIO_DIMENSIONS: Dict[str, tuple[int, int]] = {
    "3:2": (1248, 832),
    "1:1": (1024, 1024),
    "16:9": (1344, 768),
    "9:16": (768, 1344),
    "4:3": (1152, 864)
}

RESOLUTION_SELECTOR_MAP: Dict[str, str] = {
    "3:2": "3:2 (Photo)",
    "1:1": "1:1 (Square)",
    "16:9": "16:9 (Widescreen)",
    "9:16": "9:16 (Vertical)",
    "4:3": "4:3 (Classic)"
}


@NodeRegistry.register
class ImageGenNode(BaseNode):
    node_type = "image_gen"
    name = "AI Image Generator"
    category = "media"
    description = "Tạo ảnh nghệ thuật AI chất lượng cao (Hỗ trợ ComfyUI Local Pipeline, DALL-E 3, Flux.1 hoặc Simulator)."
    icon = "Image"

    inputs = [
        PortDef(name="prompt", data_type="string", label="Positive Prompt", required=True),
        PortDef(name="negative_prompt", data_type="string", label="Negative Prompt", required=False),
        PortDef(name="aspect_ratio", data_type="string", label="Aspect Ratio (3:2, 1:1, 16:9...)", required=False)
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
            "options": ["comfyui_local", "simulator", "dalle3", "flux_pollinations"],
            "default": "comfyui_local"
        },
        "comfyui_base_url": {
            "type": "string",
            "label": "ComfyUI Server Address",
            "default": "http://192.168.10.7:8188"
        },
        "workflow_mode": {
            "type": "select",
            "label": "Chế độ ComfyUI Workflow",
            "options": ["auto_history", "qwen_image_2_1", "sdxl_standard", "custom_json"],
            "default": "auto_history"
        },
        "enable_prompt_expansion": {
            "type": "boolean",
            "label": "Bật LLM Prompt Rewriter (Qwen TextGenerate)",
            "default": True
        },
        "steps": {
            "type": "number",
            "label": "Sampling Steps (Số bước lấy mẫu)",
            "min": 1,
            "max": 100,
            "step": 1,
            "default": 25
        },
        "cfg_scale": {
            "type": "number",
            "label": "CFG Scale (Guidance)",
            "min": 1.0,
            "max": 20.0,
            "step": 0.5,
            "default": 1.0
        },
        "sampler_name": {
            "type": "select",
            "label": "Sampler Name",
            "options": ["euler", "euler_ancestral", "dpmpp_2m", "dpmpp_2s_ancestral", "dpmpp_sde", "ddim", "uni_pc"],
            "default": "euler"
        },
        "scheduler": {
            "type": "select",
            "label": "Scheduler",
            "options": ["simple", "normal", "karras", "exponential", "sgm_uniform", "ddim_uniform"],
            "default": "simple"
        },
        "denoise": {
            "type": "number",
            "label": "Denoise Strength",
            "min": 0.1,
            "max": 1.0,
            "step": 0.05,
            "default": 1.0
        },
        "aspect_ratio": {
            "type": "select",
            "label": "Tỉ lệ khung hình (Aspect Ratio)",
            "options": ["3:2", "1:1", "16:9", "9:16", "4:3", "custom"],
            "default": "3:2"
        },
        "custom_width": {
            "type": "number",
            "label": "Custom Width px (nếu chọn custom)",
            "min": 256,
            "max": 2048,
            "step": 64,
            "default": 1248
        },
        "custom_height": {
            "type": "number",
            "label": "Custom Height px (nếu chọn custom)",
            "min": 256,
            "max": 2048,
            "step": 64,
            "default": 832
        },
        "seed": {
            "type": "number",
            "label": "Random Seed (-1 để ngẫu nhiên)",
            "default": -1
        },
        "negative_prompt": {
            "type": "string",
            "label": "Negative Prompt mặc định",
            "default": ""
        },
        "timeout_seconds": {
            "type": "number",
            "label": "ComfyUI Timeout (giây)",
            "min": 30,
            "max": 600,
            "step": 10,
            "default": 240
        },
        "fallback_simulator": {
            "type": "boolean",
            "label": "Fallback sang Simulator nếu ComfyUI lỗi",
            "default": False
        },
        "custom_workflow_json": {
            "type": "textarea",
            "label": "Custom Workflow JSON (nếu chọn custom_json)",
            "default": ""
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
            or config.get("negative_prompt", "")
        ).strip()

        ratio = str(inputs.get("aspect_ratio") or config.get("aspect_ratio", "3:2"))
        if ratio == "custom":
            width = int(config.get("custom_width", 1248))
            height = int(config.get("custom_height", 832))
        else:
            width, height = ASPECT_RATIO_DIMENSIONS.get(ratio, (1248, 832))

        provider = config.get("provider", "comfyui_local")
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
            base_url = config.get("comfyui_base_url", "http://192.168.10.7:8188")
            try:
                image_url = await self._generate_comfyui_bridge(
                    prompt=prompt,
                    neg_prompt=neg_prompt,
                    width=width,
                    height=height,
                    ratio=ratio,
                    seed=seed,
                    base_url=base_url,
                    config=config,
                    context=context
                )
            except Exception as e:
                context.log("error", f"ComfyUI bridge error: {e}")
                if config.get("fallback_simulator", False):
                    context.log("warning", "Falling back to High-res Simulator.")
                    image_url = self._generate_simulator(prompt, width, height, seed)
                else:
                    err_msg = f"❌ **Lỗi sinh ảnh ComfyUI ({base_url})**:\n\n`{str(e)}`\n\n*Vui lòng kiểm tra server ComfyUI hoặc chỉnh lại thông số node.*"
                    return {
                        "image_url": "",
                        "markdown_image": err_msg,
                        "markdown": err_msg,
                        "revised_prompt": prompt,
                        "seed": seed,
                        "aspect_ratio": ratio,
                        "width": width,
                        "height": height,
                        "is_mock": False,
                        "status": "error",
                        "error": str(e)
                    }
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
            "is_mock": provider == "simulator",
            "status": status
        }

    def _generate_simulator(self, prompt: str, width: int, height: int, seed: int) -> str:
        """
        Generates realistic high-res AI image link matching keywords from prompt.
        """
        clean_prompt = prompt.replace("\n", " ").strip()
        encoded = urllib.parse.quote(clean_prompt[:150])
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

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/images/generations",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"}
            )
            resp.raise_for_status()
            data = resp.json()
            item = data["data"][0]
            return item.get("url", ""), item.get("revised_prompt", prompt)

    async def _generate_comfyui_bridge(
        self,
        prompt: str,
        neg_prompt: str,
        width: int,
        height: int,
        ratio: str,
        seed: int,
        base_url: str,
        config: Dict[str, Any],
        context: ExecutionContext
    ) -> str:
        """
        Communicates with local ComfyUI API (/prompt endpoint) and polls for real output.
        Dynamically adapts to the user's active workflow or falls back to template.
        """
        base_url = base_url.rstrip("/")
        workflow_mode = config.get("workflow_mode", "auto_history")
        workflow = None

        # 1. Custom workflow from config if selected
        if workflow_mode == "custom_json":
            custom_wf_str = config.get("custom_workflow_json", "").strip()
            if custom_wf_str:
                try:
                    workflow = json.loads(custom_wf_str)
                    context.log("info", "Using custom ComfyUI workflow JSON from node config.")
                except Exception as e:
                    context.log("warning", f"Failed to parse custom workflow JSON: {e}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 2. Try to fetch active workflow from ComfyUI history if mode is auto_history
            if not workflow and workflow_mode == "auto_history":
                try:
                    hist_resp = await client.get(f"{base_url}/history", timeout=5.0)
                    if hist_resp.status_code == 200:
                        hist_data = hist_resp.json()
                        for pid in reversed(list(hist_data.keys())):
                            entry = hist_data[pid]
                            if entry.get("prompt") and len(entry["prompt"]) > 2:
                                workflow = json.loads(json.dumps(entry["prompt"][2]))
                                context.log("info", f"Reusing active workflow from ComfyUI history (ID: {pid})")
                                break
                except Exception as e:
                    context.log("warning", f"Could not fetch ComfyUI history: {e}")

            # 3. Load Qwen Image 2.1 template from server/config
            if not workflow and workflow_mode in ("auto_history", "qwen_image_2_1"):
                template_path = os.path.join(os.path.dirname(__file__), "..", "config", "comfyui_default_workflow.json")
                if os.path.exists(template_path):
                    try:
                        with open(template_path, "r", encoding="utf-8") as f:
                            workflow = json.load(f)
                        context.log("info", "Loaded ComfyUI workflow from Qwen Image 2.1 template.")
                    except Exception as e:
                        context.log("warning", f"Failed to load comfyui_default_workflow.json: {e}")

            # 4. Standard Checkpoint / SDXL fallback
            if not workflow:
                context.log("info", "Constructing standard SDXL / SD 1.5 pipeline workflow.")
                workflow = {
                    "3": {"class_type": "KSampler", "inputs": {"cfg": 7, "denoise": 1, "latent_image": ["5", 0], "model": ["4", 0], "negative": ["7", 0], "positive": ["6", 0], "sampler_name": "euler", "scheduler": "normal", "seed": seed, "steps": 20}},
                    "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"}},
                    "5": {"class_type": "EmptyLatentImage", "inputs": {"batch_size": 1, "height": height, "width": width}},
                    "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 1], "text": prompt}},
                    "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 1], "text": neg_prompt or "bad quality"}},
                    "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
                    "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "ZFlow_Output", "images": ["8", 0]}}
                }

            # 5. Inject prompt and advanced ComfyUI parameters into workflow
            steps = int(config.get("steps", 25))
            cfg = float(config.get("cfg_scale", 1.0))
            sampler = str(config.get("sampler_name", "euler"))
            scheduler = str(config.get("scheduler", "simple"))
            denoise = float(config.get("denoise", 1.0))
            enable_expansion = bool(config.get("enable_prompt_expansion", True))
            res_ratio_str = RESOLUTION_SELECTOR_MAP.get(ratio, "3:2 (Photo)")

            for nid, node in workflow.items():
                ctype = node.get("class_type", "")
                inputs = node.get("inputs", {})

                # Text / Prompt injection
                if ctype == "TextGenerate":
                    inputs["prompt"] = prompt
                    if "sampling_mode.seed" in inputs:
                        inputs["sampling_mode.seed"] = seed
                elif ctype == "ComfySwitchNode":
                    # Controls whether to use TextGenerate (on_true) or bypass to user prompt (on_false)
                    inputs["switch"] = enable_expansion
                    if isinstance(inputs.get("on_false"), str):
                        inputs["on_false"] = prompt
                elif ctype in ("CLIPTextEncode", "TextEncodeQwenImage21"):
                    if "negative_prompt" in inputs and neg_prompt:
                        inputs["negative_prompt"] = neg_prompt
                    if "text" in inputs:
                        text_val = inputs["text"]
                        if isinstance(text_val, str):
                            if any(w in text_val.lower() for w in ["bad", "ugly", "blur", "low quality", "worst", "disfigured"]):
                                if neg_prompt:
                                    inputs["text"] = neg_prompt
                            else:
                                inputs["text"] = prompt
                elif ctype in ("KSampler", "KSamplerAdvanced"):
                    inputs["seed"] = seed
                    inputs["steps"] = steps
                    inputs["cfg"] = cfg
                    inputs["sampler_name"] = sampler
                    inputs["scheduler"] = scheduler
                    inputs["denoise"] = denoise
                elif ctype == "ResolutionSelector":
                    if "aspect_ratio" in inputs:
                        inputs["aspect_ratio"] = res_ratio_str
                elif ctype == "EmptyLatentImage":
                    if isinstance(inputs.get("width"), (int, float)):
                        inputs["width"] = width
                    if isinstance(inputs.get("height"), (int, float)):
                        inputs["height"] = height

            # 6. Submit prompt to ComfyUI
            submit_resp = await client.post(
                f"{base_url}/prompt",
                json={"prompt": workflow},
                timeout=15.0
            )
            if submit_resp.status_code != 200:
                raise RuntimeError(f"ComfyUI rejected prompt ({submit_resp.status_code}): {submit_resp.text}")

            submit_data = submit_resp.json()
            prompt_id = submit_data.get("prompt_id")
            if not prompt_id:
                raise RuntimeError(f"ComfyUI did not return prompt_id: {submit_resp.text}")

            context.log("info", f"Submitted prompt to ComfyUI with ID {prompt_id} (steps: {steps}, cfg: {cfg}, sampler: {sampler}), waiting for generation...")

            # 7. Asynchronously poll for completion
            max_wait_seconds = int(config.get("timeout_seconds", 240))
            start_time = time.time()
            poll_interval = 2.0

            while time.time() - start_time < max_wait_seconds:
                await asyncio.sleep(poll_interval)
                elapsed = int(time.time() - start_time)

                try:
                    check_resp = await client.get(f"{base_url}/history/{prompt_id}", timeout=5.0)
                    if check_resp.status_code == 200:
                        h_data = check_resp.json()
                        if prompt_id in h_data:
                            entry = h_data[prompt_id]
                            status = entry.get("status", {})
                            if status.get("status_str") == "error":
                                err_details = status.get("messages", [])
                                raise RuntimeError(f"ComfyUI execution failed: {err_details}")

                            outputs = entry.get("outputs", {})
                            for out_nid, out_val in outputs.items():
                                if "images" in out_val and len(out_val["images"]) > 0:
                                    img_info = out_val["images"][0]
                                    fname = img_info["filename"]
                                    subf = img_info.get("subfolder", "")
                                    img_type = img_info.get("type", "temp")
                                    image_url = f"{base_url}/view?filename={urllib.parse.quote(fname)}&subfolder={urllib.parse.quote(subf)}&type={urllib.parse.quote(img_type)}"
                                    context.log("info", f"ComfyUI generation completed in {elapsed}s: {image_url}")
                                    return image_url

                    context.log("info", f"ComfyUI generating... ({elapsed}s)")
                except Exception as poll_err:
                    if "ComfyUI execution failed" in str(poll_err):
                        raise
                    # Ignore transient network issues during polling

            raise TimeoutError(f"ComfyUI generation timed out after {max_wait_seconds}s for prompt {prompt_id}")
