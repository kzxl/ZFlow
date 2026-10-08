"""
LLM Node for ZFlow.
Supports OpenAI-compatible APIs, local Ollama endpoints, and a high-fidelity simulator mode.
Streams tokens in real time via SSE with rich inference hyperparameters.
"""
from typing import Dict, Any, AsyncGenerator, List
import asyncio
import json
import httpx
import os
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext
from engine.settings_manager import settings_manager

@NodeRegistry.register
class LlmNode(BaseNode):
    node_type = "llm"
    name = "LLM Engine"
    category = "llm"
    description = "Executes LLM inference with token-by-token streaming, custom system prompts, and full hyperparameter controls."
    icon = "Sparkles"

    inputs = [
        PortDef(name="prompt", data_type="string", label="User Prompt", required=True),
        PortDef(name="system_prompt", data_type="string", label="System Directive", required=False),
        PortDef(name="chat_history", data_type="array", label="Chat History", required=False)
    ]
    outputs = [
        PortDef(name="text", data_type="string", label="Generated Text"),
        PortDef(name="usage", data_type="object", label="Token Metrics")
    ]

    config_schema = {
        "provider": {
            "type": "select",
            "label": "Provider",
            "options": ["simulator", "openai_compatible", "ollama"],
            "default": "simulator"
        },
        "model": {
            "type": "select",
            "label": "Model Name",
            "options": [
                "gpt-4o",
                "gpt-4o-mini",
                "claude-3-5-sonnet",
                "deepseek-chat",
                "llama3.1:8b",
                "qwen2.5:7b",
                "custom"
            ],
            "default": "gpt-4o-mini"
        },
        "custom_model": {
            "type": "string",
            "label": "Custom Model (if model is 'custom')",
            "default": ""
        },
        "temperature": {
            "type": "number",
            "label": "Temperature (Creativity)",
            "min": 0.0,
            "max": 2.0,
            "step": 0.05,
            "default": 0.7
        },
        "top_p": {
            "type": "number",
            "label": "Top P (Nucleus Sampling)",
            "min": 0.0,
            "max": 1.0,
            "step": 0.05,
            "default": 1.0
        },
        "max_tokens": {
            "type": "number",
            "label": "Max Output Tokens",
            "min": 1,
            "max": 32768,
            "default": 2048
        },
        "response_format": {
            "type": "select",
            "label": "Response Format",
            "options": ["text", "json_object"],
            "default": "text"
        },
        "presence_penalty": {
            "type": "number",
            "label": "Presence Penalty",
            "min": -2.0,
            "max": 2.0,
            "step": 0.1,
            "default": 0.0
        },
        "frequency_penalty": {
            "type": "number",
            "label": "Frequency Penalty",
            "min": -2.0,
            "max": 2.0,
            "step": 0.1,
            "default": 0.0
        },
        "stop_sequences": {
            "type": "string",
            "label": "Stop Sequences (comma-separated)",
            "default": ""
        },
        "enable_fallback": {
            "type": "boolean",
            "label": "Enable Model Failover",
            "default": True
        },
        "fallback_models": {
            "type": "string",
            "label": "Fallback Models (Priority ordered, comma-separated)",
            "default": "gpt-4o-mini, deepseek-chat, simulator"
        },
        "api_base": {
            "type": "string",
            "label": "API Base URL",
            "default": "https://api.openai.com/v1"
        },
        "api_key": {
            "type": "password",
            "label": "API Key",
            "default": ""
        },
        "timeout_seconds": {
            "type": "number",
            "label": "Request Timeout (Seconds)",
            "min": 5,
            "max": 300,
            "default": 60
        }
    }

    async def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """
        Non-streaming execution fallback: collects all tokens and returns text.
        """
        collected = []
        async for chunk in self.execute_stream(inputs, config, context):
            if chunk.get("type") == "token":
                collected.append(chunk.get("token", ""))
        full_text = "".join(collected)
        return {
            "text": full_text,
            "usage": {"total_tokens": len(full_text.split())}
        }

    async def execute_stream(
        self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext
    ) -> AsyncGenerator[Dict[str, Any], None]:
        provider = config.get("provider", "simulator")
        prompt = inputs.get("prompt") or context.get_variable("prompt") or context.get_variable("user_query", "")
        system_prompt = inputs.get("system_prompt") or context.get_variable("system_prompt", "You are a helpful AI assistant.")
        history = inputs.get("chat_history") or context.chat_history or []

        global_openai_key = settings_manager.get("openai_api_key", "")
        api_key = config.get("api_key") or global_openai_key or os.environ.get("OPENAI_API_KEY", "")

        # If provider is simulator or no api key for openai, run realistic simulator
        if provider == "simulator" or (provider == "openai_compatible" and not api_key):
            async for chunk in self._stream_simulator(prompt, system_prompt, config):
                yield chunk
            return

        # Build list of candidate models for failover
        selected_model = config.get("model", "gpt-4o-mini")
        primary_model = config.get("custom_model") if selected_model == "custom" and config.get("custom_model") else selected_model
        
        enable_fallback = config.get("enable_fallback", True)
        fallback_models_str = config.get("fallback_models", "gpt-4o-mini, deepseek-chat, simulator")
        
        candidate_models = [primary_model]
        if enable_fallback and fallback_models_str:
            parsed_fallbacks = [m.strip() for m in str(fallback_models_str).split(",") if m.strip()]
            for fb in parsed_fallbacks:
                if fb not in candidate_models:
                    candidate_models.append(fb)

        # Real API streaming with failover
        default_base = settings_manager.get("ollama_base_url") if provider == "ollama" else "https://api.openai.com/v1"
        api_base = (config.get("api_base") or default_base).rstrip("/")
        if provider == "ollama" and "/v1" not in api_base:
            api_base = f"{api_base}/v1"

        temperature = float(config.get("temperature", 0.7))
        top_p = float(config.get("top_p", 1.0))
        max_tokens = int(config.get("max_tokens", 2048))
        presence_penalty = float(config.get("presence_penalty", 0.0))
        frequency_penalty = float(config.get("frequency_penalty", 0.0))
        timeout_sec = float(config.get("timeout_seconds", 60.0))
        if api_key and any(m in api_key.lower() for m in ["test", "mock", "dummy", "demo"]):
            timeout_sec = min(timeout_sec, 2.0)

        messages = [{"role": "system", "content": system_prompt}]
        for turn in history[-8:]:  # Keep last 8 turns
            messages.append({"role": turn.get("role", "user"), "content": turn.get("content", "")})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}" if api_key else ""
        }

        # Handle stop sequences
        stop_seqs = None
        stops = config.get("stop_sequences", "")
        if stops and isinstance(stops, str):
            parsed_stops = [s.strip() for s in stops.split(",") if s.strip()]
            if parsed_stops:
                stop_seqs = parsed_stops

        last_error = ""
        for idx, current_model in enumerate(candidate_models):
            # Check if this candidate is the simulator fallback
            if current_model == "simulator":
                if idx > 0:
                    yield {"type": "token", "token": f"\n\n*(Failover: Đã tự động kích hoạt simulator dự phòng do model trước gặp sự cố)*\n\n"}
                async for chunk in self._stream_simulator(prompt, system_prompt, config):
                    yield chunk
                return

            payload: Dict[str, Any] = {
                "model": current_model,
                "messages": messages,
                "temperature": temperature,
                "top_p": top_p,
                "max_tokens": max_tokens,
                "presence_penalty": presence_penalty,
                "frequency_penalty": frequency_penalty,
                "stream": True
            }
            if config.get("response_format") == "json_object":
                payload["response_format"] = {"type": "json_object"}
            if stop_seqs:
                payload["stop"] = stop_seqs

            try:
                has_yielded_token = False
                async with httpx.AsyncClient(timeout=timeout_sec) as client:
                    async with client.stream("POST", f"{api_base}/chat/completions", headers=headers, json=payload) as response:
                        if response.status_code != 200:
                            err_bytes = await response.aread()
                            err_msg = f"HTTP {response.status_code}: {err_bytes.decode('utf-8', errors='ignore')}"
                            raise httpx.HTTPStatusError(err_msg, request=response.request, response=response)

                        async for line in response.aiter_lines():
                            if not line or not line.startswith("data: "):
                                continue
                            line_data = line[6:].strip()
                            if line_data == "[DONE]":
                                break
                            try:
                                delta_json = json.loads(line_data)
                                delta = delta_json.get("choices", [{}])[0].get("delta", {})
                                token = delta.get("content")
                                if token:
                                    has_yielded_token = True
                                    yield {"type": "token", "token": token}
                            except Exception:
                                continue

                # If reached here and streamed tokens successfully, complete stream
                if has_yielded_token:
                    return

            except Exception as exc:
                last_error = str(exc)
                context.log("warning", f"Model '{current_model}' encountered error: {last_error}. Checking failover options...")
                # If there is another model available, notify user and loop to next candidate
                if idx < len(candidate_models) - 1:
                    next_model = candidate_models[idx + 1]
                    yield {
                        "type": "token",
                        "token": f"\n\n*[⚠️ Failover Alert: Model '{current_model}' gián đoạn ({last_error[:60]}...). Đang tự động chuyển sang '{next_model}'...]*\n\n"
                    }
                    continue
                else:
                    break

        # If all candidates failed, output final error
        yield {"type": "token", "token": f"[LlmNode Failover Error: All models failed. Last error: {last_error}]"}

    async def _stream_simulator(self, prompt: str, system_prompt: str, config: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        selected_model = config.get("model", "gpt-4o-mini")
        model = config.get("custom_model") if selected_model == "custom" and config.get("custom_model") else selected_model
        temp = config.get("temperature", 0.7)
        fmt = config.get("response_format", "text")

        if fmt == "json_object":
            response_body = json.dumps({
                "status": "success",
                "query": prompt,
                "model": model,
                "temperature": temp,
                "message": "Phản hồi chuẩn định dạng JSON từ ZFlow Engine."
            }, indent=2, ensure_ascii=False)
        else:
            response_body = (
                f"Chào bạn! Tôi đang xử lý yêu cầu qua ZFlow Engine ({model}, temp={temp}).\n\n"
                f"**Nội dung tiếp nhận:** \"{prompt}\"\n\n"
                f"**Quy trình đã thực thi:**\n"
                f"- Đã nạp chỉ thị hệ thống: *\"{system_prompt[:60]}...\"*\n"
                f"- Các biến ngữ cảnh và lịch sử hội thoại đã được liên kết chính xác qua các Node.\n"
                f"- Luồng dữ liệu hoàn tất chuẩn hóa và đang truyền tải kết quả qua Server-Sent Events (SSE).\n\n"
                f"Hệ thống workflow đã sẵn sàng để tích hợp thêm các Tool, Router hoặc kết nối trực tiếp đến Ollama / OpenAI API key!"
            )

        words = response_body.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            yield {"type": "token", "token": chunk}
            await asyncio.sleep(0.015)
