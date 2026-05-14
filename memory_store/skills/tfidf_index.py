#!/usr/bin/env python3
"""
纯 Python TF-IDF 检索引擎 — 零外部依赖。
支持中英文混合分词：中文按字符 bigram + 单字，英文按词。
"""

import re
import math
from collections import Counter
from typing import List, Tuple, Dict


def tokenize(text: str) -> List[str]:
    """中英文混合分词。中文 → bigram + 单字；英文/数字 → 小写词。"""
    text = text.lower()
    tokens = []

    # 提取连续字母/数字段
    alpha_num = re.findall(r"[a-z0-9]+", text)
    tokens.extend(alpha_num)

    # 中文：逐字符 + bigram
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", text)
    tokens.extend(chinese_chars)
    for i in range(len(chinese_chars) - 1):
        tokens.append(chinese_chars[i] + chinese_chars[i + 1])

    # 过滤纯空白/标点 token
    tokens = [t for t in tokens if t.strip() and len(t) >= 1]
    return tokens


class TfidfIndex:
    """增量式 TF-IDF 索引，支持文档添加后统一 build，然后查询。"""

    def __init__(self):
        self.documents: List[Tuple[str, List[str]]] = []  # (doc_id, tokens)
        self.idf: Dict[str, float] = {}
        self.doc_freq: Counter = Counter()
        self._built = False

    def add_document(self, doc_id: str, text: str):
        """添加一篇文档并立即分词。"""
        tokens = tokenize(text)
        self.documents.append((doc_id, tokens))
        for t in set(tokens):
            self.doc_freq[t] += 1
        self._built = False

    def build(self):
        """计算 IDF 权重。添加新文档后需要重新 build。"""
        n = len(self.documents)
        if n == 0:
            self.idf = {}
        else:
            self.idf = {
                t: math.log((n + 1) / (df + 1)) + 1.0
                for t, df in self.doc_freq.items()
            }
        self._built = True

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """余弦相似度检索，返回 [(doc_id, score), ...]。"""
        if not self._built:
            self.build()

        query_tokens = tokenize(query)
        query_tf = Counter(query_tokens)
        query_norm = math.sqrt(
            sum((tf * self.idf.get(t, 0.5)) ** 2 for t, tf in query_tf.items())
        )
        if query_norm == 0:
            return []

        scores = []
        for doc_id, doc_tokens in self.documents:
            doc_tf = Counter(doc_tokens)
            dot = 0.0
            for t, qtf in query_tf.items():
                dot += qtf * doc_tf.get(t, 0) * self.idf.get(t, 0.5)
            doc_norm = math.sqrt(
                sum((tf * self.idf.get(t, 0.5)) ** 2 for t, tf in doc_tf.items())
            )
            score = dot / (doc_norm + 1e-9) if doc_norm > 0 else 0.0
            scores.append((doc_id, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def clear(self):
        """清空索引。"""
        self.documents.clear()
        self.doc_freq.clear()
        self.idf.clear()
        self._built = False

    def __len__(self):
        return len(self.documents)
