"""Render the library grid and the digest as static HTML for a progress shot.

Each cover is the volume's content: title, edition, publisher, the cover
text, licence, page count, and when it arrived. Sorted latest first.
"""

import html
import re
import sys
from pathlib import Path

from .build import DB_PATH, connect

CSS = """
body{margin:0;background:#09090b;color:#fafafa;font:17px/1.5 -apple-system,Inter,Helvetica,Arial,sans-serif}
.top{padding:44px 24px 6px}.top h1{font-size:40px;margin:0;font-weight:700;letter-spacing:-.02em}
.top span{display:block;color:#a1a1aa;font-size:17px;margin-top:6px}
.digest{margin:18px 24px 6px;padding:18px 0 4px;border-top:1px solid #27272a;border-bottom:1px solid #27272a}
.digest h2{font-size:12px;margin:0 0 10px;color:#a1a1aa;font-weight:500;letter-spacing:.1em;text-transform:uppercase}
.digest p{margin:0 0 12px;font-size:17px;color:#fafafa}
.digest .q b{display:block;font-size:17px;margin-bottom:6px;font-weight:600}
.digest .q i{display:block;color:#a1a1aa;font-style:normal;font-size:15px;line-height:1.55;margin-bottom:14px}
.grid{display:grid;grid-template-columns:1fr;gap:12px;padding:0 24px 8px}
.cover{background:#0f0f12;border:1px solid #27272a;border-radius:12px;padding:18px 20px}
.cover .head{display:grid;grid-template-columns:56px 1fr;gap:14px;align-items:center;margin-bottom:12px}
.cover h2{font-size:22px;margin:0 0 4px;line-height:1.25;font-weight:700;letter-spacing:-.01em}
.cover .ed{color:#a1a1aa;font-size:15px}
.cover p{margin:0;font-size:16px;line-height:1.55;color:#d4d4d8}
.cover .foot{margin-top:12px;font-size:13px;color:#71717a}
.role{text-transform:capitalize}
.thumb{width:56px;height:76px;object-fit:cover;object-position:top;border-radius:4px;border:1px solid #27272a;background:#fff}
.chip.empty{color:#52525b;border-color:#1f1f23}.chip.empty .n{opacity:.7}
.chips{display:flex;flex-wrap:wrap;gap:8px;padding:6px 24px 4px;align-items:center}
.chips .lab{width:100%;font-size:13px;letter-spacing:.1em;color:#71717a;margin:14px 0 0;text-transform:uppercase}
.chip{font-size:14px;padding:6px 12px;border-radius:999px;border:1px solid #27272a;color:#d4d4d8;background:#09090b}
.chip.on{background:#fafafa;color:#09090b;border-color:#fafafa;font-weight:600}
.chip .n{opacity:.55;margin-left:4px}
.day{padding:26px 24px 10px;font-size:14px;color:#71717a;letter-spacing:.08em;text-transform:uppercase}
.tags{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px;align-items:center}
.tag{font-size:12.5px;padding:3px 9px;border-radius:999px;background:#18181b;color:#a1a1aa;border:1px solid #27272a}
.tag.section{background:#27272a;color:#fafafa}.tag.hand{border-style:dashed}
.bar{margin:10px 24px 8px;display:flex;align-items:center;gap:10px;background:#0f0f12;border:1px solid #3f3f46;border-radius:10px;padding:13px 16px;font-size:17px;color:#fafafa}
.bar .x{margin-left:auto;color:#71717a;font-size:16px}
.hint{padding:4px 24px 0;font-size:14px;color:#a1a1aa}
.res{margin:0 24px 12px;background:#0f0f12;border:1px solid #27272a;border-radius:12px;padding:16px 18px}
.res .src{font-size:13px;color:#a1a1aa;margin-bottom:6px}.res .src b{color:#fafafa;font-weight:600}
.res p{margin:0;font-size:15.5px;line-height:1.55;color:#d4d4d8}
.res .open{margin-top:12px;font-size:13px;color:#09090b;background:#fafafa;display:inline-block;padding:6px 12px;border-radius:8px;font-weight:600}
.group{padding:24px 24px 10px;font-size:14px;letter-spacing:.1em;color:#71717a;text-transform:uppercase}
.divider{display:flex;justify-content:space-between;align-items:baseline;padding:30px 24px 10px}
.divider h3{margin:0;font-size:20px;font-weight:600}.divider span{color:#71717a;font-size:14px}
body.dir{background:#F6F2E8;color:#1C2B36}
.dir .top h1{color:#1C2B36}.dir .top span{color:#74858F}
.dir .digest{border-color:#E4DCC9}.dir .digest h2{color:#74858F}.dir .digest p{color:#1C2B36}
.dir .digest .q b{color:#1C2B36}.dir .digest .q i{color:#51626E}
.dir .label{padding:26px 24px 6px;font-size:12px;letter-spacing:.12em;color:#74858F}
.row{display:grid;grid-template-columns:44px 1fr 28px;align-items:start;padding:18px 24px;border-top:1px solid #E4DCC9}
.row .n{font:italic 28px/1 Georgia,"Times New Roman",serif;color:#1C2B36;padding-top:2px}
.row .t{font-size:21px;font-weight:600;color:#1C2B36;border-bottom:1px solid #C98D12;padding-bottom:3px;display:inline-block}
.row .s{font-size:15px;color:#51626E;margin-top:6px}
.row .c{font-size:14px;color:#74858F;margin-top:6px}.row .c.some{color:#1C2B36;font-weight:600}
"""


