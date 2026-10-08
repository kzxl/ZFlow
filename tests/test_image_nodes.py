"""
Integration tests for ComfyUI-style Image Generation Suite in ZFlow:
1. PromptStylerNode: Artistic style presets, camera framing, lighting, negative prompts
2. ImageGenNode: Pollinations Flux engine, Aspect Ratio dimensions, Seed control, Simulator
3. VisionNode: Image description, OCR extraction, tags analysis
4. End-to-end DAG execution: Input -> PromptStyler -> ImageGen -> Output
"""
import asyncio
import os
import sys
import unittest

SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server"))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from engine.context import ExecutionContext
from engine.graph import WorkflowGraph
from engine.runner import WorkflowRunner
from nodes.prompt_styler_node import PromptStylerNode
from nodes.image_gen_node import ImageGenNode
from nodes.vision_node import VisionNode
from nodes.input_node import InputNode
from nodes.output_node import OutputNode
import nodes


class TestImageNodes(unittest.IsolatedAsyncioTestCase):

    async def test_prompt_styler_cinematic(self):
        styler = PromptStylerNode()
        ctx = ExecutionContext(session_id="styler_test")
        
        output = await styler.execute(
            inputs={"base_prompt": "A solitary warrior on a misty mountain"},
            config={
                "style": "cinematic",
                "lighting": "dramatic",
                "camera": "wide_angle",
                "quality_preset": "high",
                "enable_negative_prompts": True
            },
            context=ctx
        )
        
        styled_prompt = output["styled_prompt"]
        neg_prompt = output["negative_prompt"]
        
        self.assertIn("A solitary warrior on a misty mountain", styled_prompt)
        self.assertIn("cinematic", styled_prompt.lower())
        self.assertIn("dramatic", styled_prompt.lower())
        self.assertTrue(len(neg_prompt) > 10)
        self.assertIn("blurry", neg_prompt.lower())
        self.assertTrue("wide-angle" in styled_prompt.lower() or "wide angle" in styled_prompt.lower())
        print("✓ PromptStyler (Cinematic) styled prompt:\n ", styled_prompt)
        print("✓ Negative prompt:", neg_prompt)

    async def test_prompt_styler_anime_and_cyberpunk(self):
        styler = PromptStylerNode()
        ctx = ExecutionContext(session_id="styler_styles_test")
        
        # Test anime
        out_anime = await styler.execute(
            inputs={"base_prompt": "School girl running with toast in mouth"},
            config={"style": "anime", "lighting": "natural"},
            context=ctx
        )
        self.assertIn("makoto shinkai", out_anime["styled_prompt"].lower())
        
        # Test cyberpunk
        out_cyber = await styler.execute(
            inputs={"base_prompt": "Street noodles stall"},
            config={"style": "cyberpunk", "lighting": "neon"},
            context=ctx
        )
        self.assertIn("neon", out_cyber["styled_prompt"].lower())
        print("✓ PromptStyler multiple style presets verified.")

    async def test_prompt_enchant_character_epic(self):
        styler = PromptStylerNode()
        ctx = ExecutionContext(session_id="enchant_char_test")
        
        output = await styler.execute(
            inputs={"base_prompt": "Cô gái samurai đứng dưới mưa hoa anh đào"},
            config={
                "enchant_level": "masterpiece_epic",
                "style": "cinematic",
                "lighting": "dramatic",
                "atmosphere": "floating_particles",
                "artist": "artgerm",
                "camera": "anamorphic",
                "enable_subject_detailing": True
            },
            context=ctx
        )
        
        styled = output["styled_prompt"]
        self.assertEqual(output["detected_subject"], "character")
        self.assertEqual(output["enchant_level"], "masterpiece_epic")
        self.assertIn("skin micro-texture", styled.lower())
        self.assertIn("unreal engine 5", styled.lower())
        self.assertIn("artgerm", styled.lower())
        self.assertIn("anamorphic", styled.lower())
        self.assertTrue(len(output["added_traits"]) >= 5)
        print("✓ Prompt Enchant (Epic Character) verified:\n ", styled[:180], "...")

    async def test_prompt_enchant_animal_and_nature(self):
        styler = PromptStylerNode()
        ctx = ExecutionContext(session_id="enchant_animal_test")
        
        output = await styler.execute(
            inputs={"base_prompt": "Chú mèo con ngủ trên ban công đầy nắng"},
            config={
                "enchant_level": "vivid",
                "style": "watercolor",
                "lighting": "golden_hour",
                "atmosphere": "golden_twilight"
            },
            context=ctx
        )
        
        styled = output["styled_prompt"]
        self.assertEqual(output["detected_subject"], "animal")
        self.assertIn("fur", styled.lower())
        self.assertIn("watercolor", styled.lower())
        self.assertIn("golden hour", styled.lower())
        print("✓ Prompt Enchant (Animal & Golden Twilight) verified.")

    async def test_image_gen_pollinations_flux(self):
        image_gen = ImageGenNode()
        ctx = ExecutionContext(session_id="image_gen_test")
        
        output = await image_gen.execute(
            inputs={"prompt": "Majestic golden eagle flying over snowy alps"},
            config={
                "provider": "flux_pollinations",
                "aspect_ratio": "16:9",
                "seed": 42
            },
            context=ctx
        )
        
        self.assertIn("image_url", output)
        self.assertTrue(output["image_url"].startswith("https://image.pollinations.ai/prompt/"))
        self.assertEqual(output["width"], 1344)
        self.assertEqual(output["height"], 768)
        self.assertEqual(output["aspect_ratio"], "16:9")
        self.assertEqual(output["seed"], 42)
        self.assertIn("![", output["markdown_image"])
        print("✓ ImageGen (Pollinations Flux 16:9) verified:", output["image_url"])

    async def test_image_gen_simulator_fallback(self):
        image_gen = ImageGenNode()
        ctx = ExecutionContext(session_id="image_gen_sim_test")
        
        output = await image_gen.execute(
            inputs={"prompt": "A modern minimalist coffee shop interior"},
            config={
                "provider": "simulator",
                "aspect_ratio": "1:1"
            },
            context=ctx
        )
        
        self.assertIn("image_url", output)
        self.assertEqual(output["width"], 1024)
        self.assertEqual(output["height"], 1024)
        self.assertEqual(output["aspect_ratio"], "1:1")
        self.assertTrue(output["is_mock"])
        print("✓ ImageGen (Simulator 1:1) verified:", output["image_url"])

    async def test_vision_node_analysis_and_ocr(self):
        vision = VisionNode()
        ctx = ExecutionContext(session_id="vision_test")
        
        # 1. OCR query
        output_ocr = await vision.execute(
            inputs={
                "image_url": "https://example.com/receipt.jpg",
                "query": "Đọc hóa đơn này và tính tổng tiền thanh toán"
            },
            config={"provider": "simulator"},
            context=ctx
        )
        self.assertIn("HÓA ĐƠN", output_ocr["description"])
        self.assertIn("VNĐ", output_ocr["description"])
        self.assertTrue(len(output_ocr["tags"]) > 0)
        
        # 2. General description query
        output_desc = await vision.execute(
            inputs={
                "image_url": "https://example.com/landscape.jpg",
                "query": "Bức ảnh này chụp gì?"
            },
            config={"provider": "simulator"},
            context=ctx
        )
        self.assertTrue(len(output_desc["description"]) > 20)
        print("✓ VisionNode (OCR & Scene description) verified.")

    async def test_dag_pipeline_image_flow(self):
        graph_dict = {
            "nodes": [
                {"id": "n_input", "type": "input", "title": "User Input", "data": {"config": {"default_query": "Cyberpunk street samurai"}}},
                {"id": "n_styler", "type": "prompt_styler", "title": "Prompt Styler", "data": {"config": {"style": "cyberpunk", "lighting": "neon"}}},
                {"id": "n_gen", "type": "image_gen", "title": "Flux Image Gen", "data": {"config": {"provider": "flux_pollinations", "aspect_ratio": "16:9"}}},
                {"id": "n_output", "type": "output", "title": "Final Output", "data": {"config": {}}}
            ],
            "edges": [
                {"id": "edge_1", "source": "n_input", "target": "n_styler", "sourceHandle": "query", "targetHandle": "base_prompt"},
                {"id": "edge_2", "source": "n_styler", "target": "n_gen", "sourceHandle": "styled_prompt", "targetHandle": "prompt"},
                {"id": "edge_3", "source": "n_gen", "target": "n_output", "sourceHandle": "markdown_image", "targetHandle": "response_text"}
            ]
        }
        graph = WorkflowGraph.from_dict(graph_dict)
        
        # Execute Runner
        runner = WorkflowRunner()
        context = ExecutionContext(session_id="dag_image_test", initial_variables={"input": "Cyberpunk street samurai"})
        result = await runner.run(graph, context)
        
        self.assertIsNotNone(result)
        final_output = result.get("final_output")
        self.assertIsNotNone(final_output)
        self.assertIn("![", final_output)
        self.assertIn("https://image.pollinations.ai/", final_output)
        print("✓ End-to-End Image Generation DAG pipeline executed successfully!")
        print("Final Rendered Output preview:\n", final_output)


if __name__ == "__main__":
    unittest.main()
