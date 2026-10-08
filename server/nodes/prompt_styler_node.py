"""
Diffusion Prompt Styler & Magic Enchant Engine (ComfyUI / Midjourney / Flux).
Transforms simple, brief concepts into ultra-detailed, professionally styled
diffusion prompts with semantic subject enrichment, atmospheric effects,
artist flavors, camera optics, and optimized negative prompt tokens.
"""
import re
from typing import Dict, Any, List, Optional, Tuple
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
    },
    "fantasy_oil": {
        "positive": "majestic high fantasy oil painting, classical renaissance lighting, textured canvas impasto, rich golden hues, mystical grandeur, heroic composition",
        "negative": "modern, futuristic, plastic, neon, low quality, sketch, amateur"
    },
    "dark_fantasy": {
        "positive": "dark fantasy souls-like atmosphere, moody gothic aesthetic, decrepit stone ruins, ominous shadows, brooding low-key lighting, haunting epic scale",
        "negative": "bright, cheerful, cartoon, saturated colors, low resolution, plastic"
    }
}

LIGHTING_PRESETS: Dict[str, str] = {
    "natural": "clean balanced natural daylight with soft fill light",
    "dramatic": "dramatic chiaroscuro lighting with deep shadows and rim highlights",
    "golden_hour": "warm golden hour sunlight, soft orange glow, long romantic shadows",
    "studio_soft": "soft diffused professional three-point studio lighting",
    "neon": "vibrant neon rim light, moody dual-tone contrast, electric glow",
    "bioluminescent": "ethereal bioluminescent glow, soft radiant ambient light in darkness",
    "cyber_noir": "moody Venetian blind shadows, rainy street lamp reflection, hard side light"
}

CAMERA_PRESETS: Dict[str, str] = {
    "none": "",
    "close_up": "close-up portrait shot, detailed facial expressions, 85mm f/1.4 lens, creamy bokeh",
    "wide_angle": "wide-angle panoramic shot, grand environmental view, 16mm lens, dramatic scale",
    "macro": "extreme macro detail, sharp micro textures, shallow depth of field, 100mm macro lens",
    "drone_aerial": "high angle bird's eye view, sweeping landscape perspective, cinematic aerial composition",
    "anamorphic": "cinematic anamorphic widescreen framing, subtle horizontal lens flare, 2.39:1 aspect ratio aesthetic"
}

ATMOSPHERE_PRESETS: Dict[str, str] = {
    "none": "",
    "volumetric_rays": "dramatic volumetric god rays streaming through atmosphere, crepuscular light shafts",
    "rainy_reflections": "heavy gentle rain, puddles on ground reflecting glowing ambient lights, wet surface sheen",
    "ethereal_fog": "swirling mystical low-lying fog, atmospheric ground haze, moody silhouette depth",
    "floating_particles": "floating bioluminescent dust motes, magical glittering bokeh embers drifting in air",
    "golden_twilight": "golden hour radiance, warm sunset backlighting, long dramatic shadows, dusk gradient sky",
    "studio_noir": "dramatic hard rim light, deep cinematic noir shadows, atmospheric cigarette smoke wisps"
}

ARTIST_PRESETS: Dict[str, str] = {
    "none": "",
    "greg_rutkowski": "art by Greg Rutkowski, grand epic scale, painted dramatic brushwork, fantasy realism",
    "makoto_shinkai": "art aesthetic by Makoto Shinkai, luminous clouds, radiant skies, vibrant anime clarity",
    "studio_ghibli": "inspired by Studio Ghibli, hand-painted warmth, whimsical storybook charm, lush nature",
    "artgerm": "portrait art by Artgerm, clean elegant digital illustration, striking facial focal point",
    "roger_deakins": "cinematography by Roger Deakins, masterclass chiaroscuro framing, cinematic depth"
}

