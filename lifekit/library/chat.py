"""The chat: a conversation with the library's voice, grounded in its pages.

Carried over from the flux app's chat (server nemotron.py, app chat.tsx). Each turn
retrieves the top passages for the question, the model answers in the guide's
voice and names the document and page it quotes, and a question the pages do
not cover is stored for the online retrieval with the model's own gap record, so the reply
can say what was noted for the library.
"""

import json
import re

from . import provider
from .online_retrieval import gap_record, store_question
from .query import search

PASSAGE_LIMIT = 5
PASSAGE_CHARS = 800

CHAT_PROMPT = (
    "Ground every statement in the passages this prompt gives you. State uncertainty "
    "plainly instead of guessing. You inform; the reader decides. Write plain prose: no "
    "markdown, no asterisks, no headings, no bullet syntax.\n\n"
    "You are the voice of this survival library: a calm, capable companion, not a lookup "
    "table. Survival answers are concrete, imperative, and brief, with the steps that "
    "matter in order and nothing decorative.\n\n"
    "Rules:\n"
    "- Not every message is a survival question. A greeting, thanks, small talk, or a "
    "question about you gets a short, friendly reply with no source line and no citation "
    "of any kind.\n"
    "- Cite nothing when no passages are attached to the message.\n"
    "- When passages cover the question, open with the practical guidance, quote the "
    "sentence you rely on in double quotes, and name the document and page exactly as "
    "they appear in the square brackets before that passage. Never name a document that "
    "is not in the brackets, and never invent a page.\n"
    "- When no passages are attached, answer from your own knowledge in the same voice, "
    "briefly, and never claim a source. The screen tells the reader the topic was noted "
    "for the library, so you do not. Medical actions are the exception: they come only "
    "from the reviewed documents, so an unlisted medical procedure gets one sentence "
    "saying the library has no reviewed procedure for it, and no improvised steps.\n"
    "- Identification of plants, fungi, and animals is never certain from a description. "
    "Treat uncertain specimens as hazardous by default.\n"
    "- You are offline support for a wilderness situation: no links, no 'consult a "
    "professional' filler when no professional is reachable, though say when something "
    "needs evacuation or rescue."
)

COVERS_PROMPT = (
    "You judge whether library passages answer a question. Reply yes only when at least one "
    "passage gives information about the subject of the question itself. Passages that merely "
    "share a word with the question, or are about something else, mean no. Reply with one "
    "word: yes or no."
)
_VERDICT = re.compile(r"^\s*(NOT ANSWERED|ANSWERED)[:.\s-]*", re.I)
_MARKDOWN = [(re.compile(r"^#{1,6}\s+", re.M), ""), (re.compile(r"\*{1,3}([^*]+)\*{1,3}"), r"\1"),
             (re.compile(r"`+([^`]*)`+"), r"\1"), (re.compile(r"^\s*[-*]\s+", re.M), "")]


def _clean(text: str) -> str:
    for pattern, repl in _MARKDOWN:
        text = pattern.sub(repl, text)
    return text.strip()


def _passages(db, question: str) -> tuple[list[dict], str]:
    hits = search(db, question, limit=PASSAGE_LIMIT)
    if not hits:
        return [], ""
    lines = [f"- [{h['title']}, {h['edition']}, page {h['number']}] {h['text'][:PASSAGE_CHARS]}" for h in hits]
    sources = [{"title": h["title"], "edition": h["edition"], "volume": h["volume"], "page": h["number"],
                "passage": h["passage"], "snippet": h["text"][:200]} for h in hits]
    return sources, "\n\nPassages from the library matching the question (quote these and name their document and page):\n" + "\n".join(lines)


def answer(db, question: str, history: list[dict] | None = None, profile: dict | None = None) -> dict:
    """One turn. history holds earlier turns as {role: user|assistant, text}."""
    asking = _looks_like_question(question)
    # A short follow-up ("and if that does not stop it?") carries its subject in the
    # previous question, so retrieval, the coverage judgment, and the gap record read both.
    focus = _with_context(question, history or [])
    sources, block = _passages(db, focus) if asking else ([], "")
    # A separate tiny judgment decides coverage; the answer prompt then sees passages
    # only when they bear on the question, so an off-topic passage cannot be quoted.
    covered = bool(sources) and _covers(focus, block)
    if not covered:
        sources, block = [], ""
    messages = [{"role": "system", "content": CHAT_PROMPT}]
    for turn in (history or [])[-8:]:
        role = "assistant" if turn.get("role") == "assistant" else "user"
        messages.append({"role": role, "content": str(turn.get("text", ""))[:2000]})
    messages.append({"role": "user", "content": question + block})
    raw = provider.chat(messages, max_tokens=600, kind="answer")
    text = _clean(_VERDICT.sub("", raw, count=1))
    if not covered:
        # no source stands behind the reply, so no bracketed citation may remain
        text = re.sub(r"\s*\[[^\]]{3,120}\]", "", text).strip()
    queued = None
    if asking and not covered:
        topic, wanted = gap_record(lambda s, u: provider.ask(s, u), focus) if provider.online_retrieval_enabled() else (None, None)
        if topic and topic != "none":
            qid = store_question(db, focus, profile, topic=topic, wanted=wanted)
            queued = {"id": qid, "topic": topic, "wanted": wanted}
    return {"text": text, "sources": sources if covered else [], "queued": queued, "model": provider.endpoint("answer").name}


def _covers(question: str, block: str) -> bool:
    try:
        said = provider.ask(COVERS_PROMPT, f"Question: {question}{block}", max_tokens=4).strip().lower()
    except Exception:  # noqa: BLE001
        return False
    return said.startswith("yes")


_FOLLOW_UP = re.compile(r"^\s*(and|but|what if|if|then|or|also|how about|what about|does|is|it|that|this)\b", re.I)


def _with_context(question: str, history: list[dict]) -> str:
    words = re.findall(r"[a-z]+", question.lower())
    short = len(words) < 6 or _FOLLOW_UP.match(question) is not None
    last_user = next((t.get("text", "") for t in reversed(history) if t.get("role") == "user"), "")
    return f"{last_user} {question}".strip() if short and last_user else question


def _looks_like_question(text: str) -> bool:
    words = re.findall(r"[a-z]+", text.lower())
    return len(words) >= 3 and not any(w in ("hi", "hello", "thanks", "thank", "hey") for w in words[:2])
