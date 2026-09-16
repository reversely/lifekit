"""Build library.sqlite for every shelf from the fetched volumes.

Steps: create tables, keep the cover, question, and digest rows of the previous
build, load volume rows from volumes.tsv and learned.tsv, cut pages, cut
passages, index for full-text search, apply tags, write provenance rows.
"""

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from lifekit.packs import LOCAL_PACKS

from .fetch import VOLUMES_DIR, read_volumes
from .pages import html_pages, pdf_pages
from .segment import segment
from .tags import apply_tags
from .verdicts import read_verdict

DB_PATH = LOCAL_PACKS / "library.sqlite"
SCHEMA = Path(__file__).with_name("schema.sql")
AGENT = "lifekit.library.build 0.1"

from . import sections

# First page of each FM 21-76 chapter in the 233-page scan (lifekit/reference.py).
from lifekit.reference import CHAPTER_PAGES


def page_ranges(volume_id: str) -> list[tuple[int, int | None]]:
    """A FM 21-76 chapter volume carries only its chapter pages; others carry all."""
    if not volume_id.startswith("fm-21-76-1992-ch"):
        return [(1, None)]
    ranges = []
    for piece in volume_id.split("-ch", 1)[1].split("+"):
        first, last = (piece.split("-") + [None])[:2]
        a, b = int(first), int(last or first)
        ranges.append((CHAPTER_PAGES[a], CHAPTER_PAGES.get(b + 1, 234) - 1))
    return ranges


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.execute("PRAGMA foreign_keys = ON")
    return db


def build(shelves: list[str] | None = None, db_path: Path = DB_PATH) -> dict:
    """Build every shelf that has a volume list into one library.sqlite."""
    kept: dict[str, list[tuple]] = {}
    if db_path.exists():
        old = connect(db_path)
        for table in ("cover", "question", "digest", "profile"):
            try:
                kept[table] = old.execute(f"SELECT * FROM {table}").fetchall()
            except sqlite3.OperationalError:
                kept[table] = []
        old.close()
        db_path.unlink()
    db = connect(db_path)
    db.executescript(SCHEMA.read_text())
    db.executescript(
        "CREATE TABLE IF NOT EXISTS cover (volume_id TEXT PRIMARY KEY, text TEXT, digest_line TEXT,"
        " model TEXT, at TEXT, edited INTEGER DEFAULT 0);"
    )
    for table, rows_kept in kept.items():
        for row in rows_kept:
            db.execute(f"INSERT OR IGNORE INTO {table} VALUES ({','.join('?' * len(row))})", row)
    counts = {"volumes": 0, "pages": 0, "passages": 0}
    tags_by_volume: dict[str, list[str]] = {}
    for row in sections.rows():
        shelf, order, title, scope_line = row["id"], row["order"], row["title"], row["scope"]
        if shelves and shelf not in shelves:
            continue
        if not (LOCAL_PACKS / "shelves" / shelf / "volumes.tsv").exists():
            continue
        db.execute("INSERT INTO shelf VALUES (?, ?, ?, ?, ?, ?, ?)", (shelf, order, title, scope_line, row["icon"], row["gloss"], row.get("accent")))
        for position, volume in enumerate(read_volumes(shelf), start=1):
            rule_tags = [f"section:{shelf}"] + [t.strip() for t in volume.get("tags", "").split(",") if t.strip()]
            tags_by_volume.setdefault(volume["id"], []).extend(t for t in rule_tags if t not in tags_by_volume.get(volume["id"], []))
            _load_volume(db, shelf, position, volume, counts)
        db.commit()
    for volume_id, tags in tags_by_volume.items():
        apply_tags(db, volume_id, tags)
    db.commit()
    db.close()
    return counts


def _load_volume(db, shelf, position, volume, counts) -> None:
    meta_path = VOLUMES_DIR / volume["id"] / "source.meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    seen = db.execute("SELECT 1 FROM volume WHERE id = ?", (volume["id"],)).fetchone() is not None
    db.execute(
        "INSERT OR IGNORE INTO volume (id, title, publisher, edition, url, format, licence, licence_statement,"
        " licence_read_at, retrieved, sha256, carry, freshness) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            volume["id"], volume["title"], volume["publisher"], volume["edition"], volume["url"],
            volume["format"], volume["licence"], volume["licence_statement"],
            volume["licence_read_at"], meta.get("retrieved"), meta.get("sha256"), volume["carry"],
            volume.get("freshness", "static"),
        ),
    )
    if "tier:learned" in volume.get("tags", ""):
        db.execute("UPDATE volume SET tier = 'learned' WHERE id = ?", (volume["id"],))
        verdict = read_verdict(volume["id"])
        db.execute("UPDATE volume SET admission = ?, admitted_at = ?, admitted_by = ? WHERE id = ?",
                   (verdict.get("admission", "staged"), verdict.get("at"), verdict.get("by"), volume["id"]))
    db.execute(
        "INSERT INTO shelf_volume VALUES (?,?,?,?)", (shelf, volume["id"], position, volume["role"])
    )
    if seen:
        return  # pages and passages were cut when the first shelf loaded it
    counts["volumes"] += 1
    if volume["carry"] != "carry" or not meta:
        return
    source = VOLUMES_DIR / volume["id"] / ("source.pdf" if volume["format"] == "pdf" else "source.html")
    if volume["format"] == "pdf":
        pages = []
        for first, last in page_ranges(volume["id"]):
            pages += pdf_pages(source, first, last)
    else:
        pages = html_pages(source, volume["url"])
    db.execute("UPDATE volume SET page_count = ? WHERE id = ?", (len(pages), volume["id"]))
    for page in pages:
        page_id = f"{volume['id']}/p{page['number']:03d}"
        db.execute(
            "INSERT INTO page (id, volume_id, number, anchor, text) VALUES (?,?,?,?,?)",
            (page_id, volume["id"], page["number"], page["anchor"], page["text"]),
        )
        db.execute(
            "INSERT INTO provenance VALUES (?,?,?,?,?)",
            (page_id, "segment", AGENT, json.dumps([volume["id"]]), now()),
        )
        counts["pages"] += 1
        for n, passage in enumerate(segment(page["text"]), start=1):
            passage_id = f"{page_id}/{n}"
            assert page["text"][passage["start"]:passage["end"]] == passage["text"]
            db.execute(
                "INSERT INTO passage (id, page_id, start, \"end\", text, kind) VALUES (?,?,?,?,?,?)",
                (passage_id, page_id, passage["start"], passage["end"], passage["text"], passage["kind"]),
            )
            db.execute(
                "INSERT INTO passage_fts (text, passage_id) VALUES (?, ?)", (passage["text"], passage_id)
            )
            counts["passages"] += 1


if __name__ == "__main__":
    print(build(sys.argv[1:] or None))
