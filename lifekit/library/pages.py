"""Cut a fetched volume into pages.

A PDF yields one page per printed page. An HTML page yields one page per
heading section, in document order. Each page carries an anchor that opens
the source at that spot.
"""

import re
from pathlib import Path


def pdf_pages(source: Path, first: int = 1, last: int | None = None) -> list[dict]:
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(source)
    count = len(document)
    last = min(last or count, count)
    pages = []
    for index in range(first - 1, last):
        text = document[index].get_textpage().get_text_range()
        text = _normalise(text)
        pages.append({"number": index + 1, "anchor": f"page={index + 1}", "text": text})
    return pages


_HEADINGS = ("h1", "h2", "h3")


def html_pages(source: Path, url: str) -> list[dict]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(source.read_text(errors="replace"), "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript", "form", "aside"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    pages: list[dict] = []
    current = {"number": 1, "anchor": url, "text": ""}
    for element in main.descendants:
        if getattr(element, "name", None) in _HEADINGS:
            if current["text"].strip():
                pages.append(current)
            heading = element.get_text(" ", strip=True)
            fragment = element.get("id") or _slug(heading)
            current = {
                "number": len(pages) + 1,
                "anchor": f"{url}#{fragment}",
                "text": heading + "\n",
            }
        elif getattr(element, "name", None) in ("p", "li", "td", "th", "dt", "dd"):
            line = element.get_text(" ", strip=True)
            if line:
                current["text"] += line + "\n"
    if current["text"].strip():
        pages.append(current)
    for page in pages:
        page["text"] = _normalise(page["text"])
    return pages


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def _normalise(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    lines: list[str] = []
    for line in text.split("\n"):
        if not lines or line.strip() != lines[-1].strip():
            lines.append(line)
    return "\n".join(lines).strip()
