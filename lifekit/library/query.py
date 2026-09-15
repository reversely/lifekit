"""Search the library and run its RAG tests.

    uv run python -m lifekit.library.query "how long can a tourniquet stay on"
    uv run python -m lifekit.library.query --tests
    uv run python -m lifekit.library.query --entry medicine/bleeding

Ranking combines the FTS5 bm25 score with the volume's shelf role: primary
first, then reference and depth, figures, archive.
"""

import json
import re
import sqlite3
import sys
from datetime import datetime, timezone

from .build import DB_PATH, connect

ROLE_RANK = {"primary": 0.0, "reference": 0.5, "depth": 0.7, "figures": 1.0, "archive": 2.0}
_TOKEN = re.compile(r"[A-Za-z0-9]+")


_STOP = {"the", "and", "for", "how", "can", "what", "with", "you", "are", "should", "long", "stay",
         "who", "someone", "very", "not", "when", "does", "did", "put", "get", "into", "from", "this",
         "that", "there", "they", "them", "their", "your", "our", "his", "her", "its"}


def _words(question: str) -> list[str]:
    words = [w for w in _TOKEN.findall(question.lower()) if len(w) > 2 and w not in _STOP]
    return words or _TOKEN.findall(question.lower())


def _fts_queries(question: str) -> list[str]:
    """Strictest first: every word, then all but one, then any word."""
    words = _words(question)
    queries = [" AND ".join(words)]
    if len(words) > 2:
        queries.append(" OR ".join(f"({' AND '.join(w for w in words if w != drop)})" for drop in words))
    queries.append(" OR ".join(words))
    return queries


def search(db: sqlite3.Connection, question: str, limit: int = 5, tag: str | None = None) -> list[dict]:
    """Full-text search over passages, with role and kind adjustments and an
    optional tag filter."""
    lexical: list[dict] = []
    for query in _fts_queries(question):
        lexical = _search(db, query, 40)
        if len(lexical) >= 3:
            break
    fused: dict[str, float] = {}
    rows: dict[str, dict] = {}
    for rank, r in enumerate(lexical):
        fused[r["passage"]] = fused.get(r["passage"], 0) + 1 / (60 + rank)
        rows[r["passage"]] = r
    results = []
    for pid, score in fused.items():
        r = rows[pid]
        if r is None:
            continue
        bonus = 0.004 * (2.0 - ROLE_RANK.get(r["role"], 1.0)) / 2.0
        if r["kind"] in ("procedure_step", "checklist", "warning"):
            bonus += 0.002
        r["score"] = round(score + bonus, 4)
        results.append(r)
    if tag:
        allowed = {v for (v,) in db.execute("SELECT volume_id FROM volume_tag WHERE tag = ?", (tag,))}
        results = [r for r in results if r["volume"] in allowed]
    results.sort(key=lambda r: -r["score"])
    return results[:limit]


def _row(db: sqlite3.Connection, passage_id: str) -> dict | None:
    row = db.execute(
        "SELECT s.id, s.text, s.kind, p.id, p.number, p.anchor, v.id, v.title, v.edition, sv.role"
        " FROM passage s JOIN page p ON p.id = s.page_id JOIN volume v ON v.id = p.volume_id"
        " JOIN shelf_volume sv ON sv.volume_id = v.id WHERE s.id = ?", (passage_id,)
    ).fetchone()
    if row is None:
        return None
    return {"passage": row[0], "score": 0.0, "text": row[1], "kind": row[2], "page": row[3],
            "number": row[4], "anchor": row[5], "volume": row[6], "title": row[7],
            "edition": row[8], "role": row[9]}


def _search(db: sqlite3.Connection, query: str, limit: int) -> list[dict]:
    rows = db.execute(
        "SELECT f.passage_id, bm25(passage_fts) AS score, s.text, s.kind, p.id, p.number, p.anchor,"
        " v.id, v.title, v.edition, sv.role"
        " FROM passage_fts f JOIN passage s ON s.id = f.passage_id JOIN page p ON p.id = s.page_id"
        " JOIN volume v ON v.id = p.volume_id JOIN shelf_volume sv ON sv.volume_id = v.id"
        " WHERE passage_fts MATCH ? AND v.admission != 'rejected' ORDER BY score LIMIT 60",
        (query,),
    ).fetchall()
    results = []
    for row in rows:
        score = row[1] + ROLE_RANK.get(row[10], 1.0)  # bm25 is negative; lower is better
        if row[3] in ("procedure_step", "checklist", "warning"):
            score -= 1.0  # a how-to question prefers a step over a discussion of the evidence
        results.append({
            "passage": row[0], "score": round(score, 2), "text": row[2], "kind": row[3],
            "page": row[4], "number": row[5], "anchor": row[6], "volume": row[7],
            "title": row[8], "edition": row[9], "role": row[10],
        })
    results.sort(key=lambda r: r["score"])
    return results[:limit]


