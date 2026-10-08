"""
System 1 Fast Reflex & Intuitive Decision Engine.
Inspired by Daniel Kahneman's cognitive framework ("Thinking, Fast and Slow").
Provides sub-millisecond (< 1ms) heuristic decisions, security guardrails,
fast chitchat reflexes, and smart escalation to System 2 (deep reasoning LLM).
"""
import re
import time
import json
from typing import Dict, Any, List, Optional, Tuple
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext

# 1. Guardrail & Security Heuristics (Highest Priority)
GUARDRAIL_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"bypass\s+(the\s+)?(system|filter|guardrail|rules)",
    r"act\s+as\s+DAN\b",
    r"you\s+are\s+now\s+in\s+developer\s+mode",
    r"reveal\s+(your\s+)?(system\s+prompt|secret\s+key|api\s+key)",
    r"drop\s+table\b",
    r"delete\s+from\s+[a-z0-9_]+",
    r"<script\b[^>]*>",
    r"bỏ\s+qua\s+(toàn\s+bộ\s+)?chỉ\s+thị\s+trước",
    r"tiết\s+lộ\s+prompt\s+hệ\s+thống",
    r"hack\s+hệ\s+thống"
]

# 2. System 1 Fast Reflex Chitchat & FAQ Patterns
FAST_REFLEX_DICTIONARY = [
    {
        "patterns": [
            r"^(xin\s+)?chào(\s+bạn|\s+ai|\s+bot|\s+zflow)?([!.,?~]*)$",
            r"^(hello|hi|hey|alo)\b([!.,?~]*)$"
        ],
        "reply": "Chào bạn! Tôi là ZFlow AI Assistant. Tôi có thể hỗ trợ gì cho bạn hôm nay?",
        "intent": "greeting"
    },
    {
        "patterns": [
            r"^(cảm\s+ơn|thanks?|thank\s+you|cảm\s+ơn\s+bạn)(\s+nhiều)?([!.,?~]*)$"
        ],
        "reply": "Rất vui được hỗ trợ bạn! Nếu bạn có bất kỳ câu hỏi nào khác, đừng ngần ngại nhắn cho tôi nhé!",
        "intent": "gratitude"
    },
    {
        "patterns": [
            r"^(tạm\s+biệt|bye|goodbye|hẹn\s+gặp\s+lại)([!.,?~]*)$"
        ],
        "reply": "Tạm biệt bạn! Chúc bạn một ngày tốt lành và làm việc thật hiệu quả!",
        "intent": "farewell"
    },
    {
        "patterns": [
            r"^(bạn\s+là\s+ai|who\s+are\s+you|giới\s+thiệu\s+về\s+bạn)([!.,?~]*)$"
        ],
        "reply": "Tôi là trợ lý ảo được điều phối bởi ZFlow Engine — nền tảng trực quan hóa luồng công việc AI Workflow & Cognitive Architecture đa tác tử.",
        "intent": "identity"
    },
    {
        "patterns": [
            r"^(/help|trợ\s+giúp|hướng\s+dẫn(\s+sử\s+dụng)?)([!.,?~]*)$"
        ],
        "reply": (
            "📋 **Hướng dẫn Nhanh:**\n"
            "- Nhắn tin trực tiếp để kiểm tra luồng phản hồi.\n"
            "- Bấm nút 🪄 **Magic Enchant** cạnh ô chat để phù phép câu prompt chi tiết chuẩn 8K.\n"
            "- Các câu chào hỏi thông thường sẽ được **System 1** xử lý tức thời (< 0.2ms).\n"
            "- Các câu hỏi phân tích, lập trình hoặc giải toán sẽ tự động được điều chuyển lên **System 2**."
        ),
        "intent": "help"
    },
    {
        "patterns": [
            r"^(/ping|ping)([!.,?~]*)$"
        ],
        "reply": "🏓 Pong! Phản xạ System 1 phản hồi tức thời.",
        "intent": "ping"
    }
]

