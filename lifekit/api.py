"""The HTTP API the web app calls. Locally a FastAPI app; on the Space the same
functions mount beside Gradio.

    uv run uvicorn lifekit.api:app --port 8008

Endpoints
  GET  /api/health
  GET  /api/config                     model endpoints and whether the online retrieval runs
  GET  /api/search?q=&tag=            passages and matching volumes from the library
  POST /api/answer  {question, tag}   model answer that quotes passages, or a stored question
  POST /api/chat    {question, history}  a conversation turn in the library's voice, with sources
  POST /api/questions {text}          store a question (the client is offline, or nothing answered)
  POST /api/sync                       work stored questions: name, find, pull, re-ask
  GET  /api/sync/stream                the same run, one JSON record per step as it happens
  GET  /api/events?since=              the event log of every run, for the screens
  GET  /api/digest                     what arrived and what got answered, newest first
  GET  /api/library.sqlite             the current database, for the app to (re)load
  GET  /api/profile                    the household profile and the onboarding questions
  PUT  /api/profile {answers}          save answers; pull rules seed questions for the online retrieval
  GET  /api/candidates                 staged additions awaiting a verdict
  POST /api/verdict {volume, verdict, section?}   admit, refile, or reject one addition
"""

import json
import os
import threading
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from lifekit.library import chat as chats, online_retrieval, profile as profiles, provider, verdicts
from lifekit.library.build import DB_PATH, connect
from lifekit.packs import LOCAL_PACKS
from lifekit.library.query import search, volumes_matching

