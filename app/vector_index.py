"""Tiny dependency-free TF-IDF cosine index over the scheme knowledge base.

Swap `TfidfIndex` for Chroma / FAISS + multilingual embeddings in production; the
`search(query, k)` contract stays the same.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

DATA = Path(__file__).parent / "data" / "schemes.json"
_TOKEN = re.compile(r"[^\s,.;:!?()\[\]\"'/|\-_]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class TfidfIndex:
    def __init__(self, docs: dict[str, str]):
        toks = {k: tokenize(v) for k, v in docs.items()}
        df = Counter(t for ts in toks.values() for t in set(ts))
        n = len(docs)
        self.idf = {t: math.log((1 + n) / (1 + c)) + 1 for t, c in df.items()}
        self.vecs = {k: self._vec(ts) for k, ts in toks.items()}

    def _vec(self, tokens: list[str]) -> dict[str, float]:
        tf = Counter(t for t in tokens if t in self.idf)
        v = {t: c * self.idf[t] for t, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norm for t, x in v.items()}

    def search(self, query: str, k: int = 5) -> list[tuple[str, float]]:
        q = self._vec(tokenize(query))
        scored = [(key, sum(w * v.get(t, 0.0) for t, w in q.items())) for key, v in self.vecs.items()]
        return sorted(scored, key=lambda x: -x[1])[:k]


_cache: dict = {}


def load_kb() -> list[dict]:
    if "kb" not in _cache:
        _cache["kb"] = json.loads(DATA.read_text(encoding="utf-8"))["schemes"]
    return _cache["kb"]


def get_index() -> TfidfIndex:
    if "idx" not in _cache:
        docs = {s["id"]: " ".join([s["name"], s["desc"], s["eligibility"], s["kind"], " ".join(s["kw"])])
                for s in load_kb()}
        _cache["idx"] = TfidfIndex(docs)
    return _cache["idx"]
