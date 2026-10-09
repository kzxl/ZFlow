"""
Negative Prompt Node for AI Image Generation (ComfyUI / SDXL / Flux / DALL-E).
Configures and compiles exclusion keywords and quality filter tokens to remove
artifacts, bad anatomy, watermarks, and unwanted elements from generated images.
"""
from typing import Dict, Any, List
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext

NEGATIVE_PRESETS: Dict[str, str] = {
    "universal_clean": (
        "blurry, low quality, bad anatomy, deformed, mutated, disfigured, poorly drawn face, "
        "bad hands, missing fingers, extra limbs, worst quality, low resolution, jpeg artifacts, "
        "grainy, duplicate, morbid, mutilated, extra fingers, poorly drawn hands"
    ),
    "photorealistic_clean": (
        "ugly, deformed, noise, blurry, distorted, grainy, low quality, bad eyes, unnatural skin, "
        "extra fingers, cartoon, 3d, painting, sketch, drawing, bad proportions, cloned face, "
        "disfigured, gross proportions, malformed limbs, missing arms, missing legs"
    ),
    "anime_clean": (
        "low quality, worst quality, blurry, 3d, realistic photo, bad hands, extra limbs, "
        "bad anatomy, poorly drawn eyes, poorly drawn hair, monochrome, greyscale, text, watermark"
    ),
    "no_watermark_text": (
        "watermark, text, signature, logo, copyright, subtitle, caption, branding, username, "
        "artist name, stamp, label, banner"
    ),
    "custom_only": ""
}


@NodeRegistry.register
class NegativePromptNode(BaseNode):
    node_type = "negative_prompt"
    name = "Negative Prompt"
    category = "media"
    description = "Định cấu hình các từ khóa phủ định (negative prompt) và bộ lọc chất lượng loại trừ artifact cho AI Image Generator."
    icon = "Ban"

    inputs = [
        PortDef(name="prompt", data_type="string", label="Incoming Prompt (Opt)", required=False),
        PortDef(name="text", data_type="string", label="Custom Negative Input", required=False),
        PortDef(name="append_text", data_type="string", label="Additional Keywords", required=False)
    ]

    outputs = [
        PortDef(name="negative_prompt", data_type="string", label="Negative Prompt Output"),
        PortDef(name="prompt", data_type="string", label="Prompt Passthrough"),
        PortDef(name="text", data_type="string", label="Negative Prompt Text")
    ]

    config_schema = {
        "preset": {
            "type": "select",
            "label": "Bộ lọc chất lượng mẫu (Quality Filter Preset)",
            "options": ["universal_clean", "photorealistic_clean", "anime_clean", "no_watermark_text", "custom_only"],
            "default": "universal_clean"
        },
        "custom_negative": {
            "type": "textarea",
            "label": "Từ khóa phủ định tùy chỉnh (Custom Negative Tokens)",
            "default": "blurry, low quality, bad anatomy, deformed, worst quality"
        },
        "append_preset": {
            "type": "boolean",
            "label": "Ghép chung bộ lọc mẫu với từ khóa tùy chỉnh",
            "default": True
        }
    }

    async def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        preset_key = config.get("preset", "universal_clean")
        preset_tokens = NEGATIVE_PRESETS.get(preset_key, "")
        custom_tokens = config.get("custom_negative", "").strip()
        append_preset = config.get("append_preset", True)

        prompt_val = str(inputs.get("prompt") or context.get_variable("prompt") or context.get_variable("input", "")).strip()
        incoming_text = str(inputs.get("text") or "").strip()
        additional_text = str(inputs.get("append_text") or "").strip()

        tokens_list = []
        if append_preset and preset_tokens:
            tokens_list.append(preset_tokens)
        elif not append_preset and preset_key != "custom_only" and not custom_tokens:
            tokens_list.append(preset_tokens)

        if custom_tokens:
            tokens_list.append(custom_tokens)
        if incoming_text:
            tokens_list.append(incoming_text)
        if additional_text:
            tokens_list.append(additional_text)

        # Merge and deduplicate comma-separated tokens
        raw_combined = ", ".join(filter(None, tokens_list))
        raw_tokens = [t.strip() for t in raw_combined.split(",") if t.strip()]

        seen = set()
        deduped = []
        for t in raw_tokens:
            t_lower = t.lower()
            if t_lower not in seen:
                seen.add(t_lower)
                deduped.append(t)

        final_negative = ", ".join(deduped)

        context.set_variable("negative_prompt", final_negative)
        context.log("info", f"Compiled Negative Prompt ({len(deduped)} tokens): {final_negative[:60]}...")

        return {
            "negative_prompt": final_negative,
            "prompt": prompt_val,
            "text": final_negative
        }