def _short(text: str | None, sentences: int = 2) -> str:
    if not text:
        return "Cover pending."
    parts = re.split(r"(?<=[.!?])\s+", text.replace("\n", " ").strip())
    return " ".join(parts[:sentences])


from . import sections as _sections

SECTIONS = [(r['id'], r['title'], r['scope']) for r in _sections.rows()]
HEAD = '<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'


def render_timeline(out: Path, active: str | None = None, sort: str = "latest") -> None:
    """The Library as one chronological list, latest first, grouped by day, with tag bubbles."""
    db = connect(DB_PATH)
    section_names = {f"section:{sid}": name for sid, name, _ in SECTIONS}
    chips = _chip_groups(db, active)
    where = " AND v.id IN (SELECT volume_id FROM volume_tag WHERE tag = ?)" if active else ""
    rows = db.execute(
        "SELECT v.id, v.title, v.publisher, v.edition, v.page_count, v.retrieved, c.text, v.format FROM volume v"
        " LEFT JOIN cover c ON c.volume_id = v.id WHERE v.carry = 'carry'" + where +
        " ORDER BY " + SORT_SQL[sort], (active,) if active else ()
    ).fetchall()
    body = ""
    last_day = None
    for vid, title, publisher, edition, pages, retrieved, cover, fmt in rows:
        day = (retrieved or "")[:10]
        if sort in ("latest", "oldest") and day != last_day:
            body += f'<div class="day">{_day_label(day)}</div>'
            last_day = day
        tags = "".join(
            f'<span class="tag{" section" if tag.startswith("section:") else ""}{" hand" if source == "hand" else ""}">'
            f'{html.escape(section_names.get(tag, tag.split(":", 1)[-1]))}</span>'
            for tag, source in db.execute(
                "SELECT tag, source FROM volume_tag WHERE volume_id = ? AND tag NOT LIKE 'section:%' ORDER BY tag", (vid,)
            )
        )
        body += f'<div class="grid">{_card(vid, title, publisher, edition, pages, cover, fmt, f"<div class=\"tags\">{tags}</div>")}</div>'
    page = f"""{HEAD}<style>{CSS}</style></head><body>
<div class="top"><h1>Recent</h1></div>
<div class="chips">{_sort_chips(sort)}{chips}</div>{body}<div style="height:30px"></div></body></html>"""
    out.write_text(page)


NAMESPACES = [("section", "SECTION"), ("type", "TYPE"), ("publisher", "PUBLISHER")]
from lifekit.packs import LOCAL_PACKS

THUMBS = LOCAL_PACKS / "thumbs"
_FONT = Path(__file__).resolve().parents[2] / "web" / "public" / "fonts" / "Aeonik-Medium.ttf"


