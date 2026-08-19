"""FM 21-76 reference: chapter jump table and page rendering."""

from functools import lru_cache

from .packs import packs_dir

PDF_NAME = "reference/FM21-76_SurvivalManual.pdf"

# First page of each chapter in the bundled scan, carried over from
# flux app/src/data/reference.ts. Regenerate if the PDF changes.
CHAPTER_PAGES: dict[int, int] = {
    1: 5, 2: 8, 3: 14, 4: 16, 5: 38, 6: 53, 7: 63, 8: 72, 9: 99, 10: 109,
    11: 112, 12: 120, 13: 131, 14: 139, 15: 146, 16: 162, 17: 185, 18: 194,
    19: 200, 20: 209, 21: 215, 22: 219, 23: 221,
}


@lru_cache(maxsize=1)
def _document():
    import pypdfium2 as pdfium

    return pdfium.PdfDocument(packs_dir() / PDF_NAME)


def page_count() -> int:
    return len(_document())


@lru_cache(maxsize=32)
def render_page(page_number: int):
    """One-based page number to a PIL image."""
    page = _document()[page_number - 1]
    return page.render(scale=2.0).to_pil()


@lru_cache(maxsize=1)
def page_texts() -> list[str]:
    """Extracted text per page, index 0 holding page 1."""
    texts = []
    for page in _document():
        texts.append(page.get_textpage().get_text_bounded())
    return texts


def chapter_of_page(page_number: int) -> int:
    chapter = 1
    for number, first_page in CHAPTER_PAGES.items():
        if page_number >= first_page:
            chapter = number
    return chapter
