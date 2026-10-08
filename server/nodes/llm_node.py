"""
LLM Node for ZFlow.
Supports OpenAI-compatible APIs, local Ollama endpoints, and a high-fidelity simulator mode.
Streams tokens in real time via SSE.
"""
from typing import Dict, Any, AsyncGenerator
import asyncio
import json
import httpx
import os
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext

@NodeRegistry.register
class LlmNode(BaseNode):
    node_type = "llm"
    name = "LLM Engine"
    category = "llm"
    description = "Executes LLM inference with token-by-token streaming, custom system prompts, and temperature controls."
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
            "type": "string",
            "label": "Model Name",
            "default": "gpt-4o-mini"
        },
        "temperature": {
            "type": "number",
            "label": "Temperature",
            "min": 0.0,
            "max": 2.0,
            "step": 0.1,
            "default": 0.7
        },
        "max_tokens": {
            "type": "number",
            "label": "Max Tokens",
            "default": 1024
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

        # If provider is simulator or no api key for openai, run realistic simulator
        if provider == "simulator" or (provider == "openai_compatible" and not config.get("api_key") and not os.environ.get("OPENAI_API_KEY")):
            async for chunk in self._stream_simulator(prompt, system_prompt, config):
                yield chunk
            return

        # Real API streaming (OpenAI / Ollama / vLLM)
        api_base = config.get("api_base", "https://api.openai.com/v1").rstrip("/")
        api_key = config.get("api_key") or os.environ.get("OPENAI_API_KEY", "")
        model = config.get("model", "gpt-4o-mini")
        temperature = float(config.get("temperature", 0.7))

        if provider == "ollama" and "/v1" not in api_base:
            api_base = f"{api_base}/v1"

        messages = [{"role": "system", "content": system_prompt}]
        for turn in history[-6:]: # Keep last 6 turns
            messages.append({"role": turn.get("role", "user"), "content": turn.get("content", "")})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}" if api_key else ""
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", f"{api_base}/chat/completions", headers=headers, json=payload) as response:
                    if response.status_code != 200:
                        err_text = await response.aread()
                        yield {"type": "token", "token": f"[API Error {response.status_code}: {err_text.decode('utf-8')}]"}
                        return

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
                                yield {"type": "token", "token": token}
                        except Exception:
                            continue
        except Exception as e:
            yield {"type": "token", "token": f"[LlmNode Connection Error: {str(e)}]"}

    async def _stream_simulator(self, prompt: str, system_prompt: str, config: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Simulates an intelligent LLM response for rapid local workflow prototyping and testing.
        """
        model = config.get("model", "gpt-4o-mini")
        
        # Build contextual simulation
        response_body = (
            f"Chào bạn! Tôi đang xử lý yêu cầu qua ZFlow Engine ({model}).\n\n"
            f"**Nội dung tiếp nhận:** \"{prompt}\"\n\n"
            f"**Quy trình đã thực thi:**\n"
            f"- Đã nạp chỉ thị hệ thống: *\"{system_prompt[:60]}...\"*\n"
            f"- Các biến ngữ cảnh và lịch sử hội thoại đã được liên kết chính xác qua các Node.\n"
            f"- Luồng dữ liệu hoàn tất chuẩn hóa và đang truyền tải kết quả qua Server-Sent Events (SSE).\n\n"
            f"Hệ thống workflow đã sẵn sàng để tích hợp thêm các Tool, Router hoặc kết nối trực tiếp đến Ollama / OpenAI API key!"
        )

        # Stream word by word with sub-millisecond to ~15ms delay
        words = response_body.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            yield {"type": "token", "token": chunk}
            await asyncio.sleep(0.015)
