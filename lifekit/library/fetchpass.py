"""The fetch pass: store, name, find a source, pull it as a volume, re-ask, digest.

States of a stored question, per docs/content/library-schema.md 1.9:
stored -> named -> searching -> staged -> extracted -> indexed -> re_asked -> resolved | exhausted

Sources are searched in licence order. This prototype searches Wikipedia (CC BY-SA 4.0),
which is the open encyclopedic class; agency classes join as their fetchers exist.
"""

import hashlib
import json
import re
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from .build import DB_PATH, connect, now
from .fetch import UA, VOLUMES_DIR
from .pages import html_pages
from .segment import segment
from .tags import apply_tags
from . import zim
from .verdicts import filing_examples, rejected_ids

WIKI_SEARCH = "https://en.wikipedia.org/w/api.php?action=query&list=search&format=json&srlimit=8&srsearch="
WIKI_PAGE = "https://en.wikipedia.org/wiki/"
from . import sections

TOPIC_PROMPT = (
    "Name the topic of this question in one to four words, as a noun phrase a librarian "
    "would file it under. Output the phrase only. If the question is small talk or a "
    "greeting, output the word none."
)
SECTION_PROMPT = (
    "Choose the one section of a survival library this document belongs in. Sections and what "
    "they hold: " + sections.filing_list() + ". Output one section id from that list and "
    "nothing else. Example: Question: how to remove a tick. Topic: ticks. Output: animals"
)
PICK_PROMPT = (
    "A question needs a document. You are given numbered Wikipedia article titles from a search. "
    "Output the numbers of the articles whose subject would answer the question, best first, at "
    "most two, separated by commas. Prefer a general article about the subject over an article "
    "about one event, person, place, or work. If none would answer it, output none. Output only "
    "the numbers or the word none."
)


