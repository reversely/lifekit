"""FM 21-76 chapter table: the first page of each chapter in the 233-page scan
at packs/reference/FM21-76_SurvivalManual.pdf. Carried over from flux
app/src/data/reference.ts; regenerate if the PDF changes. The library build
uses it to cut the per-chapter FM volumes."""

CHAPTER_PAGES: dict[int, int] = {
    1: 5, 2: 8, 3: 14, 4: 16, 5: 38, 6: 53, 7: 63, 8: 72, 9: 99, 10: 109,
    11: 112, 12: 120, 13: 131, 14: 139, 15: 146, 16: 162, 17: 185, 18: 194,
    19: 200, 20: 209, 21: 215, 22: 219, 23: 221,
}
