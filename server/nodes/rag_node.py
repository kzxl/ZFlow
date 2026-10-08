"""
RAG Node (Knowledge Retrieval & Document Vector Search).
Retrieves relevant context snippets from the knowledge base using hybrid semantic search
and injects retrieved evidence into downstream Prompt and LLM nodes.
"""
from typing import Dict, Any, List, Optional
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext
from engine.knowledge_store import knowledge_store

@NodeRegistry.register
class RagNode(BaseNode):
    node_type = "rag"
    name = "Knowledge Retrieval (RAG)"
    category = "memory"
    description = "Tra cứu tài liệu nội bộ, chính sách, FAQ và trích xuất ngữ cảnh liên quan để bơm vào Prompt cho AI."
    icon = "BookOpen"

    inputs = [
        PortDef(name="query", data_type="string", label="Search Query", required=True)
    ]
    outputs = [
        PortDef(name="context", data_type="string", label="Formatted Knowledge Context"),
        PortDef(name="chunks", data_type="any", label="Retrieved Chunks List"),
        PortDef(name="top_score", data_type="number", label="Top Similarity Score"),
        PortDef(name="has_match", data_type="boolean", label="Has Relevant Match")
    ]

    config_schema = {
        "top_k": {
            "type": "number",
            "label": "Top Chunks to Retrieve",
            "min": 1,
            "max": 10,
            "step": 1,
            "default": 3
        },
        "min_score": {
            "type": "number",
            "label": "Min Similarity Score Threshold",
            "min": 0.05,
            "max": 1.0,
            "step": 0.05,
            "default": 0.20
        },
        "doc_filter": {
            "type": "string",
            "label": "Document Filter (Optional Doc ID)",
            "default": ""
        },
        "output_format": {
            "type": "select",
            "label": "Context Formatting",
            "options": ["numbered", "bullet", "raw_text"],
            "default": "numbered"
        },
        "custom_knowledge": {
            "type": "textarea",
            "label": "Inline Custom Knowledge (Fallback FAQ)",
            "default": ""
        }
    }

    async def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        query = str(
            inputs.get("query") 
            or inputs.get("input") 
            or context.get_variable("query") 
            or context.get_variable("input", "")
        ).strip()

        top_k = int(config.get("top_k", 3))
        min_score = float(config.get("min_score", 0.20))
        doc_filter = config.get("doc_filter") or None
        fmt = config.get("output_format", "numbered")
        custom_kw = config.get("custom_knowledge", "").strip()

        # 1. Search knowledge store
        results = knowledge_store.search(query=query, top_k=top_k, min_score=min_score, doc_filter=doc_filter)

        # 2. Append inline custom knowledge if provided and nothing or low matches
        if custom_kw and (not results or len(results) < top_k):
            results.append({
                "chunk_id": "inline_custom",
                "doc_id": "inline",
                "title": "Custom Knowledge",
                "content": custom_kw,
                "score": 0.99
            })

        has_match = len(results) > 0
        top_score = results[0]["score"] if has_match else 0.0

        # Format context output
        formatted_lines = []
        for idx, item in enumerate(results, start=1):
            title = item.get("title", f"Doc {idx}")
            content = item.get("content", "").strip()
            score_percent = int(item.get("score", 0.0) * 100)

            if fmt == "numbered":
                formatted_lines.append(f"[{idx}] (Tài liệu: {title} | Độ khớp: {score_percent}%):\n{content}")
            elif fmt == "bullet":
                formatted_lines.append(f"• **{title}**:\n{content}")
            else:
                formatted_lines.append(content)

        formatted_context = "\n\n".join(formatted_lines) if formatted_lines else "Không tìm thấy tài liệu phù hợp trong cơ sở tri thức."

        # Store in context variables for prompt interpolation
        context.set_variable("retrieved_context", formatted_context)
        context.set_variable("knowledge_context", formatted_context)
        context.set_variable("context_data", formatted_context)
        context.log("info", f"RAG retrieved {len(results)} chunks (top score: {top_score}) for query: '{query[:60]}'")

        return {
            "context": formatted_context,
            "chunks": results,
            "top_score": top_score,
            "has_match": has_match
        }
