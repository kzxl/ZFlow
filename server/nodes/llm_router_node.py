"""
LLM Intent Router Node for Semantic Multi-Branching in Chatbot Workflows.
Uses Large Language Models (LLMs) to analyze user intent and semantically route
execution to candidate branches based on natural language descriptions.
"""
from typing import Dict, Any, List, Optional
import json
import os
import re
import urllib.request
import urllib.error
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext

DEFAULT_ROUTES = [
    {
        "id": "sales",
        "name": "Tư vấn Bán hàng",
        "description": "Người dùng hỏi giá, chính sách chiết khấu, tìm hiểu tính năng sản phẩm hoặc có nhu cầu đặt mua."
    },
    {
        "id": "technical_support",
        "name": "Hỗ trợ Kỹ thuật",
        "description": "Người dùng gặp lỗi, ứng dụng bị crash, sự cố đăng nhập, lỗi kết nối hoặc cần hỗ trợ cài đặt."
    },
    {
        "id": "general_faq",
        "name": "Hỏi đáp Chung",
        "description": "Chào hỏi thông thường, hỏi thông tin công ty, giờ làm việc hoặc các câu hỏi tổng quát khác."
    }
]

@NodeRegistry.register
class LlmRouterNode(BaseNode):
    node_type = "llm_router"
    name = "LLM Intent Router"
    category = "logic"
    description = "Phân loại ý đồ người dùng bằng AI (LLM) và tự động rẽ nhánh luồng dữ liệu theo mô tả ngữ nghĩa."
    icon = "GitFork"

    inputs = [
        PortDef(name="input_text", data_type="string", label="Input Text / User Query", required=True)
    ]
    outputs = [
        PortDef(name="active_branch", data_type="string", label="Active Branch ID"),
        PortDef(name="reasoning", data_type="string", label="LLM Reasoning"),
        PortDef(name="confidence", data_type="number", label="Confidence Score")
    ]

    config_schema = {
        "provider": {
            "type": "select",
            "label": "AI Provider",
            "options": ["simulator", "openai_compatible", "ollama"],
            "default": "simulator"
        },
        "model": {
            "type": "select",
            "label": "Classification Model",
            "options": ["gpt-4o-mini", "gpt-4o", "llama3:8b", "custom"],
            "default": "gpt-4o-mini"
        },
        "temperature": {
            "type": "number",
            "label": "Temperature (Lower is more deterministic)",
            "min": 0.0,
            "max": 1.0,
            "step": 0.05,
            "default": 0.1
        },
        "routes": {
            "type": "textarea",
            "label": "Intent Routes (JSON List)",
            "default": json.dumps(DEFAULT_ROUTES, indent=2, ensure_ascii=False)
        },
        "fallback_branch": {
            "type": "string",
            "label": "Fallback Branch ID",
            "default": "default_branch"
        },
        "api_base": {
            "type": "string",
            "label": "Custom API Base URL",
            "default": "https://api.openai.com/v1"
        },
        "api_key": {
            "type": "password",
            "label": "API Key (or env OPENAI_API_KEY)",
            "default": ""
        }
    }

    async def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        text = str(
            inputs.get("input_text") 
            or inputs.get("input") 
            or context.get_variable("prompt") 
            or context.get_variable("query") 
            or context.get_variable("input", "")
        ).strip()

        # Parse routes
        raw_routes = config.get("routes")
        routes: List[Dict[str, Any]] = []
        if isinstance(raw_routes, str):
            try:
                routes = json.loads(raw_routes)
            except Exception:
                routes = DEFAULT_ROUTES
        elif isinstance(raw_routes, list):
            routes = raw_routes
        else:
            routes = DEFAULT_ROUTES

        if not routes:
            routes = DEFAULT_ROUTES

        fallback_id = config.get("fallback_branch", "default_branch")
        provider = config.get("provider", "simulator")
        api_key = config.get("api_key") or os.environ.get("OPENAI_API_KEY", "")

        selected_id = fallback_id
        reasoning = "Default route selected."
        confidence = 0.5

        # 1. Real LLM Execution (if OpenAI / Ollama configured with credentials)
        if provider == "openai_compatible" and api_key:
            selected_id, reasoning, confidence = await self._classify_with_openai(text, routes, config)
        elif provider == "ollama":
            selected_id, reasoning, confidence = await self._classify_with_ollama(text, routes, config)
        else:
            # 2. Smart Semantic Heuristic Simulator (Fast, offline, 0 cost)
            selected_id, reasoning, confidence = self._classify_heuristic(text, routes, fallback_id)

        # Ensure valid branch ID
        valid_ids = [r.get("id") for r in routes if r.get("id")]
        if selected_id not in valid_ids and selected_id != fallback_id:
            selected_id = fallback_id

        context.set_variable("llm_router.active_branch", selected_id)
        context.set_variable("llm_router.reasoning", reasoning)
        context.set_variable("llm_router.confidence", confidence)
        context.log("info", f"LLM Intent Router selected '{selected_id}' (conf: {confidence}): {reasoning}")

        # Construct result mapping payload to active branch handle
        result: Dict[str, Any] = {
            "active_branch": selected_id,
            "active_route": selected_id,
            "reasoning": reasoning,
            "confidence": confidence,
            "input_text": text,
            "default_branch": text if selected_id == fallback_id else None
        }

        for r in routes:
            r_id = r.get("id")
            if r_id:
                result[r_id] = text if r_id == selected_id else None

        result[selected_id] = text
        return result

    def _classify_heuristic(
        self, text: str, routes: List[Dict[str, Any]], fallback_id: str
    ) -> tuple[str, str, float]:
        """
        Calculates lexical-semantic relevance score between user text and route descriptions.
        """
        if not text:
            return fallback_id, "No input text provided.", 0.0

        text_lower = text.lower()
        best_route = None
        highest_score = 0

        # Keywords dictionary for Vietnamese & English common terms
        domain_keywords = {
            "sales": ["giá", "mua", "báo giá", "chi phí", "bao nhiêu", "tiền", "gói", "đặt hàng", "khuyến mãi", "ưu đãi", "sales", "buy", "price", "cost", "quote"],
            "technical_support": ["lỗi", "hỏng", "không được", "sự cố", "bug", "crash", "văng", "kẹt", "hướng dẫn", "cài đặt", "login", "đăng nhập", "error", "issue", "help", "support"],
            "general_faq": ["chào", "hello", "hi", "tên gì", "ở đâu", "địa chỉ", "liên hệ", "công ty", "ai", "là ai", "about", "contact", "info"]
        }

        for r in routes:
            r_id = r.get("id", "")
            r_name = r.get("name", "").lower()
            r_desc = r.get("description", "").lower()

            score = 0
            # Direct name/desc matches
            for word in re.findall(r'\w+', r_name + " " + r_desc):
                if len(word) > 2 and word in text_lower:
                    score += 2

            # Specialized domain keywords match
            if r_id in domain_keywords:
                for kw in domain_keywords[r_id]:
                    if kw in text_lower:
                        score += 3

            if score > highest_score:
                highest_score = score
                best_route = r

        if best_route and highest_score >= 2:
            conf = min(0.6 + (highest_score * 0.08), 0.98)
            return (
                best_route["id"],
                f"Phát hiện ý đồ phù hợp với '{best_route.get('name', best_route['id'])}' dựa trên ngữ cảnh.",
                round(conf, 2)
            )

        # Fallback to first route if general or fallback_id
        if routes:
            default_candidate = routes[-1]["id"]
            return default_candidate, "Không khớp rõ ràng các nhánh chuyên biệt, chuyển sang nhánh mặc định.", 0.55

        return fallback_id, "Không tìm thấy nhánh phù hợp.", 0.3

    async def _classify_with_openai(
        self, text: str, routes: List[Dict[str, Any]], config: Dict[str, Any]
    ) -> tuple[str, str, float]:
        """
        Sends structured classification prompt to OpenAI-compatible chat endpoint.
        """
        api_base = config.get("api_base", "https://api.openai.com/v1").rstrip("/")
        api_key = config.get("api_key") or os.environ.get("OPENAI_API_KEY", "")
        model = config.get("model", "gpt-4o-mini")

        route_options_str = "\n".join(
            [f"- ID: '{r['id']}', Tên: '{r.get('name', r['id'])}', Mô tả: '{r.get('description', '')}'" for r in routes]
        )

        system_prompt = (
            "Bạn là bộ phân loại ý đồ (Intent Classifier) chuyên nghiệp.\n"
            "Nhiệm vụ: Phân tích câu nói của người dùng và chọn duy nhất 1 ID nhánh đích phù hợp nhất.\n"
            "Các nhánh có thể chọn:\n"
            f"{route_options_str}\n\n"
            "Trả về kết quả DUY NHẤT dưới định dạng JSON sau:\n"
            '{"route_id": "<ID_nhánh>", "confidence": 0.95, "reasoning": "<Lý do ngắn gọn>"}'
        )

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            "temperature": float(config.get("temperature", 0.1)),
            "response_format": {"type": "json_object"}
        }

        try:
            req = urllib.request.Request(
                f"{api_base}/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                return (
                    parsed.get("route_id", routes[0]["id"]),
                    parsed.get("reasoning", "LLM classified route."),
                    float(parsed.get("confidence", 0.9))
                )
        except Exception as e:
            # Fallback to heuristic
            return self._classify_heuristic(text, routes, config.get("fallback_branch", "default_branch"))

    async def _classify_with_ollama(
        self, text: str, routes: List[Dict[str, Any]], config: Dict[str, Any]
    ) -> tuple[str, str, float]:
        """
        Sends classification request to local Ollama instance.
        """
        api_base = config.get("api_base", "http://127.0.0.1:11434").rstrip("/")
        model = config.get("model", "llama3:8b")
        if "/v1" in api_base:
            api_base = api_base.replace("/v1", "")

        route_options_str = "\n".join(
            [f"- ID: '{r['id']}', Mô tả: '{r.get('description', '')}'" for r in routes]
        )
        prompt = (
            f"Phân loại câu sau vào 1 trong các ID: {[r['id'] for r in routes]}.\n"
            f"Mô tả các ID:\n{route_options_str}\n"
            f"Câu người dùng: \"{text}\"\n"
            "Chỉ trả về JSON: {\"route_id\": \"<ID>\", \"confidence\": 0.9, \"reasoning\": \"<lý do>\"}"
        )

        try:
            req = urllib.request.Request(
                f"{api_base}/api/generate",
                data=json.dumps({"model": model, "prompt": prompt, "format": "json", "stream": False}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                parsed = json.loads(data.get("response", "{}"))
                return (
                    parsed.get("route_id", routes[0]["id"]),
                    parsed.get("reasoning", "Ollama classified route."),
                    float(parsed.get("confidence", 0.85))
                )
        except Exception:
            return self._classify_heuristic(text, routes, config.get("fallback_branch", "default_branch"))