def thumbnail(volume_id: str, fmt: str, title: str = "", publisher: str = "", out_dir: Path = THUMBS) -> Path:
    """A small thumbnail, made once: the first page for a PDF, a typographic tile
    (publisher and title) for an HTML page. Returns the file path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{volume_id}.png"
    if not out.exists():
        if fmt == "pdf":
            import pypdfium2 as pdfium
            from .fetch import VOLUMES_DIR

            doc = pdfium.PdfDocument(VOLUMES_DIR / volume_id / "source.pdf")
            doc[0].render(scale=0.6).to_pil().save(out)
        else:
            from PIL import Image, ImageDraw, ImageFont

            img = Image.new("RGB", (240, 330), "#18181b")
            draw = ImageDraw.Draw(img)
            try:
                face = str(_FONT) if _FONT.exists() else "/System/Library/Fonts/Helvetica.ttc"
                small = ImageFont.truetype(face, 18)
                big = ImageFont.truetype(face, 26)
            except OSError:
                small = big = ImageFont.load_default()
            draw.rectangle([0, 0, 239, 329], outline="#3f3f46")
            draw.text((18, 20), (publisher or "").split(",")[0][:22], fill="#a1a1aa", font=small)
            y = 70
            line = ""
            for word in (title or "").split():
                if draw.textlength(line + " " + word, font=big) > 200 and line:
                    draw.text((18, y), line, fill="#fafafa", font=big)
                    y += 32
                    line = word
                else:
                    line = (line + " " + word).strip()
                if y > 260:
                    break
            if line and y <= 260:
                draw.text((18, y), line, fill="#fafafa", font=big)
            img.save(out)
    return out


SORTS = [("latest", "Latest"), ("oldest", "Oldest"), ("title", "A to Z"), ("pages", "Pages")]
SORT_SQL = {"latest": "v.retrieved DESC", "oldest": "v.retrieved ASC", "title": "v.title ASC", "pages": "v.page_count DESC"}


def _sort_chips(active: str = "latest") -> str:
    return '<span class="lab">Sort</span>' + "".join(
        f'<span class="chip{" on" if key == active else ""}">{label}</span>' for key, label in SORTS
    )


def _chip_groups(db, active: str | None, namespaces=None, shelf: str | None = None) -> str:
    section_names = {f"section:{sid}": name for sid, name, _ in SECTIONS}
    scope = " AND v.id IN (SELECT volume_id FROM volume_tag WHERE tag = ?)" if shelf else ""
    counts = db.execute(
        "SELECT tag, count(*) FROM volume_tag t JOIN volume v ON v.id = t.volume_id WHERE v.carry = 'carry'"
        + scope + " GROUP BY tag ORDER BY count(*) DESC, tag", (f"section:{shelf}",) if shelf else ()
    ).fetchall()
    NS = namespaces or NAMESPACES
    by_tag = dict(counts)
    out = ""
    for ns, label in NS:
        if ns == "section":
            tags = [f"section:{sid}" for sid, _, _ in SECTIONS]
        else:
            tags = [t for t, _ in counts if t.startswith(ns + ":")]
        chips = []
        for tag in tags:
            n = by_tag.get(tag, 0)
            cls = "chip" + (" on" if tag == active else "") + (" empty" if n == 0 else "")
            chips.append(f'<span class="{cls}">{html.escape(section_names.get(tag, tag.split(":", 1)[1]))}<span class="n">{n}</span></span>')
        if chips:
            all_chip = f'<span class="chip{" on" if not active else ""}">All</span>' if ns == NS[0][0] else ""
            out += f'<span class="lab">{label}</span>' + all_chip + "".join(chips)
    return out


def render_search(out: Path, question: str, tag: str | None = None) -> None:
    """Search bar, filter chips, matching volumes, then passages with their page."""
    from .query import search, volumes_matching

    db = connect(DB_PATH)
    chips = _chip_groups(db, tag)
    vols = "".join(
        f'<div class="res"><div class="src"><b>{html.escape(v["title"])}</b>, {html.escape(v["edition"] or "")}</div>'
        f'<p>{html.escape(_short(v["cover"]))}</p><div class="open">Open volume</div></div>'
        for v in volumes_matching(db, question)
    )
    hits = search(db, question, limit=6, tag=tag)
    passages = "".join(
        f'<div class="res"><div class="src"><b>{html.escape(h["title"])}</b>, {html.escape(h["edition"] or "")}, page {h["number"]}</div>'
        f'<p>{html.escape(h["text"][:360])}{"…" if len(h["text"]) > 360 else ""}</p><div class="open">Open page {h["number"]}</div></div>'
        for h in hits
    )
    page = f"""{HEAD}<style>{CSS}</style></head><body>