# Semantic subject detection keywords and tailored enrichment micro-details
SUBJECT_ENCHANTMENT_RULES: Dict[str, Dict[str, Any]] = {
    "character": {
        "keywords": ["girl", "woman", "man", "boy", "warrior", "person", "knight", "samurai", "portrait", "face", "model", "cyberpunk girl", "wizard", "cô gái", "chàng trai", "chiến binh", "người"],
        "details": "detailed iris and glossy catchlight, delicate skin micro-texture and soft pores, intricately rendered hair strands flowing naturally, tailored fabric folds and authentic garment stitching, expressive lifelike posture"
    },
    "animal": {
        "keywords": ["cat", "dog", "dragon", "wolf", "tiger", "lion", "bird", "eagle", "bear", "fox", "animal", "creature", "beast", "mèo", "chó", "rồng", "hổ", "sói"],
        "details": "luxurious detailed fur texture, individual delicate whiskers, lively glistening eyes, dynamic organic musculature, natural anatomical accuracy"
    },
    "architecture": {
        "keywords": ["city", "street", "building", "temple", "castle", "cyberpunk city", "room", "interior", "house", "palace", "thành phố", "lâu đài", "ngôi nhà", "đường phố"],
        "details": "intricate architectural masonry, atmospheric street depth, wet asphalt reflections, glowing signage typography, ornate structural geometry, volumetric perspective haze"
    },
    "nature": {
        "keywords": ["mountain", "forest", "tree", "river", "ocean", "sea", "lake", "waterfall", "sunset", "valley", "landscape", "thiên nhiên", "rừng", "núi", "biển", "hoàng hôn"],
        "details": "lush dynamic foliage, cascading ambient light through canopy, distant misty mountain ridges, crystal water surface reflections, sweeping cinematic landscape grandeur"
    },
    "scifi": {
        "keywords": ["mecha", "robot", "spaceship", "sci-fi", "futuristic", "cybernetic", "cyborg", "neon", "armor", "vũ trụ", "người máy", "phi thuyền"],
        "details": "intricate mechanical servo joints, illuminated fiber optic circuitry, weathered battle-worn alloy plates, complex greebles and vents, holographic micro-displays"
    },
    "fantasy": {
        "keywords": ["magic", "rune", "crystal", "fairy", "elf", "spell", "mystical", "celestial", "ethereal", "phép thuật", "tiên nữ", "kỳ ảo"],
        "details": "intricate ornate filigree, celestial radiant aura, ethereal glowing particles, mystical fantasy realism, shimmering ancient runic engravings"
    }
}


def detect_subject_type(prompt: str) -> Tuple[str, str]:
    """Detects the primary subject in the prompt and returns (subject_type, detail_string)."""
    p_lower = prompt.lower()
    for stype, info in SUBJECT_ENCHANTMENT_RULES.items():
        for kw in info["keywords"]:
            if re.search(r'\b' + re.escape(kw) + r'\b', p_lower) or kw in p_lower:
                return stype, info["details"]
    return "general", "hyper-detailed textures, balanced compositional harmony, refined craftsmanship, nuanced depth"


