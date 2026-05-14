#!/usr/bin/env python3
"""
RAG 文档知识库 — 基于 TF-IDF 的分块检索。
将 knowledge_base/*.txt 分成等长 chunk 后建索引，查询时返回最相关片段。
"""

import os
import glob as globmod
from typing import List, Dict, Optional

from .tfidf_index import TfidfIndex


class DocumentChunk:
    """一个文档块，携带来源元信息。"""

    def __init__(self, chunk_id: str, text: str, source: str, chunk_idx: int = 0):
        self.id = chunk_id
        self.text = text
        self.source = source
        self.chunk_idx = chunk_idx

    def __repr__(self):
        return f"Chunk({self.id}, src={self.source}, len={len(self.text)})"


class RagKnowledgeBase:
    """RAG 知识库：分块 → TF-IDF 索引 → 相似度检索。"""

    def __init__(
        self, kb_dir: str, chunk_size: int = 500, chunk_overlap: int = 50
    ):
        self.kb_dir = kb_dir
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.index = TfidfIndex()
        self.chunks: Dict[str, DocumentChunk] = {}
        self._loaded = False

    @property
    def ready(self) -> bool:
        return self._loaded and len(self.index) > 0

    def load(self) -> int:
        """扫描 knowledge_base/ 目录，分块建索引。返回加载的文档数。"""
        self.index.clear()
        self.chunks.clear()

        txt_files = globmod.glob(os.path.join(self.kb_dir, "*.txt"))
        for fpath in txt_files:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                source = os.path.basename(fpath)
                self._chunk_and_index(content, source)
            except Exception:
                continue

        self.index.build()
        self._loaded = True
        return len(txt_files)

    def search(self, query: str, top_k: int = 3) -> List[DocumentChunk]:
        """检索最相关的 top_k 个文档块。"""
        if not self._loaded:
            self.load()

        results = self.index.search(query, top_k=top_k)
        return [
            self.chunks[doc_id]
            for doc_id, score in results
            if doc_id in self.chunks and score > 0.01
        ]

    def search_as_context(self, query: str, top_k: int = 3) -> str:
        """检索并组装为可注入 prompt 的上下文字符串。"""
        chunks = self.search(query, top_k=top_k)
        if not chunks:
            return ""

        parts = []
        for c in chunks:
            header = f"【文档来源: {c.source} (片段 {c.chunk_idx + 1})】"
            snippet = c.text[:800] if len(c.text) > 800 else c.text
            parts.append(f"{header}\n{snippet}")

        return "【知识库检索结果】\n\n" + "\n\n---\n\n".join(parts)

    # ── 内部 ──

    def _chunk_and_index(self, text: str, source: str):
        """将文本按字符分块，逐块加入索引。"""
        step = self.chunk_size - self.chunk_overlap
        if step <= 0:
            step = self.chunk_size

        total = len(text)
        chunk_idx = 0
        pos = 0
        while pos < total:
            end = min(pos + self.chunk_size, total)
            chunk_text = text[pos:end]
            chunk_id = f"{source}#{chunk_idx}"
            self.chunks[chunk_id] = DocumentChunk(
                chunk_id=chunk_id, text=chunk_text, source=source, chunk_idx=chunk_idx
            )
            self.index.add_document(chunk_id, chunk_text)
            chunk_idx += 1
            if end >= total:
                break
            pos += step

    def reload(self):
        """强制重新加载所有文档。"""
        return self.load()
