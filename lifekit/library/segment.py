"""Cut a page's text into passages with checked offsets.

A passage is a verbatim span of the page text. The segmenter splits on blank
lines and on numbered or bulleted items, merges very short fragments into
their neighbour, and assigns a kind from surface cues. Offsets are computed
by searching the page text, so ``page.text[start:end] == passage.text``
holds by construction.
"""

import re

_ITEM = re.compile(r"^\s*(?:\(?\d{1,2}[.)]|[a-z][.)]|[•\-–*]|Step \d+)\s+", re.IGNORECASE)
_WARNING = re.compile(r"^\s*(WARNING|CAUTION|DANGER|Do not|Never|Note:|NOTE)", re.IGNORECASE)
_MIN_CHARS = 40
_MAX_CHARS = 900


def segment(text: str) -> list[dict]:
    raw = _split(text)
    merged = _merge(raw)
    passages = []
    cursor = 0
    for chunk in merged:
        start = text.find(chunk, cursor)
        if start < 0:
            continue
        end = start + len(chunk)
        cursor = end
        passages.append({"start": start, "end": end, "text": chunk, "kind": _kind(chunk)})
    return passages


def _split(text: str) -> list[str]:
    chunks: list[str] = []
    for block in re.split(r"\n\s*\n", text):
        lines = block.split("\n")
        current: list[str] = []
        for line in lines:
            if _ITEM.match(line) and current:
                chunks.append("\n".join(current))
                current = [line]
            else:
                current.append(line)
        if current:
            chunks.append("\n".join(current))
    return [c.strip("\n") for c in chunks if c.strip()]


def _merge(chunks: list[str]) -> list[str]:
    out: list[str] = []
    for chunk in chunks:
        if out and len(chunk) < _MIN_CHARS:
            out[-1] = out[-1] + "\n" + chunk
        elif out and len(out[-1]) < _MIN_CHARS:
            out[-1] = out[-1] + "\n" + chunk
        else:
            out.append(chunk)
    final: list[str] = []
    for chunk in out:
        while len(chunk) > _MAX_CHARS:
            cut = chunk.rfind("\n", 0, _MAX_CHARS)
            if cut < _MIN_CHARS:
                cut = chunk.rfind(". ", 0, _MAX_CHARS) + 1
            if cut < _MIN_CHARS:
                cut = _MAX_CHARS
            final.append(chunk[:cut].strip("\n"))
            chunk = chunk[cut:].strip("\n")
        if chunk:
            final.append(chunk)
    return final


def _kind(chunk: str) -> str:
    if _WARNING.match(chunk):
        return "warning"
    lines = [line for line in chunk.split("\n") if line.strip()]
    items = sum(1 for line in lines if _ITEM.match(line))
    if items >= 2 and items >= len(lines) / 2:
        return "checklist"
    if _ITEM.match(chunk):
        return "procedure_step"
    if len(lines) >= 3 and all(len(line) < 60 for line in lines):
        return "table_row"
    return "principle"
