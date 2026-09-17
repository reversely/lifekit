"""An offline Wikipedia as a source class: a Kiwix ZIM file in packs/zim/.

A ZIM carries rendered article HTML and its own full-text index, so the online retrieval
can search and pull with no network. The first *.zim under packs/zim/ (largest
first) is the one in use; none means the class is absent and the online retrieval goes to
the live search.
"""

import re
from functools import lru_cache
from pathlib import Path

from lifekit.packs import LOCAL_PACKS

ZIM_DIR = LOCAL_PACKS / "zim"
WIKI_PAGE = "https://en.wikipedia.org/wiki/"


def available() -> Path | None:
    if not ZIM_DIR.is_dir():
        return None
    files = sorted(ZIM_DIR.glob("*.zim"), key=lambda p: p.stat().st_size, reverse=True)
    return files[0] if files else None


@lru_cache(maxsize=1)
def _archive(path: str):
    from libzim.reader import Archive

    return Archive(path)


def describe() -> dict | None:
    path = available()
    if path is None:
        return None
    archive = _archive(str(path))
    meta = {}
    for key in ("Title", "Date", "Language", "Description"):
        if key in archive.metadata_keys:
            meta[key.lower()] = archive.get_metadata(key).decode("utf-8", "replace")
    return {"file": path.name, "articles": archive.article_count, "fulltext": archive.has_fulltext_index, **meta}


def search(topic: str, limit: int = 8) -> list[dict]:
    """Candidates in the same shape as the live search: title and url. Title matches for
    the topic and for each of its longer words come first, because the full-text index
    ranks by word frequency and puts "Alternative Cars" above "Alternator" for a topic
    like "car alternator replacement"; full-text matches for the whole topic follow."""
    path = available()
    if path is None:
        return []
    from libzim.search import Query, Searcher
    from libzim.suggestion import SuggestionSearcher

    archive = _archive(str(path))
    paths: list[str] = []
    suggester = SuggestionSearcher(archive)
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z-]{3,}", topic) if w.lower() not in _STOP]
    for query in [topic, *words]:
        try:
            paths += list(suggester.suggest(query).getResults(0, 3))
        except Exception:  # noqa: BLE001
            continue
    paths += list(Searcher(archive).search(Query().set_query(topic)).getResults(0, limit))
    out = []
    seen: set[str] = set()
    for entry_path in paths:
        entry = archive.get_entry_by_path(entry_path)
        if entry.is_redirect:
            entry = entry.get_redirect_entry()
        if entry.path in seen:
            continue
        seen.add(entry.path)
        out.append({"title": entry.title, "url": WIKI_PAGE + entry.path.split("/")[-1], "zim_path": entry.path})
        if len(out) >= limit + 4:
            break
    return out


_STOP = {"what", "when", "where", "which", "does", "with", "from", "that", "this", "have", "your", "about", "into", "over", "make", "made", "using"}


def article_html(zim_path: str) -> bytes:
    path = available()
    if path is None:
        raise RuntimeError("no ZIM under packs/zim")
    archive = _archive(str(path))
    entry = archive.get_entry_by_path(zim_path)
    if entry.is_redirect:
        entry = entry.get_redirect_entry()
    return bytes(entry.get_item().content)


_NAV = re.compile(r"<(nav|footer|header)[^>]*>.*?</\1>", re.S)


def clean_html(body: bytes) -> bytes:
    """Drop the Kiwix chrome so the page cutter sees the article body only."""
    text = _NAV.sub("", body.decode("utf-8", "replace"))
    return text.encode("utf-8")
