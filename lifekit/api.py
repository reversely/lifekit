"""The HTTP API the web app calls. Locally a FastAPI app; on the Space the same
functions mount beside Gradio.

    uv run uvicorn lifekit.api:app --port 8008

Endpoints
  GET  /api/health
  GET  /api/config                     model endpoints and whether the loop runs
  GET  /api/search?q=&tag=            passages and matching volumes from the library
  POST /api/answer  {question, tag}   model answer that quotes passages, or a stored question
  POST /api/questions {text}          store a question (the client is offline, or nothing answered)
  POST /api/sync                       work stored questions: name, find, pull, re-ask
  GET  /api/digest                     what arrived and what got answered, newest first
  GET  /api/library.sqlite             the current database, for the app to (re)load
"""

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from lifekit.library import loop, provider
from lifekit.library.build import DB_PATH, connect
from lifekit.library.query import search, volumes_matching

app = FastAPI(title="LifeKit API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def db():
    connection = connect(DB_PATH)
    loop.ensure_tables(connection)
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


@app.get("/api/health")
def health():
    connection = db()
    n = connection.execute("SELECT count(*) FROM volume WHERE page_count > 0").fetchone()[0]
    return {"ok": True, "volumes": n}


@app.get("/api/config")
def api_config():
    return provider.describe()


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
        qid = loop.store_question(connection, body.question)
        return {"answered": False, "stored": qid, "hits": hits, "note": strip_verdict(text)}
    return {"answered": True, "answer": strip_verdict(text), "hits": hits[:3]}


@app.post("/api/questions")
def api_store(body: Stored):
    return {"stored": loop.store_question(db(), body.text)}


@app.post("/api/sync")
def api_sync():
    connection = db()
    if not provider.loop_enabled():
        return {"digest": [], "events": ["The loop is off on this instance."], "pending": loop.pending(connection)}
    events: list[str] = []
    digest = loop.work(connection, _ask, _answer, covers=_cover, log=events.append)
    return {"digest": digest, "events": events, "pending": loop.pending(connection)}


@app.get("/api/digest")
def api_digest():
    connection = db()
    rows = connection.execute(
        "SELECT d.question_id, q.text, d.answer, d.volumes, d.at, q.state FROM digest d JOIN question q ON q.id = d.question_id ORDER BY d.at DESC LIMIT 20"
    ).fetchall()
    added = connection.execute(
        "SELECT v.id, v.title, v.publisher, v.retrieved, c.digest_line FROM volume v LEFT JOIN cover c ON c.volume_id = v.id"
        " WHERE v.tier = 'learned' ORDER BY v.retrieved DESC LIMIT 20"
    ).fetchall()
    return {
        "answered": [{"id": r[0], "question": r[1], "answer": r[2], "volumes": json.loads(r[3] or "[]"), "at": r[4], "state": r[5]} for r in rows],
        "added": [{"id": r[0], "title": r[1], "publisher": r[2], "retrieved": r[3], "line": r[4]} for r in added],
    }


@app.get("/api/library.sqlite")
def api_db():
    return FileResponse(Path(DB_PATH), media_type="application/octet-stream")


# The built web app, when present, so one process serves an instance. The SQLite
# wasm needs cross-origin isolation, hence the two headers on every response.
WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"
if WEB_DIST.is_dir():
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.staticfiles import StaticFiles

    class _Isolation(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            response = await call_next(request)
            response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
            response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
            return response

    app.add_middleware(_Isolation)
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