def volumes_matching(db: sqlite3.Connection, question: str, limit: int = 3) -> list[dict]:
    """Volumes whose title or cover matches the words, for the top of a search screen."""
    words = _words(question)
    like = " OR ".join("(lower(v.title) LIKE ? OR lower(c.text) LIKE ?)" for _ in words)
    params = [p for w in words for p in (f"%{w}%", f"%{w}%")]
    rows = db.execute(
        "SELECT v.id, v.title, v.edition, c.text FROM volume v LEFT JOIN cover c ON c.volume_id = v.id"
        f" WHERE v.carry = 'carry' AND v.admission != 'rejected' AND ({like}) LIMIT ?", (*params, limit)
    ).fetchall()
    return [{"volume": r[0], "title": r[1], "edition": r[2], "cover": r[3]} for r in rows]


def run_tests(db: sqlite3.Connection) -> tuple[int, int]:
    passed = total = 0
    for test_id, question, expected in db.execute("SELECT id, question, expected_passages FROM rag_test"):
        expected = set(json.loads(expected))
        top = {r["passage"] for r in search(db, question, limit=3)}
        ok = bool(expected & top)
        db.execute(
            "UPDATE rag_test SET last_run = ?, last_pass = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(timespec="seconds"), int(ok), test_id),
        )
        total += 1
        passed += ok
        print(f"{'pass' if ok else 'FAIL'}  {test_id}  {question}")
        if not ok:
            for r in search(db, question, limit=3):
                print(f"      got {r['passage']} ({r['role']})")
    db.commit()
    return passed, total


def show_entry(db: sqlite3.Connection, entry_id: str) -> None:
    entry = db.execute("SELECT title, gloss, kind FROM entry WHERE id = ?", (entry_id,)).fetchone()
    print(f"# {entry[0]}\n{entry[1]}\n")
    revision = db.execute(
        "SELECT id, approval FROM entry_revision WHERE entry_id = ? ORDER BY id DESC LIMIT 1", (entry_id,)
    ).fetchone()
    print(f"revision {revision[0]} ({revision[1]})\n")
    for block_id, kind, text in db.execute(
        "SELECT id, kind, text FROM block WHERE revision_id = ? ORDER BY \"order\"", (revision[0],)
    ):
        print(f"[{kind}] {text}")
        for passage_id, role in db.execute(
            "SELECT passage_id, role FROM block_cites WHERE block_id = ?", (block_id,)
        ):
            volume, number, anchor = db.execute(
                "SELECT v.title || ', ' || v.edition, p.number, p.anchor FROM passage s"
                " JOIN page p ON p.id = s.page_id JOIN volume v ON v.id = p.volume_id WHERE s.id = ?",
                (passage_id,),
            ).fetchone()
            print(f"    {role}: {volume}, p. {number}  ({passage_id})")
        print()
    for to_entry, to_volume, kind, label in db.execute(
        "SELECT to_entry, to_volume, kind, label FROM entry_links WHERE from_revision = ?", (revision[0],)
    ):
        print(f"link {kind}: {label} -> {to_entry or to_volume}")


def main(argv: list[str]) -> None:
    db = connect(DB_PATH)
    if "--tests" in argv:
        passed, total = run_tests(db)
        print(f"{passed}/{total} passed")
        return
    if "--entry" in argv:
        show_entry(db, argv[argv.index("--entry") + 1])
        return
    question = " ".join(a for a in argv[1:] if not a.startswith("--"))
    for r in search(db, question):
        print(f"{r['score']:6.2f}  {r['role']:9s} {r['title']}, {r['edition']}, p. {r['number']}  {r['passage']}")
        print("        " + r["text"][:300].replace("\n", " / "))
        print()


if __name__ == "__main__":
    main(sys.argv)