def enchant_prompt(
    base_prompt: str,
    enchant_level: str = "vivid",
    style: str = "cinematic",
    lighting: str = "dramatic",
    camera: str = "none",
    atmosphere: str = "none",
    artist: str = "none",
    extra_boosters: str = "",
    enable_subject_detailing: bool = True
) -> Dict[str, Any]:
    """
    Enchants and enriches a base prompt with multi-tier photographic,
    artistic, atmospheric, and semantic subject detailing.
    """
    base = base_prompt.strip()
    subject_type, subject_details = detect_subject_type(base)
    
    style_info = STYLE_PRESETS.get(style, {"positive": "", "negative": ""})
    
    components: List[str] = [base]
    added_traits: List[str] = []

    # 1. Subject Enrichment Layer
    if enable_subject_detailing and enchant_level != "none" and subject_details:
        components.append(subject_details)
        added_traits.append(f"Subject Detailing ({subject_type})")

    # 2. Artistic Style Layer
    if style_info.get("positive"):
        components.append(style_info["positive"])
        added_traits.append(f"Style: {style}")

    # 3. Atmosphere & Environmental Weather Layer
    atm_text = ATMOSPHERE_PRESETS.get(atmosphere, "")
    if atm_text:
        components.append(atm_text)
        added_traits.append(f"Atmosphere: {atmosphere}")

    # 4. Lighting Layer
    light_text = LIGHTING_PRESETS.get(lighting, "")
    if light_text:
        components.append(light_text)
        added_traits.append(f"Lighting: {lighting}")

    # 5. Camera Optics & Framing Layer
    cam_text = CAMERA_PRESETS.get(camera, "")
    if cam_text:
        components.append(cam_text)
        added_traits.append(f"Camera: {camera}")

    # 6. Artist & Cinematographer Flavor
    art_text = ARTIST_PRESETS.get(artist, "")
    if art_text:
        components.append(art_text)
        added_traits.append(f"Artist Flavor: {artist}")

    # 7. Enchantment Level Boosters
    if enchant_level == "subtle":
        components.append("clean focus, refined color grade, natural balance")
        added_traits.append("Enchant: Subtle")
    elif enchant_level == "vivid":
        components.append("vivid color dynamic range, 8k uhd, sharp focal plane, ray-traced shadows, masterpiece")
        added_traits.append("Enchant: Vivid")
    elif enchant_level == "masterpiece_epic":
        components.append(
            "unreal engine 5 render, octane render, 8k uhd resolution, cinematic color grading, "
            "subsurface scattering, global illumination, atmospheric perspective, award-winning masterpiece"
        )
        added_traits.append("Enchant: Epic Masterpiece")
    elif enchant_level == "ai_magic_rewrite":
        # Enhanced narrative framing
        components.append(
            "breathtaking visual storytelling, impeccably balanced golden ratio composition, "
            "photorealistic volumetric lighting, ultra high fidelity textures, cinematic key visual, masterpiece"
        )
        added_traits.append("Enchant: AI Magic Rewrite")

    if extra_boosters.strip():
        components.append(extra_boosters.strip())

    enchanted_positive = ", ".join([c.strip() for c in components if c.strip()])

    # Construct Negative Prompt
    neg_tokens: List[str] = []
    if style_info.get("negative"):
        neg_tokens.append(style_info["negative"])
    
    # Universal negative quality protectors
    neg_tokens.append("watermark, text, signature, low quality, bad anatomy, deformed, disfigured, blurry, oversaturated")

    if enchant_level in ("masterpiece_epic", "ai_magic_rewrite"):
        neg_tokens.append("jpeg artifacts, lowres, extra limbs, poorly drawn face, poorly drawn hands, duplicate")

    enchanted_negative = ", ".join([n.strip() for n in neg_tokens if n.strip()])

    return {
        "original_prompt": base,
        "enchanted_prompt": enchanted_positive,
        "negative_prompt": enchanted_negative,
        "detected_subject": subject_type,
        "enchant_level": enchant_level,
        "added_traits": added_traits
    }


