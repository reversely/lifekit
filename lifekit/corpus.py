"""Encyclopedia corpus and quote search over the reference text."""

import json
import math
import re
from functools import lru_cache

from .packs import packs_dir
from .reference import page_texts

_WORD = re.compile(r"[a-z]{2,}")


@lru_cache(maxsize=1)
def guide_corpus() -> dict:
    path = packs_dir() / "encyclopedia" / "guide-corpus.json"
    return json.loads(path.read_text())


def _tokens(text: str) -> list[str]:
    return _WORD.findall(text.lower())


@lru_cache(maxsize=1)
def _page_index() -> tuple[list[dict[str, int]], dict[str, int]]:
    """Per-page term counts and document frequencies over the FM text."""
    counts: list[dict[str, int]] = []
    doc_freq: dict[str, int] = {}
    for text in page_texts():
        page_counts: dict[str, int] = {}
        for token in _tokens(text):
            page_counts[token] = page_counts.get(token, 0) + 1
        for token in page_counts:
            doc_freq[token] = doc_freq.get(token, 0) + 1
        counts.append(page_counts)
    return counts, doc_freq


def search_pages(query: str, limit: int = 5) -> list[tuple[int, str]]:
    """Top pages for a query as (one-based page, matching passage).

    TF-IDF over page text. The passage comes back verbatim so the answer
    quotes the document rather than paraphrasing it.
    """
    counts, doc_freq = _page_index()
    total = len(counts)
    terms = [t for t in _tokens(query) if t in doc_freq]
    if not terms:
        return []
    scored = []
    for page_zero, page_counts in enumerate(counts):
        score = sum(
            page_counts.get(t, 0) * math.log(total / doc_freq[t]) for t in terms
        )
        if score > 0:
            scored.append((score, page_zero + 1))
    scored.sort(reverse=True)
    results = []
    for _, page in scored[:limit]:
        results.append((page, _passage(page_texts()[page - 1], terms)))
    return results


def _passage(text: str, terms: list[str], width: int = 320) -> str:
    """The stretch of page text around the rarest matching term.

    Word-boundary matches only: a substring match would anchor on the scan's
    repeated page header (the "in" inside "Reprinted") instead of the content.
    """
    _, doc_freq = _page_index()
    position = 0
    for term in sorted(terms, key=lambda t: doc_freq.get(t, 0)):
        match = re.search(rf"\b{re.escape(term)}\b", text, re.IGNORECASE)
        if match is not None:
            position = match.start()
            break
    start = max(0, position - width // 4)
    return " ".join(text[start : start + width].split())
