"""
Knowledge Base & Document Retrieval (RAG) Router.
Handles document indexing, semantic chunking, and hybrid vector search.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import time

from engine.knowledge_store import knowledge_store

router = APIRouter(tags=["Knowledge"])


class DocumentPayload(BaseModel):
    id: Optional[str] = None
    title: str
    content: str
    source_type: Optional[str] = "text"
    chunk_size: Optional[int] = 400
    chunk_overlap: Optional[int] = 60


class KnowledgeSearchPayload(BaseModel):
    query: str
    top_k: Optional[int] = 3
    min_score: Optional[float] = 0.15
    doc_filter: Optional[str] = None


@router.get("/api/knowledge/documents")
async def list_knowledge_documents():
    """Returns list of indexed documents in SQLite knowledge store."""
    return {"documents": knowledge_store.list_documents()}


@router.post("/api/knowledge/documents")
async def add_knowledge_document(payload: DocumentPayload):
    """Chunks, vectorizes, and indexes a text document or policy into SQLite knowledge store."""
    doc_id = payload.id or f"doc_{int(time.time() * 1000)}"
    res = knowledge_store.add_document(
        doc_id=doc_id,
        title=payload.title,
        content=payload.content,
        source_type=payload.source_type or "text",
        chunk_size=payload.chunk_size or 400,
        chunk_overlap=payload.chunk_overlap or 60
    )
    return res


@router.delete("/api/knowledge/documents/{doc_id}")
async def delete_knowledge_document(doc_id: str):
    """Deletes document and associated chunks from knowledge store."""
    success = knowledge_store.delete_document(doc_id)
    return {"status": "deleted" if success else "not_found", "doc_id": doc_id}


@router.post("/api/knowledge/search")
async def search_knowledge_documents(payload: KnowledgeSearchPayload):
    """Performs hybrid BM25 and TF-IDF semantic vector search across all indexed chunks."""
    results = knowledge_store.search(
        query=payload.query,
        top_k=payload.top_k or 3,
        min_score=payload.min_score or 0.15,
        doc_filter=payload.doc_filter
    )
    return {"query": payload.query, "results": results}