# 3. System 2 Escalation Indicators (Complex Tasks)
SYSTEM_2_INDICATORS = [
    r"\b(tính|toán|giải|phương\s+trình|math|calculate)\b",
    r"[\+\-\*\/\^]{1,}\s*\d+",  # Mathematical expressions like 1500000 * 12
    r"\b(code|lập\s+trình|python|javascript|typescript|c\#|sql|debug|refactor|function|class)\b",
    r"\b(tại\s+sao|vì\s+sao|so\s+sánh|phân\s+tích|đánh\s+giá|ưu\s+nhược\s+điểm|kế\s+hoạch|chiến\s+lược)\b",
    r"\b(tạo\s+ảnh|vẽ|generate\s+image|prompt\s+styler|flux|dall-e|comfyui)\b",
    r"\b(chính\s+sách|bảo\s+hành|báo\s+giá|hợp\s+đồng|tài\s+liệu|knowledge)\b"
]


@NodeRegistry.register
class System1ReflexNode(BaseNode):
    node_type = "system1_reflex"
    name = "System 1: Fast Reflex"
    category = "logic"
    description = "Quyết định tức thì (< 1ms): Phản xạ bảo mật Guardrail, trả lời nhanh Chitchat/FAQ không tốn token, hoặc tự động chuyển tiếp câu hỏi khó lên System 2 (LLM suy luận sâu)."
    icon = "Zap"

    inputs = [
        PortDef(name="query", data_type="string", label="User Query / Input", required=True)
    ]
    outputs = [
        PortDef(name="fast_reply", data_type="string", label="⚡ Fast Reply (System 1)"),
        PortDef(name="system_2", data_type="string", label="🧠 Escalate (System 2)"),
        PortDef(name="blocked", data_type="string", label="🛡️ Guardrail Block"),
        PortDef(name="decision", data_type="string", label="Decision Name"),
        PortDef(name="reply", data_type="string", label="Direct Response Text"),
        PortDef(name="confidence", data_type="number", label="Confidence Score"),
        PortDef(name="reason", data_type="string", label="Decision Reason"),
        PortDef(name="latency_ms", data_type="number", label="Reflex Latency (ms)")
    ]

    config_schema = {
        "enable_guardrails": {
            "type": "boolean",
            "label": "Enable Fast Security Guardrails",
            "default": True
        },
        "enable_fast_chitchat": {
            "type": "boolean",
            "label": "Enable Instant Chitchat Reflex (< 1ms)",
            "default": True
        },
        "confidence_threshold": {
            "type": "number",
            "label": "Confidence Threshold (0.0 - 1.0)",
            "default": 0.85,
            "min": 0.5,
            "max": 1.0,
            "step": 0.05
        },
        "custom_rules": {
            "type": "textarea",
            "label": "Custom Rules (JSON format: [{\"pattern\": \"regex\", \"branch\": \"fast_reply|system_2\", \"reply\": \"...\"}])",
            "default": "[]"
        },
        "default_action": {
            "type": "select",
            "label": "Default Fallback Action",
            "options": ["system_2", "fast_reply"],
            "default": "system_2"
        }
    }

    async def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        start_time = time.perf_counter()
        
        query = str(
            inputs.get("query")
            or inputs.get("input")
            or context.get_variable("query")
            or context.get_variable("input", "")
        ).strip()

        enable_guardrails = config.get("enable_guardrails", True)
        enable_chitchat = config.get("enable_fast_chitchat", True)
        conf_threshold = float(config.get("confidence_threshold", 0.85))
        default_action = config.get("default_action", "system_2")
        custom_rules_raw = config.get("custom_rules", "[]")

        active_branch = default_action
        reply = ""
        confidence = 0.5
        reason = "No fast pattern matched. Delegating to System 2 deep reasoning."

        # -------------------------------------------------------------
        # Tầng 1: Security Guardrail Check (< 0.1ms)
        # -------------------------------------------------------------
        if enable_guardrails:
            for pat in GUARDRAIL_PATTERNS:
                if re.search(pat, query, re.IGNORECASE):
                    active_branch = "blocked"
                    reply = "⚠️ Yêu cầu bị chặn bởi System 1 Guardrail (Phát hiện mẫu câu vi phạm chính sách an toàn hoặc can thiệp hệ thống)."
                    confidence = 0.99
                    reason = f"Security violation pattern detected: '{pat}'"
                    break

        # -------------------------------------------------------------
        # Tầng 2: Custom User-defined Reflex Rules
        # -------------------------------------------------------------
        if active_branch != "blocked" and custom_rules_raw:
            try:
                rules = json.loads(custom_rules_raw) if isinstance(custom_rules_raw, str) else custom_rules_raw
                if isinstance(rules, list):
                    for r in rules:
                        pat = r.get("pattern", "")
                        if pat and re.search(pat, query, re.IGNORECASE):
                            active_branch = r.get("branch", "fast_reply")
                            reply = r.get("reply", "")
                            confidence = float(r.get("confidence", 0.95))
                            reason = f"Matched custom rule pattern '{pat}'"
                            break
            except Exception as e:
                context.log("warn", f"System 1 failed to parse custom rules: {e}")

        clean_q = re.sub(r'[\s!.,?~…]+$', '', query).strip()

        # -------------------------------------------------------------
        # Tầng 3: Chitchat & Greeting Instant Reflex (< 0.2ms)
        # -------------------------------------------------------------
        if active_branch != "blocked" and active_branch != "fast_reply" and enable_chitchat:
            for item in FAST_REFLEX_DICTIONARY:
                for pat in item["patterns"]:
                    if re.search(pat, query, re.IGNORECASE) or re.search(pat, clean_q, re.IGNORECASE):
                        active_branch = "fast_reply"
                        reply = item["reply"]
                        confidence = 0.98
                        reason = f"System 1 Chitchat reflex: #{item['intent']}"
                        break
                if active_branch == "fast_reply":
                    break

        # -------------------------------------------------------------
        # Tầng 4: System 2 Escalation Filter (Heuristics for Complexity)
        # -------------------------------------------------------------
        if active_branch != "blocked" and active_branch != "fast_reply":
            for pat in SYSTEM_2_INDICATORS:
                if re.search(pat, query, re.IGNORECASE):
                    active_branch = "system_2"
                    confidence = 0.95
                    reason = f"Complex task indicator detected ('{pat}'). Escalate to System 2."
                    break

        # -------------------------------------------------------------
        # Tầng 5: Confidence Check vs Threshold
        # -------------------------------------------------------------
        if confidence < conf_threshold and active_branch != "blocked":
            active_branch = default_action
            reason = f"Confidence {confidence:.2f} < threshold {conf_threshold:.2f}. Falling back to {default_action}."

        latency_ms = round((time.perf_counter() - start_time) * 1000, 3)

        # Store in context variables
        context.set_variable("system1_decision", active_branch)
        context.set_variable("system1_confidence", confidence)
        context.set_variable("system1_latency_ms", latency_ms)
        if reply:
            context.set_variable("system1_reply", reply)
            if active_branch == "fast_reply":
                context.set_variable("reply", reply)
                context.set_variable("final_output", reply)

        context.log("info", f"System 1 evaluated in {latency_ms}ms -> {active_branch} ({reason})")

        return {
            "active_branch": active_branch,
            "decision": active_branch,
            "reply": reply,
            "fast_reply": reply if active_branch == "fast_reply" else "",
            "system_2": query if active_branch == "system_2" else "",
            "blocked": reply if active_branch == "blocked" else "",
            "confidence": confidence,
            "reason": reason,
            "latency_ms": latency_ms
        }