app = FastAPI(title="LifeKit API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

TOKEN = os.environ.get("LIFEKIT_TOKEN", "")
# Routes that change state or read private data need the box token when one is set.
GUARDED = {("POST", "/api/verdict"), ("PUT", "/api/profile"), ("POST", "/api/questions"), ("POST", "/api/sync"),
           ("GET", "/api/sync/stream"), ("GET", "/api/library.sqlite"), ("GET", "/library.sqlite"), ("GET", "/api/profile"),
           ("POST", "/api/chat"), ("POST", "/api/answer"), ("GET", "/api/digest"), ("GET", "/api/candidates"), ("GET", "/api/events")}


@app.middleware("http")
async def require_token(request, call_next):
    if TOKEN and (request.method, request.url.path) in GUARDED:
        given = request.headers.get("x-lifekit-token") or request.query_params.get("token", "")
        if given != TOKEN:
            from fastapi.responses import JSONResponse

            return JSONResponse({"error": "token required"}, status_code=401)
    return await call_next(request)


def test_run(request) -> bool:
    """A verification drive marks its requests so nothing it does is recorded as a reader's choice."""
    return request.headers.get("x-lifekit-test") == "1"


def db():
    connection = connect(DB_PATH)
    online_retrieval.ensure_tables(connection)
    return connection


def _ask(system: str, user: str, max_tokens: int = 250) -> str:
    return provider.ask(system, user, max_tokens=max_tokens)


def _answer(connection, question: str, tag: str | None = None):
    from lifekit.library.covers import ANSWER_PROMPT

    hits = search(connection, question, limit=5, tag=tag)
    if not hits:
        return "", []
    passages = "\n\n".join(f"[{h['title']}, {h['edition']}, page {h['number']}]\n{h['text']}" for h in hits)
    return provider.ask(ANSWER_PROMPT, f"Question: {question}\n\nPassages:\n{passages}", max_tokens=250, kind="answer"), hits


def _cover(volume_id: str) -> None:
    from lifekit.library.covers import write_covers_for

    write_covers_for([volume_id])


class Question(BaseModel):
    question: str
    tag: str | None = None


class Stored(BaseModel):
    text: str


class Answers(BaseModel):
    country: str | None = None
    region: str | None = None
    terrain: list[str] | None = None
    activities: list[str] | None = None
    household: list[str] | None = None
    trips: list[str] | None = None


class ChatTurn(BaseModel):
    role: str
    text: str


class ChatRequest(BaseModel):
    question: str
    history: list[ChatTurn] = []


class Verdict(BaseModel):
    volume: str
    verdict: str
    section: str | None = None


@app.get("/api/health")
def health():
    connection = db()
    n = connection.execute("SELECT count(*) FROM volume WHERE page_count > 0").fetchone()[0]
    return {"ok": True, "volumes": n}


@app.get("/api/config")
def api_config():
    import csv

    from lifekit.library import sections, zim

    with (LOCAL_PACKS / "questions.tsv").open(newline="") as handle:
        questions: dict[str, list[str]] = {}
        for row in csv.DictReader(handle, delimiter="\t"):
            questions.setdefault(row["kind"], []).append(row["text"])
    return {**provider.describe(), "zim": zim.describe(), "sections": sections.rows(), "questions": questions}


@app.get("/api/search")
def api_search(q: str, tag: str | None = None):
    connection = db()
    return {"hits": search(connection, q, limit=8, tag=tag), "volumes": volumes_matching(connection, q)}


@app.post("/api/answer")
def api_answer(body: Question):
    connection = db()
    from lifekit.library.covers import covered, strip_verdict

    text, hits = _answer(connection, body.question, body.tag)
    if not hits or not covered(text):
        topic, wanted = online_retrieval.gap_record(_ask, body.question) if provider.online_retrieval_enabled() else (None, None)
        qid = online_retrieval.store_question(connection, body.question, profiles.get(connection), topic=topic, wanted=wanted)
        return {"answered": False, "stored": qid, "hits": hits, "note": strip_verdict(text), "topic": topic, "wanted": wanted}
    return {"answered": True, "answer": strip_verdict(text), "hits": hits[:3]}


@app.post("/api/questions")
def api_store(body: Stored):
    """A question the browser held while it was offline. Nemotron on the box writes the
    missing-document record now, so the queue holds the topic and the kind of document
    wanted before any retrieval runs."""
    connection = db()
    topic, wanted = online_retrieval.gap_record(_ask, body.text) if provider.online_retrieval_enabled() else (None, None)
    qid = online_retrieval.store_question(connection, body.text, profiles.get(connection), topic=topic, wanted=wanted)
    wake_retrieval()
    return {"stored": qid, "topic": topic, "wanted": wanted}


@app.post("/api/sync")
def api_sync():
    connection = db()
    if not provider.online_retrieval_enabled():
        return {"digest": [], "events": ["The online retrieval is off on this instance."], "pending": online_retrieval.pending(connection)}
    events: list[str] = []
    digest = online_retrieval.retrieve_for_queue(connection, _ask, _answer, covers=_cover, log=events.append)
    return {"digest": digest, "events": events, "pending": online_retrieval.pending(connection)}


@app.post("/api/chat")
def api_chat(body: ChatRequest):
    connection = db()
    reply = chats.answer(connection, body.question, [t.model_dump() for t in body.history], profiles.get(connection))
    if reply.get("queued"):
        wake_retrieval()
    return reply


@app.get("/api/profile")
def api_profile():
    connection = db()
    current = profiles.get(connection)
    return {"profile": current, "questions": profiles.questions(current), "summary": profiles.describe(current)}


@app.put("/api/profile")
def api_profile_save(body: Answers):
    connection = db()
    saved = profiles.save(connection, {k: v for k, v in body.model_dump().items() if v is not None})
    seeded = profiles.evaluate(connection, saved)
    return {"profile": saved, "questions": profiles.questions(saved), "summary": profiles.describe(saved), "seeded": seeded}


@app.get("/api/candidates")
def api_candidates():
    return {"candidates": online_retrieval.candidates(db())}


@app.post("/api/verdict")
def api_verdict(body: Verdict, request: Request):
    if not online_retrieval.valid_id(body.volume):
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="invalid volume id")
    try:
        return verdicts.apply(db(), body.volume, body.verdict, body.section, by="test" if test_run(request) else "reader")
    except (ValueError, KeyError) as error:
        return {"error": str(error)}


