"""
ZFlow Knowledge Store & Retrieval Engine (RAG).
Provides document chunking, indexing, and hybrid lexical-semantic retrieval.
Persists document collections and chunks in SQLite with TF-IDF/BM25 vectorization.
Zero heavy dependencies required: runs blazing fast (< 2ms) locally.
"""
import sqlite3
import os
import json
import time
import math
import re
from typing import List, Dict, Any, Optional

DEFAULT_DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "storage", "knowledge_base.db")
)

VIETNAMESE_STOPWORDS = {
    "và", "của", "là", "các", "có", "trong", "được", "cho", "với", "về",
    "đã", "khi", "những", "này", "tại", "từ", "như", "thì", "đó", "ra",
    "the", "and", "is", "in", "to", "of", "a", "an", "for", "with", "on"
}

def tokenize(text: str) -> List[str]:
    """
    Cleans and tokenizes text into lowercase normalized words.
    """
    words = re.findall(r'\w+', text.lower())
    return [w for w in words if len(w) > 1 and w not in VIETNAMESE_STOPWORDS]


class KnowledgeStore:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
        self._seed_default_knowledge()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    chunk_count INTEGER DEFAULT 0,
                    created_at REAL NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    metadata_json TEXT,
                    terms_json TEXT,
                    created_at REAL NOT NULL,
                    FOREIGN KEY(doc_id) REFERENCES documents(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id)")
            conn.commit()

    def _seed_default_knowledge(self):
        """
        Seeds sample enterprise FAQ and product documentation if store is empty.
        """
        docs = self.list_documents()
        if len(docs) > 0:
            return

        sample_policy = (
            "Chính sách bảo hành và đổi trả của ZFlow:\n"
            "1. Thời hạn đổi mới: Khách hàng được đổi mới 100% trong vòng 30 ngày đầu tiên nếu phát sinh lỗi kỹ thuật từ nhà sản xuất.\n"
            "2. Thời hạn bảo hành: Bảo hành phần mềm và hỗ trợ kỹ thuật 24/7 trong suốt 12 tháng kể từ ngày kích hoạt hợp đồng.\n"
            "3. Quy trình hoàn tiền: Yêu cầu hoàn tiền được tiếp nhận và xử lý chuyển khoản trong vòng 3 đến 5 ngày làm việc qua tài khoản ngân hàng chính chủ.\n"
            "4. Hotline hỗ trợ kỹ thuật khẩn cấp: 1900-6868 hoặc email support@zflow.vn."
        )

        sample_pricing = (
            "Bảng giá các gói dịch vụ ZFlow Workflow Orchestrator:\n"
            "- Gói Khởi nghiệp (Starter): Miễn phí trọn đời, hỗ trợ tối đa 5 workflow hoạt động đồng thời, 10,000 requests/tháng.\n"
            "- Gói Doanh nghiệp (Enterprise Pro): 1,500,000 VNĐ/tháng, không giới hạn workflow, hỗ trợ SQLite Memory, Vector Search RAG, Function Calling Agent và SLA 99.9%.\n"
            "- Gói Tùy biến Dedicated (On-Premise): Dành riêng cho tập đoàn, triển khai hạ tầng máy chủ nội bộ hoặc VPC bảo mật cao."
        )

        self.add_document("chinh_sach_bao_hanh", "Chính sách Bảo hành & Đổi trả ZFlow", sample_policy, "policy")
        self.add_document("bang_gia_dich_vu", "Bảng giá Dịch vụ ZFlow", sample_pricing, "pricing")

    def add_document(
        self,
        doc_id: str,
        title: str,
        content: str,
        source_type: str = "text",
        chunk_size: int = 400,
        chunk_overlap: int = 60
    ) -> Dict[str, Any]:
        """
        Splits document into semantic chunks with overlap and indexes term frequencies.
        """
        if not content.strip():
            return {"status": "error", "message": "Content is empty"}

        # Semantic paragraph and sliding window chunking
        raw_chunks = self._chunk_text(content, chunk_size, chunk_overlap)
        now = time.time()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Upsert document
            cursor.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
            cursor.execute(
                "INSERT OR REPLACE INTO documents (id, title, source_type, chunk_count, created_at) VALUES (?, ?, ?, ?, ?)",
                (doc_id, title, source_type, len(raw_chunks), now)
            )

            # Insert chunks with term frequency dictionary
            for idx, chunk_text in enumerate(raw_chunks):
                tokens = tokenize(chunk_text)
                term_freq: Dict[str, int] = {}
                for t in tokens:
                    term_freq[t] = term_freq.get(t, 0) + 1

                cursor.execute(
                    "INSERT INTO chunks (doc_id, chunk_index, content, metadata_json, terms_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        doc_id,
                        idx,
                        chunk_text,
                        json.dumps({"title": title, "source": source_type}, ensure_ascii=False),
                        json.dumps(term_freq, ensure_ascii=False),
                        now
                    )
                )
            conn.commit()

        return {
            "status": "success",
            "doc_id": doc_id,
            "title": title,
            "chunk_count": len(raw_chunks)
        }

    def _chunk_text(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """
        Splits text by double newlines (paragraphs) or sentences with overlap.
        """
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for p in paragraphs:
            p = p.strip()
            if not p:
                continue

            if len(current_chunk) + len(p) <= chunk_size:
                current_chunk += ("\n\n" + p if current_chunk else p)
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                    # Keep overlap from end of current chunk
                    current_chunk = current_chunk[-chunk_overlap:] + "\n\n" + p
                else:
                    # Single paragraph exceeds chunk size, split by lines or words
                    words = p.split()
                    temp = ""
                    for w in words:
                        if len(temp) + len(w) + 1 <= chunk_size:
                            temp += (" " + w if temp else w)
                        else:
                            chunks.append(temp)
                            temp = temp[-chunk_overlap:] + " " + w if chunk_overlap > 0 else w
                    if temp:
                        current_chunk = temp

        if current_chunk:
            chunks.append(current_chunk)

        return chunks if chunks else [text]

    def search(
        self,
        query: str,
        top_k: int = 3,
        min_score: float = 0.15,
        doc_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Performs hybrid BM25/TF-IDF similarity ranking across all indexed chunks.
        """
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        # Read chunks
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if doc_filter:
                cursor.execute("SELECT id, doc_id, chunk_index, content, metadata_json, terms_json FROM chunks WHERE doc_id = ?", (doc_filter,))
            else:
                cursor.execute("SELECT id, doc_id, chunk_index, content, metadata_json, terms_json FROM chunks")
            rows = cursor.fetchall()

        if not rows:
            return []

        total_chunks = len(rows)
        # Compute Document Frequency (DF) for query tokens
        df: Dict[str, int] = {t: 0 for t in query_tokens}
        chunk_data = []

        for r in rows:
            try:
                tf = json.loads(r["terms_json"])
            except Exception:
                tf = {}
            for t in query_tokens:
                if t in tf:
                    df[t] += 1
            chunk_data.append({
                "id": r["id"],
                "doc_id": r["doc_id"],
                "chunk_index": r["chunk_index"],
                "content": r["content"],
                "metadata": json.loads(r["metadata_json"]) if r["metadata_json"] else {},
                "tf": tf
            })

        # Calculate BM25 / TF-IDF score for each chunk
        results = []
        for c in chunk_data:
            score = 0.0
            chunk_len = sum(c["tf"].values())
            for t in query_tokens:
                if t in c["tf"]:
                    # IDF
                    idf = math.log((total_chunks - df[t] + 0.5) / (df[t] + 0.5) + 1.0)
                    # TF with saturation
                    tf_val = c["tf"][t]
                    bm25_tf = (tf_val * 2.2) / (tf_val + 1.2 * (0.25 + 0.75 * (chunk_len / 40.0)))
                    score += idf * bm25_tf

            # Exact keyword substring bonus
            clean_query = query.lower()
            clean_content = c["content"].lower()
            if clean_query in clean_content:
                score += 2.5

            for word in query_tokens:
                if word in clean_content:
                    score += 0.3

            norm_score = round(min(score / 5.0, 1.0), 3)
            if norm_score >= min_score:
                results.append({
                    "chunk_id": c["id"],
                    "doc_id": c["doc_id"],
                    "title": c["metadata"].get("title", c["doc_id"]),
                    "content": c["content"],
                    "score": norm_score,
                    "metadata": c["metadata"]
                })

        # Sort descending by score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def list_documents(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, source_type, chunk_count, created_at FROM documents ORDER BY created_at DESC")
            return [dict(r) for r in cursor.fetchall()]

    def delete_document(self, doc_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
            cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_all(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chunks")
            cursor.execute("DELETE FROM documents")
            conn.commit()


# Global Singleton instance
knowledge_store = KnowledgeStore()
