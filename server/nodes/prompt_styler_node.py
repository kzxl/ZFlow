"""
Prompt Styler Node (SD / Flux / ComfyUI Style Enhancer).
Transforms simple user prompts into professional diffusion prompts with
curated artistic styles, lighting cues, camera perspectives, and negative prompt tokens.
"""
from typing import Dict, Any, List, Optional
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext

STYLE_PRESETS: Dict[str, Dict[str, str]] = {
    "cinematic": {
        "positive": "cinematic film still, 35mm photograph, dramatic rim lighting, blockbuster atmosphere, shallow depth of field, 8k resolution, photorealistic, color graded",
        "negative": "cartoon, illustration, 3d render, oversaturated, blurry, low resolution, bad anatomy, deformed"
    },
    "photorealistic": {
        "positive": "ultra-realistic professional photograph, 8k uhd, dslr, soft natural lighting, high dynamic range, sharp focus, hyper-detailed, masterpiece",
        "negative": "cgi, 3d, painting, sketch, drawing, deformed, bad eyes, disfigured, watermark, text"
    },
    "anime": {
        "positive": "anime key visual, studio ghibli and makoto shinkai aesthetic, gorgeous detailed background, vibrant colors, expressive eyes, digital art, masterpiece",
        "negative": "photo, realistic, 3d, western comic, blurry, muted colors, deformed fingers"
    },
    "pixar_3d": {
        "positive": "charming 3d character render, pixar and disney animation style, smooth subsurface scattering, expressive face, vibrant lighting, octane render, 4k",
        "negative": "photograph, realistic human, sketch, 2d anime, creepy, uncanny valley, dark, grainy"
    },
    "cyberpunk": {
        "positive": "neon cyberpunk aesthetic, futuristic sci-fi city, glowing neon signage, reflective wet asphalt, volumetric fog and smoke, cinematic composition, unreal engine 5",
        "negative": "daylight, rustic, vintage, low quality, washed out, blurry"
    },
    "watercolor": {
        "positive": "delicate watercolor painting, artistic paper texture, soft brush strokes, dreamy color bleed, traditional fine art, expressive masterpiece",
        "negative": "photo, digital render, 3d, harsh lines, oversaturated, sharp geometric"
    }
}

LIGHTING_PRESETS: Dict[str, str] = {
    "dramatic": "dramatic chiaroscuro lighting with deep shadows",
    "golden_hour": "warm golden hour sunlight, soft orange glow",
    "studio_soft": "soft diffused professional studio lighting",
    "neon": "vibrant neon rim light, moody contrast",
    "natural": "clean balanced natural daylight"
}

CAMERA_PRESETS: Dict[str, str] = {
    "close_up": "close-up portrait shot, detailed facial expressions",
    "wide_angle": "wide-angle panoramic shot, grand environmental view",
    "macro": "extreme macro detail, sharp micro textures",
    "drone_aerial": "high angle bird's eye view, sweeping landscape"
}


@NodeRegistry.register
class PromptStylerNode(BaseNode):
    node_type = "prompt_styler"
    name = "Diffusion Prompt Styler"
    category = "prompt"
    description = "Nâng cấp câu lệnh tạo ảnh thường thành câu prompt chuyên nghiệp (Cinematic, Anime, Pixar 3D, Cyberpunk) kèm Negative Prompt chuẩn ComfyUI."
    icon = "Palette"

    inputs = [
        PortDef(name="base_prompt", data_type="string", label="Base Concept / User Query", required=True),
        PortDef(name="extra_negative", data_type="string", label="Extra Negative Tokens", required=False)
    ]
    outputs = [
        PortDef(name="positive_prompt", data_type="string", label="Styled Positive Prompt"),
        PortDef(name="styled_prompt", data_type="string", label="Styled Positive Prompt (Alias)"),
        PortDef(name="negative_prompt", data_type="string", label="Negative Prompt"),
        PortDef(name="style_applied", data_type="string", label="Selected Style Name")
    ]

    config_schema = {
        "style": {
            "type": "select",
            "label": "Artistic Style Preset",
            "options": ["cinematic", "photorealistic", "anime", "pixar_3d", "cyberpunk", "watercolor", "none"],
            "default": "cinematic"
        },
        "lighting": {
            "type": "select",
            "label": "Lighting Mood",
            "options": ["natural", "dramatic", "golden_hour", "studio_soft", "neon"],
            "default": "dramatic"
        },
        "camera": {
            "type": "select",
            "label": "Camera Framing",
            "options": ["none", "close_up", "wide_angle", "macro", "drone_aerial"],
            "default": "none"
        },
        "quality_boosters": {
            "type": "string",
            "label": "Quality Boosters",
            "default": "masterpiece, best quality, highly detailed"
        }
    }

    async def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        base = str(
            inputs.get("base_prompt")
            or inputs.get("query")
            or inputs.get("input")
            or context.get_variable("query")
            or context.get_variable("input", "")
        ).strip()

        extra_neg = str(inputs.get("extra_negative") or "").strip()
        style_key = config.get("style", "cinematic")
        lighting_key = config.get("lighting", "dramatic")
        camera_key = config.get("camera", "none")
        boosters = config.get("quality_boosters", "masterpiece, highly detailed")

        style_info = STYLE_PRESETS.get(style_key, {"positive": "", "negative": ""})
        
        # Build positive prompt elements
        pos_parts = [base]
        if style_info["positive"]:
            pos_parts.append(style_info["positive"])
        if lighting_key in LIGHTING_PRESETS:
            pos_parts.append(LIGHTING_PRESETS[lighting_key])
        if camera_key in CAMERA_PRESETS:
            pos_parts.append(CAMERA_PRESETS[camera_key])
        if boosters:
            pos_parts.append(boosters)

        styled_positive = ", ".join([p.strip() for p in pos_parts if p.strip()])

        # Build negative prompt
        neg_parts = []
        if style_info["negative"]:
            neg_parts.append(style_info["negative"])
        if extra_neg:
            neg_parts.append(extra_neg)
        neg_parts.append("watermark, text, signature, low quality, bad anatomy, deformed")

        styled_negative = ", ".join([n.strip() for n in neg_parts if n.strip()])

        # Store in context
        context.set_variable("positive_prompt", styled_positive)
        context.set_variable("negative_prompt", styled_negative)
        context.set_variable("prompt_style", style_key)
        context.log("info", f"Prompt Styler applied '{style_key}' style.")

        return {
            "positive_prompt": styled_positive,
            "styled_prompt": styled_positive,
            "prompt": styled_positive,
            "negative_prompt": styled_negative,
            "style_applied": style_key
        }