def _get(url: str, timeout: int = 60) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": UA + " lifekit-fetch/0.1", "Accept": "*/*"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


# -- questions -----------------------------------------------------------------

GAP_PROMPT = (
    "A question could not be answered from a library of documents. Write two lines. "
    "Line 1: 'Topic: ' then the topic in one to four words, as a noun phrase a librarian would "
    "file it under. Line 2: 'Wanted: ' then one sentence naming the kind of document that would "
    "answer it (for example: a first aid guideline on insect stings). Output the two lines only."
)


def store_question(db: sqlite3.Connection, text: str, profile: dict | None = None,
                   origin: str = "asked", topic: str | None = None, wanted: str | None = None) -> str:
    qid = "q_" + hashlib.sha1((text + now()).encode()).hexdigest()[:10]
    db.execute(
        "INSERT INTO question (id, text, profile_snapshot, asked_at, state, origin, topic, wanted) VALUES (?,?,?,?,?,?,?,?)",
        (qid, text, json.dumps(profile or {}), now(), "stored", origin, topic, wanted),
    )
    db.commit()
    return qid


def gap_record(ask, text: str) -> tuple[str | None, str | None]:
    """The model's own statement of what is missing: (topic, wanted)."""
    try:
        reply = ask(GAP_PROMPT, text)
    except Exception:  # noqa: BLE001
        return None, None
    topic = wanted = None
    for line in reply.splitlines():
        low = line.strip().lower()
        if low.startswith("topic:"):
            topic = line.split(":", 1)[1].strip().strip('."').lower() or None
        elif low.startswith("wanted:"):
            wanted = line.split(":", 1)[1].strip() or None
    return topic, wanted


def candidates(db: sqlite3.Connection) -> list[dict]:
    """Staged volumes with the question that pulled them and the answer they gave."""
    out = []
    for vid, title, publisher, licence, retrieved, cover in db.execute(
        "SELECT v.id, v.title, v.publisher, v.licence, v.retrieved, c.text FROM volume v"
        " LEFT JOIN cover c ON c.volume_id = v.id WHERE v.admission = 'staged' ORDER BY v.retrieved DESC"
    ):
        section = db.execute("SELECT shelf_id FROM shelf_volume WHERE volume_id = ?", (vid,)).fetchone()
        prov = db.execute("SELECT derived_from FROM provenance WHERE entity_id = ? AND activity = 'pull' ORDER BY at DESC", (vid,)).fetchone()
        qids = json.loads(prov[0]) if prov else []
        question = None
        if qids:
            q = db.execute("SELECT q.id, q.text, q.wanted, q.state, d.answer FROM question q LEFT JOIN digest d ON d.question_id = q.id WHERE q.id = ?", (qids[0],)).fetchone()
            if q:
                question = {"id": q[0], "text": q[1], "wanted": q[2], "state": q[3], "answer": q[4]}
        out.append({"id": vid, "title": title, "publisher": publisher, "licence": licence, "retrieved": retrieved,
                    "cover": cover, "section": section[0] if section else None, "question": question})
    return out


def set_state(db, qid: str, state: str, **fields) -> None:
    sets = ", ".join(f"{k} = ?" for k in fields)
    db.execute(f"UPDATE question SET state = ?{', ' + sets if sets else ''} WHERE id = ?", (state, *fields.values(), qid))
    db.commit()


def pending(db) -> list[dict]:
    return [
        {"id": r[0], "text": r[1], "state": r[2], "topic": r[3], "origin": r[4]}
        for r in db.execute("SELECT id, text, state, topic, origin FROM question WHERE state NOT IN ('resolved', 'exhausted') ORDER BY asked_at")
    ]


# -- sources -------------------------------------------------------------------

def wikipedia_candidates(topic: str) -> list[dict]:
    body = _get(WIKI_SEARCH + urllib.parse.quote(topic))
    hits = json.loads(body)["query"]["search"]
    return [{"title": h["title"], "url": WIKI_PAGE + h["title"].replace(" ", "_")} for h in hits]


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def pull_wikipedia(db, candidate: dict, section: str, question_id: str) -> str:
    """Fetch one article, cut it, index it, tag it. Returns the volume id."""
    volume_id = f"wikipedia-{slug(candidate['title'])}"
    if volume_id in rejected_ids():
        raise RuntimeError(f"{volume_id}: rejected by the owner earlier")
    if db.execute("SELECT 1 FROM volume WHERE id = ? AND page_count > 0", (volume_id,)).fetchone():
        # already in the library; a pull is idempotent, but the question still links to it
        db.execute("INSERT INTO provenance VALUES (?,?,?,?,?)",
                   (volume_id, "pull", "lifekit.library.fetchpass 0.1", json.dumps([question_id]), now()))
        db.commit()
        return volume_id
    dest = VOLUMES_DIR / volume_id
    dest.mkdir(parents=True, exist_ok=True)
    if candidate.get("zim_path"):
        body = zim.clean_html(zim.article_html(candidate["zim_path"]))
        fetched_by = f"lifekit.library.fetchpass 0.1 from {zim.available().name}"
    else:
        body = _get(candidate["url"])
        fetched_by = "lifekit.library.fetchpass 0.1"
    (dest / "source.html").write_bytes(body)
    sha = hashlib.sha256(body).hexdigest()
    retrieved = now()
    (dest / "source.meta.json").write_text(json.dumps({
        "id": volume_id, "url": candidate["url"], "sha256": sha, "bytes": len(body),
        "content_type": "text/html", "retrieved": retrieved, "fetched_by": fetched_by,
    }, indent=1))
    db.execute("DELETE FROM passage_fts WHERE passage_id IN (SELECT id FROM passage WHERE page_id IN (SELECT id FROM page WHERE volume_id = ?))", (volume_id,))
    db.execute("DELETE FROM passage WHERE page_id IN (SELECT id FROM page WHERE volume_id = ?)", (volume_id,))
    db.execute("DELETE FROM page WHERE volume_id = ?", (volume_id,))
    db.execute("DELETE FROM shelf_volume WHERE volume_id = ?", (volume_id,))
    db.execute("DELETE FROM volume WHERE id = ?", (volume_id,))
    db.execute(
        "INSERT INTO volume (id, title, publisher, edition, url, format, licence, licence_statement, licence_read_at,"
        " retrieved, sha256, carry, tier, freshness) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (volume_id, candidate["title"], "Wikipedia", retrieved[:10], candidate["url"], "html",
         "CC-BY-SA-4.0", "Text is available under the Creative Commons Attribution-ShareAlike 4.0 License; "
         "the authors are the article's editors, listed in its page history",
         candidate["url"] + "?action=history", retrieved, sha, "carry", "learned", "live"),
    )
    db.execute("UPDATE volume SET admission = 'staged' WHERE id = ?", (volume_id,))
    order = db.execute("SELECT coalesce(max(\"order\"), 0) + 1 FROM shelf_volume WHERE shelf_id = ?", (section,)).fetchone()[0]
    db.execute("INSERT INTO shelf_volume VALUES (?,?,?,?)", (section, volume_id, order, "reference"))
    pages = html_pages(dest / "source.html", candidate["url"])
    for page in pages:
        page_id = f"{volume_id}/p{page['number']:03d}"
        db.execute("INSERT INTO page (id, volume_id, number, anchor, text) VALUES (?,?,?,?,?)",
                   (page_id, volume_id, page["number"], page["anchor"], page["text"]))
        for n, passage in enumerate(segment(page["text"]), start=1):
            pid = f"{page_id}/{n}"
            db.execute("INSERT INTO passage (id, page_id, start, \"end\", text, kind) VALUES (?,?,?,?,?,?)",
                       (pid, page_id, passage["start"], passage["end"], passage["text"], passage["kind"]))
            db.execute("INSERT INTO passage_fts (text, passage_id) VALUES (?, ?)", (passage["text"], pid))
    db.execute("UPDATE volume SET page_count = ? WHERE id = ?", (len(pages), volume_id))
    apply_tags(db, volume_id, [f"section:{section}", "type:encyclopedia", "publisher:Wikipedia", "tier:learned"])
    _record_learned(section, volume_id, candidate, retrieved)
    db.execute("INSERT INTO provenance VALUES (?,?,?,?,?)", (volume_id, "pull", "lifekit.library.fetchpass 0.1", json.dumps([question_id]), now()))
    db.commit()
    return volume_id


def _record_learned(section: str, volume_id: str, candidate: dict, retrieved: str) -> None:
    """Append the volume to the shelf's learned.tsv so a rebuild keeps it."""
    import csv

    from lifekit.packs import LOCAL_PACKS

    path = LOCAL_PACKS / "shelves" / section / "learned.tsv"
    cols = ["id", "title", "publisher", "edition", "url", "format", "licence", "licence_statement",
            "licence_read_at", "carry", "role", "freshness", "tags"]
    existing = set()
    if path.exists():
        with path.open(newline="") as handle:
            existing = {r["id"] for r in csv.DictReader(handle, delimiter="\t")}
    if volume_id in existing:
        return
    new = not path.exists()
    with path.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=cols, delimiter="\t", lineterminator="\n")
        if new:
            writer.writeheader()
        writer.writerow({
            "id": volume_id, "title": candidate["title"], "publisher": "Wikipedia",
            "edition": retrieved[:10], "url": candidate["url"], "format": "html", "licence": "CC-BY-SA-4.0",
            "licence_statement": "Text is available under the Creative Commons Attribution-ShareAlike 4.0 License; "
            "the authors are the article's editors, listed in its page history",
            "licence_read_at": candidate["url"] + "?action=history", "carry": "carry",
            "role": "reference", "freshness": "live", "tags": "type:encyclopedia,publisher:Wikipedia,tier:learned",
        })


_NOT_A_SUBJECT = re.compile(
    r"\((?:\d{4} )?(?:film|novel|album|song|band|EP|TV series|television series|video game|comics|magazine|"
    r"play|musical|poem|painting|character|episode)\)$|^\d{4} |^List of .* (?:episodes|characters)", re.I)


def pick(ask, question: str, candidates: list[dict]) -> list[dict]:
    """The model chooses which search hits would answer the question, at most two.
    Titles that name a work, an episode, or a dated event never reach it."""
    candidates = [c for c in candidates if not _NOT_A_SUBJECT.search(c["title"])]
    if not candidates:
        return []
    listing = "\n".join(f"{i + 1}. {c['title']}" for i, c in enumerate(candidates))
    said = ask(PICK_PROMPT, f"Question: {question}\n\nArticles:\n{listing}").strip().lower()
    if said.startswith("none"):
        return []
    chosen = []
    for token in re.findall(r"\d+", said):
        index = int(token) - 1
        if 0 <= index < len(candidates) and candidates[index] not in chosen:
            chosen.append(candidates[index])
    return chosen[:2] or candidates[:1]


def choose_section(ask, prompt: str, question: str, topic: str) -> str:
    """One section id; a reply that names none gets one stricter retry, then tools."""
    for attempt in range(2):
        user = f"Question: {question}\nTopic: {topic}"
        if attempt:
            user += "\nAnswer with exactly one of: " + ", ".join(sections.ids())
        said = ask(prompt, user).strip().lower()
        hit = next((s for s in sorted(sections.ids(), key=len, reverse=True) if s in said), None)
        if hit:
            return hit
    return sections.ids()[-5]  # tools, the catch-all for equipment and repairs


# -- the pass ------------------------------------------------------------------

def work(db, ask, answer, covers=None, log=print, event=None) -> list[dict]:
    """Work every pending question once. `ask(system, user)` calls the model; `answer(db, question)`
    returns (text, hits). `event(dict)` receives one record per step as it happens, so a
    screen can show the fetch pass working. Returns the digest entries produced."""
    from .query import search

    def emit(qid: str, step: str, **fields) -> None:
        record = {"question": qid, "step": step, "at": now(), **fields}
        if event:
            event(record)
        log(f"{qid}: {step} " + " ".join(f"{k}={v}" for k, v in fields.items() if k != "text"))

    digest = []
    examples = "".join(f"\nExample: {q} -> {s}" for q, s in filing_examples())
    for q in pending(db):
        qid, text = q["id"], q["text"]
        emit(qid, "start", text=text, origin=q.get("origin"))
        topic = q.get("topic") or ask(TOPIC_PROMPT, text).strip().strip('."').lower()
        if not topic or topic == "none":
            set_state(db, qid, "exhausted", topic=topic)
            emit(qid, "exhausted", reason="no topic")
            continue
        set_state(db, qid, "named", topic=topic)
        emit(qid, "named", topic=topic)
        candidates = []
        source = None
        if zim.available():
            try:
                candidates = zim.search(topic)
                source = zim.available().name
            except Exception as error:  # noqa: BLE001
                emit(qid, "search_failed", source="zim", error=str(error)[:120])
        if not candidates:
            try:
                candidates = wikipedia_candidates(topic)
                source = "en.wikipedia.org"
            except Exception as error:  # noqa: BLE001
                emit(qid, "search_failed", source="live", error=str(error)[:120])
                continue
        set_state(db, qid, "searching")
        emit(qid, "searched", source=source, titles=[c["title"] for c in candidates])
        candidates = pick(ask, text, candidates)
        if not candidates:
            set_state(db, qid, "exhausted")
            emit(qid, "exhausted", reason="no article fits")
            continue
        emit(qid, "picked", titles=[c["title"] for c in candidates])
        section = choose_section(ask, SECTION_PROMPT + examples, text, topic)
        emit(qid, "filed", section=section)
        pulled = []
        for candidate in candidates[:2]:
            try:
                vid = pull_wikipedia(db, candidate, section, qid)
                pulled.append(vid)
                emit(qid, "pulled", volume=vid, title=candidate["title"], section=section)
            except Exception as error:  # noqa: BLE001
                emit(qid, "pull_failed", title=candidate["title"], error=str(error)[:120])
        if not pulled:
            set_state(db, qid, "exhausted")
            continue
        set_state(db, qid, "indexed")
        if covers:
            for vid in pulled:
                covers(vid)
            emit(qid, "covered", volumes=pulled)
        # Re-ask with the topic's words beside the question's, so a source that spells or
        # names the thing differently ("tire" for "tyre") can still be found.
        from .covers import covered as is_covered, strip_verdict

        text_answer, hits = answer(db, f"{text} {topic}")
        hit_ids = [h["passage"] for h in hits[:3]]
        covered = bool(hits) and is_covered(text_answer)
        text_answer = strip_verdict(text_answer)
        set_state(db, qid, "resolved" if covered else "exhausted", answer_passages=json.dumps(hit_ids))
        db.execute("INSERT OR REPLACE INTO digest (question_id, answer, volumes, at) VALUES (?,?,?,?)",
                   (qid, text_answer, json.dumps(pulled), now()))
        db.commit()
        emit(qid, "resolved" if covered else "exhausted", answer=text_answer[:400],
             pages=[{"title": h["title"], "page": h["number"], "volume": h["volume"], "passage": h["passage"]} for h in hits[:2]])
        digest.append({"question": text, "answer": text_answer, "volumes": pulled, "state": "resolved" if covered else "exhausted"})
    return digest


def ensure_tables(db) -> None:
    db.executescript(
        "CREATE TABLE IF NOT EXISTS question (id TEXT PRIMARY KEY, text TEXT NOT NULL, profile_snapshot TEXT,"
        " asked_at TEXT, state TEXT NOT NULL DEFAULT 'stored', topic TEXT, answer_passages TEXT);"
        "CREATE TABLE IF NOT EXISTS digest (question_id TEXT PRIMARY KEY, answer TEXT, volumes TEXT, at TEXT);"
        "CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY CHECK (id = 1), country TEXT, region TEXT,"
        " terrain TEXT DEFAULT '[]', activities TEXT DEFAULT '[\"home\"]', household TEXT DEFAULT '[\"adult\"]',"
        " trips TEXT DEFAULT '[]', updated_at TEXT);"
    )
    # columns added after the first databases were built
    for table, column, ddl in (
        ("question", "wanted", "TEXT"), ("question", "origin", "TEXT NOT NULL DEFAULT 'asked'"),
        ("volume", "admission", "TEXT NOT NULL DEFAULT 'stock'"), ("volume", "admitted_at", "TEXT"), ("volume", "admitted_by", "TEXT"),
    ):
        if column not in [c[1] for c in db.execute(f"PRAGMA table_info({table})")]:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
    db.commit()