@NodeRegistry.register
class PromptStylerNode(BaseNode):
    node_type = "prompt_styler"
    name = "Diffusion Prompt Styler & Enchant"
    category = "prompt"
    description = "Nâng cấp và phù phép (Enchant) prompt tạo ảnh chi tiết: Bổ sung texture nhân vật/phong cảnh, ánh sáng, góc máy, hiệu ứng không khí và Negative Prompt tối ưu."
    icon = "Palette"

    inputs = [
        PortDef(name="base_prompt", data_type="string", label="Base Concept / Prompt", required=True),
        PortDef(name="extra_negative", data_type="string", label="Extra Negative Tokens", required=False)
    ]
    outputs = [
        PortDef(name="positive_prompt", data_type="string", label="Enchanted Positive Prompt"),
        PortDef(name="styled_prompt", data_type="string", label="Styled Prompt (Alias)"),
        PortDef(name="prompt", data_type="string", label="Prompt (Alias)"),
        PortDef(name="negative_prompt", data_type="string", label="Optimized Negative Prompt"),
        PortDef(name="detected_subject", data_type="string", label="Detected Subject Type"),
        PortDef(name="style_applied", data_type="string", label="Selected Style Name")
    ]

    config_schema = {
        "enchant_level": {
            "type": "select",
            "label": "Prompt Enchant Level (Cấp độ phù phép)",
            "options": ["none", "subtle", "vivid", "masterpiece_epic", "ai_magic_rewrite"],
            "default": "vivid"
        },
        "style": {
            "type": "select",
            "label": "Artistic Style Preset",
            "options": ["cinematic", "photorealistic", "anime", "pixar_3d", "cyberpunk", "watercolor", "fantasy_oil", "dark_fantasy", "none"],
            "default": "cinematic"
        },
        "lighting": {
            "type": "select",
            "label": "Lighting Mood",
            "options": ["natural", "dramatic", "golden_hour", "studio_soft", "neon", "bioluminescent", "cyber_noir"],
            "default": "dramatic"
        },
        "camera": {
            "type": "select",
            "label": "Camera & Lens",
            "options": ["none", "close_up", "wide_angle", "macro", "drone_aerial", "anamorphic"],
            "default": "none"
        },
        "atmosphere": {
            "type": "select",
            "label": "Atmospheric Effects",
            "options": ["none", "volumetric_rays", "rainy_reflections", "ethereal_fog", "floating_particles", "golden_twilight", "studio_noir"],
            "default": "none"
        },
        "artist": {
            "type": "select",
            "label": "Artist / Director Flavor",
            "options": ["none", "greg_rutkowski", "makoto_shinkai", "studio_ghibli", "artgerm", "roger_deakins"],
            "default": "none"
        },
        "enable_subject_detailing": {
            "type": "boolean",
            "label": "Auto Semantic Subject Detailing",
            "default": True
        },
        "quality_boosters": {
            "type": "string",
            "label": "Extra Custom Tokens",
            "default": ""
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
        
        enchant_level = config.get("enchant_level", "vivid")
        style_key = config.get("style", "cinematic")
        lighting_key = config.get("lighting", "dramatic")
        camera_key = config.get("camera", "none")
        atmosphere_key = config.get("atmosphere", "none")
        artist_key = config.get("artist", "none")
        subject_detailing = config.get("enable_subject_detailing", True)
        boosters = config.get("quality_boosters", "")

        enchant_result = enchant_prompt(
            base_prompt=base,
            enchant_level=enchant_level,
            style=style_key,
            lighting=lighting_key,
            camera=camera_key,
            atmosphere=atmosphere_key,
            artist=artist_key,
            extra_boosters=boosters,
            enable_subject_detailing=subject_detailing
        )

        styled_positive = enchant_result["enchanted_prompt"]
        styled_negative = enchant_result["negative_prompt"]
        if extra_neg:
            styled_negative = f"{extra_neg}, {styled_negative}"

        subject_type = enchant_result["detected_subject"]

        # Store in context variables
        context.set_variable("positive_prompt", styled_positive)
        context.set_variable("styled_prompt", styled_positive)
        context.set_variable("enchanted_prompt", styled_positive)
        context.set_variable("negative_prompt", styled_negative)
        context.set_variable("detected_subject", subject_type)
        context.set_variable("prompt_style", style_key)
        
        context.log("info", f"Prompt Styler enchanted prompt ({enchant_level}, subject: {subject_type}): {styled_positive[:60]}...")

        return {
            "positive_prompt": styled_positive,
            "styled_prompt": styled_positive,
            "prompt": styled_positive,
            "negative_prompt": styled_negative,
            "detected_subject": subject_type,
            "style_applied": style_key,
            "enchant_level": enchant_level,
            "added_traits": enchant_result["added_traits"]
        }
