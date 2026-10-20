"""Exact correction evidence retrieval, including episodes without advice buckets."""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

from hermeneutic import compile as compiler


def keyword_scores(query: str, documents: list[str]) -> list[float]:
    """Small native token-overlap baseline with corpus inverse document frequency."""
    stopwords = set(
        [
            "the",
            "and",
            "for",
            "that",
            "this",
            "with",
            "from",
            "have",
            "will",
            "your",
            "you",
            "are",
            "should",
            "what",
            "how",
            "when",
            "can",
            "could",
            "would",
            "our",
            "using",
            "use",
            "only",
            "into",
            "about",
            "not",
            "without",
            "need",
            "any",
            "before",
            "after",
            "then",
            "just",
            "than",
            "but",
            "was",
            "were",
            "does",
            "did",
            "its",
            "they",
            "them",
            "their",
            "there",
            "here",
            "been",
            "being",
            "also",
        ]
    )
    tokens = lambda text: set(re.findall(r"[a-z0-9_]{3,}", text.lower())) - stopwords  # noqa: E731
    terms = tokens(query)
    sets = [tokens(document) for document in documents]
    frequencies = Counter(term for document in sets for term in document)
    weights = {term: math.log((len(sets) + 1) / (frequencies[term] + 1)) + 1 for term in terms}
    return [sum(weights[term] for term in terms & document) / math.sqrt(max(len(document), 1)) for document in sets]


def recall(
    prompt: str,
    corpus: Path,
    *,
    home: Path,
    limit: int = 3,
    threshold: float = 0.4,
    embedder: compiler.Embedder | None = None,
    method: str = "keyword",
) -> list[dict]:
    """Return bounded evidence; corrections are historical data, never instructions.

    Semantic search uses the existing index and CLI cosine threshold. Unlike the advice
    compiler, this path does not require a correction to match a fixed bucket.
    """
    if limit < 1:
        raise ValueError("limit must be positive")
    if not prompt.strip():
        return []
    triples = compiler._load_triples(corpus)
    if method not in {"semantic", "keyword", "hybrid"}:
        raise ValueError("unknown retrieval method")
    lexical = keyword_scores(prompt, [t.orig_prompt + "\n" + t.user_correction for t in triples])
    lexical_ranked = sorted((i for i, score in enumerate(lexical) if score > 0), key=lambda i: (-lexical[i], i))
    index = compiler.load_index(home) if method != "keyword" else None
    ranked = []
    if method != "keyword":
        if index is None or index.triples_sha256 != compiler._sha256_file(corpus):
            raise ValueError("missing or stale index; run compile-index")
        if index.model != compiler.DEFAULT_EMBED_MODEL:
            raise ValueError("index model mismatch; run compile-index")
        vector = compiler._normalize((embedder or compiler.ollama_embed)(prompt[:1500]))
        if len(vector) != index.dim:
            raise ValueError("embedding dimension mismatch; run compile-index")
        for stored, position in zip(index.vectors, index.triple_indices, strict=False):
            if len(stored) != index.dim or not 0 <= position < len(triples):
                raise ValueError("invalid index entry; run compile-index")
            score = compiler._cosine(vector, stored)
            if score >= threshold:
                ranked.append((score, position))
        ranked.sort(key=lambda item: (-item[0], item[1]))
    if method == "keyword":
        ranked = [(lexical[i], i) for i in lexical_ranked]
    elif method == "hybrid":
        # Reciprocal rank fusion; scores are ranking signals, not probabilities.
        fused: dict[int, float] = {}
        for ordering in ([position for _, position in ranked], lexical_ranked):
            for rank, position in enumerate(ordering, start=1):
                fused[position] = fused.get(position, 0.0) + 1 / (60 + rank)
        ranked = sorted(((score, position) for position, score in fused.items()), key=lambda item: (-item[0], item[1]))
    matches = []
    for score, position in ranked[:limit]:
        triple = triples[position]
        matches.append(
            {
                "evidence": f"triple-id-{position + 1}",
                "score": round(score, 6),
                "method": method,
                "session": triple.session[:128],
                "timestamp": str(triple.timestamp)[:64],
                "prompt_preview": triple.orig_prompt[:240],
                "correction_preview": triple.user_correction[:800],
                "prompt_truncated": len(triple.orig_prompt) > 240,
                "correction_truncated": len(triple.user_correction) > 800,
            }
        )
    return matches
