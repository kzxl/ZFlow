"""
Aspect Ratio Node for AI Image Generation (ComfyUI / SDXL / Flux / DALL-E).
Manages canvas proportions, dimension mappings, and resolution calculations
for high-performance latent image rendering.
"""
from typing import Dict, Any, Tuple
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext

ASPECT_RATIO_PRESETS: Dict[str, Tuple[int, int, str]] = {
    "3:2": (1248, 832, "3:2 (Ngang - Photo Landscape)"),
    "2:3": (832, 1248, "2:3 (Dọc - Photo Portrait)"),
    "1:1": (1024, 1024, "1:1 (Vuông - Square Avatar/Post)"),
    "16:9": (1280, 720, "16:9 (Điện ảnh - Cinematic Widescreen)"),
    "9:16": (720, 1280, "9:16 (Dọc điện thoại - Story / TikTok)"),
    "4:3": (1152, 864, "4:3 (Truyền thống - Standard Classic)"),
    "3:4": (864, 1152, "3:4 (Chân dung cổ điển - Classic Portrait)"),
    "21:9": (1536, 640, "21:9 (Toàn cảnh siêu rộng - Ultrawide)")
}


@NodeRegistry.register
class AspectRatioNode(BaseNode):
    node_type = "aspect_ratio"
    name = "Aspect Ratio"
    category = "media"
    description = "Quản lý tỉ lệ khung hình và tính toán độ phân giải chuẩn (Width/Height) cho AI Image Generator."
    icon = "Maximize2"

    inputs = [
        PortDef(name="prompt", data_type="string", label="Incoming Prompt (Opt)", required=False),
        PortDef(name="negative_prompt", data_type="string", label="Incoming Negative Prompt (Opt)", required=False),
        PortDef(name="ratio", data_type="string", label="Tỉ lệ đầu vào (Tùy chọn)", required=False)
    ]

    outputs = [
        PortDef(name="aspect_ratio", data_type="string", label="Mã tỉ lệ (3:2, 1:1, 16:9...)"),
        PortDef(name="prompt", data_type="string", label="Prompt Passthrough"),
        PortDef(name="negative_prompt", data_type="string", label="Negative Prompt Passthrough"),
        PortDef(name="width", data_type="number", label="Chiều rộng (px)"),
        PortDef(name="height", data_type="number", label="Chiều cao (px)"),
        PortDef(name="resolution_label", data_type="string", label="Nhãn hiển thị độ phân giải")
    ]

    config_schema = {
        "aspect_ratio": {
            "type": "select",
            "label": "Tỉ lệ khung hình (Aspect Ratio)",
            "options": ["3:2", "2:3", "1:1", "16:9", "9:16", "4:3", "3:4", "21:9", "custom"],
            "default": "3:2"
        },
        "custom_width": {
            "type": "number",
            "label": "Custom Width (px - nếu chọn custom)",
            "min": 256,
            "max": 2048,
            "step": 64,
            "default": 1248
        },
        "custom_height": {
            "type": "number",
            "label": "Custom Height (px - nếu chọn custom)",
            "min": 256,
            "max": 2048,
            "step": 64,
            "default": 832
        }
    }

    async def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        incoming_ratio = str(inputs.get("ratio") or "").strip()
        selected_ratio = incoming_ratio if incoming_ratio in ASPECT_RATIO_PRESETS else config.get("aspect_ratio", "3:2")

        prompt_val = str(inputs.get("prompt") or context.get_variable("prompt") or context.get_variable("input", "")).strip()
        neg_val = str(inputs.get("negative_prompt") or context.get_variable("negative_prompt", "")).strip()

        if selected_ratio == "custom":
            width = int(config.get("custom_width", 1248))
            height = int(config.get("custom_height", 832))
            label = f"{width} × {height} (Custom)"
        else:
            w_def, h_def, label_def = ASPECT_RATIO_PRESETS.get(selected_ratio, (1248, 832, "3:2 Landscape"))
            width = w_def
            height = h_def
            label = f"{width} × {height} ({label_def})"

        context.set_variable("aspect_ratio", selected_ratio)
        context.set_variable("image_width", width)
        context.set_variable("image_height", height)
        context.log("info", f"Resolved Aspect Ratio: {selected_ratio} -> {width}x{height} ({label})")

        return {
            "aspect_ratio": selected_ratio,
            "prompt": prompt_val,
            "negative_prompt": neg_val,
            "width": width,
            "height": height,
            "resolution_label": label
        }