@app.get("/api/sync/stream")
def api_sync_stream():
    """The same pass as POST /api/sync, streamed as one JSON record per line while
    the online retrieval works, so the screen can show each step. Ends with a {"done": ...} line."""
    import queue
    import threading

    from fastapi.responses import StreamingResponse

    def generate():
        if not provider.online_retrieval_enabled():
            yield json.dumps({"done": True, "digest": [], "note": "The online retrieval is off on this instance."}) + "\n"
            return
        events: "queue.Queue[dict | None]" = queue.Queue()
        result: dict = {}

        def run():
            try:
                connection = db()  # sqlite connections stay on the thread that made them
                result["digest"] = online_retrieval.retrieve_for_queue(connection, _ask, _answer, covers=_cover, log=lambda _: None, event=events.put)
            except Exception as error:  # noqa: BLE001
                result["error"] = str(error)
            finally:
                events.put(None)

        threading.Thread(target=run, daemon=True).start()
        while True:
            record = events.get()
            if record is None:
                break
            yield json.dumps(record) + "\n"
        yield json.dumps({"done": True, "digest": result.get("digest", []), "error": result.get("error"), "pending": online_retrieval.pending(db())}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@app.get("/api/events")
def api_events(since: int = 0):
    """The event log of online retrieval: one record per step, however the run started."""
    return {"events": online_retrieval.events(db(), since=since)}


# Online retrieval on the box, started by the queue (#26): a thread waits for a wake
# signal, sent when a question is stored, and also wakes every minute while the queue
# holds questions, so a question queued during an internet outage runs once the internet
# returns. Nothing in a browser is needed.
_wake = threading.Event()
_worker_started = False


def wake_retrieval() -> None:
    _wake.set()


def _retrieval_worker() -> None:
    from lifekit.library.chat import internet_reachable

    while True:
        _wake.wait(timeout=60)
        _wake.clear()
        try:
            connection = db()
            if not provider.online_retrieval_enabled() or not online_retrieval.pending(connection):
                continue
            if not internet_reachable():
                continue
            online_retrieval.retrieve_for_queue(connection, _ask, _answer, covers=_cover, log=lambda _: None)
        except Exception as error:  # noqa: BLE001
            print(f"retrieval worker: {error}")


@app.on_event("startup")
def start_worker() -> None:
    global _worker_started
    if os.environ.get("LIFEKIT_QUEUE_WORKER", "on") != "off" and not _worker_started:
        threading.Thread(target=_retrieval_worker, daemon=True, name="online-retrieval").start()
        _worker_started = True


@app.get("/api/digest")
def api_digest():
    connection = db()
    rows = connection.execute(
        "SELECT d.question_id, q.text, d.answer, d.volumes, d.at, q.state FROM digest d JOIN question q ON q.id = d.question_id ORDER BY d.at DESC LIMIT 20"
    ).fetchall()
    added = connection.execute(
        "SELECT v.id, v.title, v.publisher, v.retrieved, c.digest_line, v.admission FROM volume v LEFT JOIN cover c ON c.volume_id = v.id"
        " WHERE v.tier = 'learned' AND v.admission != 'rejected' ORDER BY v.retrieved DESC LIMIT 20"
    ).fetchall()
    return {
        "answered": [{"id": r[0], "question": r[1], "answer": r[2], "volumes": json.loads(r[3] or "[]"), "at": r[4], "state": r[5]} for r in rows],
        "added": [{"id": r[0], "title": r[1], "publisher": r[2], "retrieved": r[3], "line": r[4], "admission": r[5]} for r in added],
        "candidates": online_retrieval.candidates(connection),
        "pending": online_retrieval.pending(connection),
    }


@app.get("/api/library.sqlite")
@app.get("/library.sqlite")
def api_db():
    """The live database. The app fetches /library.sqlite, so this route must
    precede the static mount or the build's copy would answer instead."""
    return FileResponse(Path(DB_PATH), media_type="application/octet-stream", headers={"Cache-Control": "no-store"})


WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"


@app.get("/thumbs/{volume_id}.png")
def api_thumb(volume_id: str):
    """A thumbnail for every volume: the build's file when present, else one rendered
    on demand (first PDF page, or a typographic tile for an HTML article)."""
    from fastapi import HTTPException

    from lifekit.library.render import thumbnail

    built = WEB_DIST / "thumbs" / f"{volume_id}.png"
    if built.exists():
        return FileResponse(built, media_type="image/png")
    row = db().execute("SELECT format, title, publisher FROM volume WHERE id = ?", (volume_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404)
    try:
        path = thumbnail(volume_id, row[0], row[1] or "", row[2] or "")
    except Exception:  # noqa: BLE001  a missing source file: fall back to the tile
        path = thumbnail(volume_id, "html", row[1] or "", row[2] or "")
    return FileResponse(path, media_type="image/png")


# The built web app, when present, so one process serves an instance. The SQLite
# wasm loads the database into memory and needs no cross-origin isolation, and a
# box serves plain HTTP on a LAN address where Chrome would ignore the headers.
if WEB_DIST.is_dir():
    from starlette.staticfiles import StaticFiles

    from starlette.middleware.base import BaseHTTPMiddleware

    class _NoCacheHtml(BaseHTTPMiddleware):
        # index.html carries the hashed asset names; a cached copy shows an old build.
        async def dispatch(self, request, call_next):
            response = await call_next(request)
            if response.headers.get("content-type", "").startswith("text/html"):
                response.headers["Cache-Control"] = "no-cache"
            return response

    app.add_middleware(_NoCacheHtml)
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