<div class="top"><h1>Search</h1></div>
<div class="bar">{html.escape(question)}<span class="x">×</span></div>
<div class="chips">{chips}</div>
{'<div class="group">VOLUMES</div>' + vols if vols else ''}
<div class="group">IN THE PAGES</div>{passages or '<div class="hint">Nothing in the library answers this. Stored for when you are online.</div>'}
<div style="height:30px"></div></body></html>"""
    out.write_text(page)


def _card(vid, title, publisher, edition, pages, cover, fmt, tags_html="") -> str:
    thumbnail(vid, fmt, title, publisher, out_dir=Path("docs/progress/thumbs"))
    thumb = f"thumbs/{vid}.png"
    return (
        f'<div class="cover"><div class="head"><img class="thumb" src="{thumb}"><div>'
        f'<h2>{html.escape(title)}</h2>'
        f'<div class="ed">{html.escape(publisher or "")}, {html.escape(edition or "")}</div></div></div>'
        f'<p>{html.escape(_short(cover))}</p>{tags_html}'
        f'<div class="foot">{pages or 0} pages</div></div>'
    )


def _day_label(day: str) -> str:
    from datetime import date

    if not day:
        return "Undated"
    d = date.fromisoformat(day)
    return d.strftime("%-d %B %Y")


def render_directory(out: Path, answer: tuple[str, str] | None = None) -> None:
    """The Library as the contents directory: twelve numbered sections with counts."""
    db = connect(DB_PATH)
    rows = ""
    total = 0
    for n, (shelf_id, name, scope) in enumerate(SECTIONS, start=1):
        count = db.execute(
            "SELECT count(*) FROM shelf_volume sv JOIN volume v ON v.id = sv.volume_id"
            " WHERE sv.shelf_id = ? AND v.carry = 'carry'", (shelf_id,)
        ).fetchone()[0]
        total += count
        counted = f'<div class="c some">{count} volumes</div>' if count else '<div class="c">none yet</div>'
        rows += f'<div class="row"><div class="n">{n}</div><div><div class="t">{html.escape(name)}</div><div class="s">{html.escape(scope)}</div>{counted}</div><div></div></div>'
    answered = ""
    if answer:
        answered = f'<div class="q"><b>You asked: {html.escape(answer[0])}</b><i>{html.escape(answer[1])}</i></div>'
    page = f"""{HEAD}<style>{CSS}</style></head><body class="dir">
<div class="top"><h1>Library</h1></div>
<div class="digest"><h2>Since you were last online</h2><p>{total} volumes added.{" 1 question answered." if answer else ""}</p>{answered}</div>
<div class="label">CONTENTS</div>{rows}<div style="height:30px"></div></body></html>"""
    out.write_text(page)


def render(shelf: str, out: Path, answer: tuple[str, str] | None = None) -> None:
    """One section: its volumes, latest first."""
    db = connect(DB_PATH)
    n, name, scope = next((i, nm, sc) for i, (sid, nm, sc) in enumerate(SECTIONS, start=1) if sid == shelf)
    cards, count = _cards(db, shelf)
    chips = _chip_groups(db, None, namespaces=[("type", "TYPE"), ("publisher", "PUBLISHER")], shelf=shelf)
    page = f"""{HEAD}<style>{CSS}</style></head><body>
<div class="top"><h1>{n}. {html.escape(name)}</h1><span>{html.escape(scope)}</span></div>
<div class="chips">{_sort_chips("latest")}{chips}</div><div style="height:16px"></div><div class="grid">{cards}</div><div style="height:30px"></div></body></html>"""
    out.write_text(page)


def _cards(db, shelf: str) -> tuple[str, int]:
    rows = db.execute(
        "SELECT v.id, v.title, v.publisher, v.edition, v.licence, v.page_count, v.retrieved,"
        " sv.role, c.text, c.digest_line FROM volume v JOIN shelf_volume sv ON sv.volume_id = v.id"
        " LEFT JOIN cover c ON c.volume_id = v.id WHERE sv.shelf_id = ? AND v.carry = 'carry'"
        " ORDER BY v.retrieved DESC",
        (shelf,),
    ).fetchall()
    cards = ""
    for vid, title, publisher, edition, licence, pages, retrieved, role, cover, digest in rows:
        fmt = db.execute("SELECT format FROM volume WHERE id = ?", (vid,)).fetchone()[0]
        cards += _card(vid, title, publisher, edition, pages, cover, fmt)
    return cards, len(rows)


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/progress/_library.html")
    answer = None
    if len(sys.argv) > 3:
        answer = (sys.argv[2], sys.argv[3])
    render_directory(out, answer)
    render("medicine", out.with_name("_section.html"))
    render_timeline(out.with_name("_timeline.html"))
    render_timeline(out.with_name("_timeline_filtered.html"), active="type:fact sheet")
    render_search(out.with_name("_search.html"), "signs of hypothermia")
    render_search(out.with_name("_search_filtered.html"), "how much paracetamol", tag="publisher:NHS")
    print(out)
