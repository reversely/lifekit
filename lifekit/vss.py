"""Video summarization: a clip is cut into ten-second chunks, the frames of each chunk go
to a vision model with the summarization prompt, and the chunk descriptions are joined into
one report by the text model.

The vision model is any OpenAI-compatible chat server that accepts images, set by
LIFEKIT_VISION_URL and LIFEKIT_VISION_MODEL (default: Cosmos Reason2 8B served by vLLM on the box
at port 8010, scripts/cosmos_up.sh; any server that takes images on the chat route works). Clips live in packs/vss-demo and every
clip is named by a manifest row.
"""

import base64
import json
import os
import re
import subprocess
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

import httpx

from lifekit.library import provider
from lifekit.packs import LOCAL_PACKS

CLIPS = LOCAL_PACKS / "vss-demo"
CHUNK_SECONDS = 10
FRAMES_PER_CHUNK = 6
FRAME_WIDTH = 640
_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}\.mp4$")

Emit = Callable[[dict], None]


def vision_endpoint() -> tuple[str, str]:
    return (
        os.environ.get("LIFEKIT_VISION_URL", "http://127.0.0.1:8010/v1").rstrip("/"),
        os.environ.get("LIFEKIT_VISION_MODEL", "cosmos-reason2-8b"),
    )


def valid_clip(name: str) -> bool:
    """A clip name is lowercase letters, digits, hyphens, and one .mp4 suffix, so it can never
    name a path outside packs/vss-demo."""
    return bool(_NAME.match(name)) and ".." not in name and (CLIPS / name).is_file()


def clips() -> list[dict]:
    """Every clip in packs/vss-demo with its duration in seconds."""
    out = []
    for path in sorted(CLIPS.glob("*.mp4")):
        if valid_clip(path.name):
            out.append({"name": path.name, "seconds": duration(path)})
    return out


def duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True, timeout=60,
    )
    return float(result.stdout.strip() or 0)


def frames(path: Path, start: float, seconds: float, folder: Path) -> list[Path]:
    """FRAMES_PER_CHUNK JPEG frames spread evenly over the chunk, FRAME_WIDTH wide."""
    rate = FRAMES_PER_CHUNK / seconds
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.3f}", "-t", f"{seconds:.3f}", "-i", str(path),
         "-vf", f"fps={rate:.4f},scale={FRAME_WIDTH}:-2", "-frames:v", str(FRAMES_PER_CHUNK), "-q:v", "4",
         str(folder / "frame-%02d.jpg")],
        check=True, timeout=120,
    )
    return sorted(folder.glob("frame-*.jpg"))


def describe_chunk(prompt: str, tracking: str, start: float, end: float, images: list[Path]) -> str:
    """One vision call: the summarization prompt, the tracking target, and the chunk's frames."""
    base_url, model = vision_endpoint()
    content: list[dict] = [{"type": "text", "text": (
        f"{prompt}\n\nThese {len(images)} frames are spread evenly over seconds {start:.0f} to {end:.0f} of the clip. "
        f"Track: {tracking}. Write one line per event as '<start>-<end>: <what happens>', with times in seconds within {start:.0f} to {end:.0f}. "
        "One event is one continuous action or condition and spans all the seconds it lasts; never split one action into one-second lines. "
        "Describe only what the frames show. If nothing moves, describe the scene and its conditions in one line."
    )}]
    for image in images:
        data = base64.b64encode(image.read_bytes()).decode()
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{data}"}})
    body = {"model": model, "messages": [{"role": "user", "content": content}], "max_tokens": 400, "temperature": 0.2}
    if os.environ.get("LIFEKIT_MODEL_THINKING", "off").lower() != "on":
        body["reasoning_effort"] = "none"
    response = httpx.post(f"{base_url}/chat/completions", json=body, timeout=600)
    response.raise_for_status()
    text = response.json()["choices"][0]["message"]["content"].strip()
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


_EVENT = re.compile(r"^\s*-?\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*[:\s]\s*(.+)$")


def seconds(text: str) -> str:
    """A time stamp as the model wrote it, without trailing zeros: 50.000 becomes 50."""
    return f"{float(text):g}"


def stamp(seconds: float) -> str:
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


def report(prompt: str, notes: list[tuple[float, float, str]]) -> str:
    """The report: a title line and a summary paragraph from the text model, then, built in
    code so no event is invented or dropped, one heading per time range and one line per
    event with its start and end time stamps first."""
    joined = "\n\n".join(f"Seconds {s:.0f} to {e:.0f}:\n{t}" for s, e, t in notes)
    system = (
        "You summarize time-stamped observations of one video clip. Output exactly two lines: "
        "line one is a title of at most eight words; line two is one paragraph of at most two sentences "
        "stating what was observed and when. Use only the observations given."
    )
    head = provider.ask(system, f"The observation task was: {prompt}\n\nObservations:\n{joined}", max_tokens=200)
    lines = [l.strip().strip("<>#* ") for l in head.splitlines() if l.strip()][:2]
    out = lines + [""]
    for s, e, text in notes:
        out.append(f"## {stamp(s)} to {stamp(e)}")
        for raw in text.splitlines():
            raw = raw.strip()
            if not raw:
                continue
            match = _EVENT.match(raw)
            if match:
                out.append(f"- {seconds(match.group(1))}-{seconds(match.group(2))}: {match.group(3).strip()}")
            else:
                out.append(f"- {s:.0f}-{e:.0f}: {raw.lstrip('-* ')}")
        out.append("")
    return "\n".join(out).strip()


def run(clip: str, prompt: str, tracking: str, emit: Emit) -> str:
    """The whole pass, one JSON record per step through emit; returns the report text."""
    path = CLIPS / clip
    total = duration(path)
    started = time.monotonic()
    emit({"step": "start", "clip": clip, "seconds": total, "model": vision_endpoint()[1], "elapsed": 0})
    notes: list[tuple[float, float, str]] = []
    start = 0.0
    with tempfile.TemporaryDirectory(prefix="lifekit-vss-") as temp:
        while start < total - 0.5:
            end = min(start + CHUNK_SECONDS, total)
            folder = Path(temp) / f"chunk-{int(start):04d}"
            folder.mkdir()
            images = frames(path, start, end - start, folder)
            emit({"step": "frames", "start": start, "end": end, "count": len(images), "elapsed": round(time.monotonic() - started, 1)})
            text = describe_chunk(prompt, tracking, start, end, images)
            if not text:
                raise RuntimeError(f"The vision model returned no text for seconds {start:.0f} to {end:.0f}.")
            notes.append((start, end, text))
            emit({"step": "chunk", "start": start, "end": end, "text": text, "elapsed": round(time.monotonic() - started, 1)})
            start = end
    emit({"step": "report", "elapsed": round(time.monotonic() - started, 1)})
    text = report(prompt, notes)
    emit({"step": "done", "text": text, "elapsed": round(time.monotonic() - started, 1)})
    return text


def stream(clip: str, prompt: str, tracking: str):
    """Generator of NDJSON lines for the API route."""
    import queue
    import threading

    events: "queue.Queue[dict | None]" = queue.Queue()

    def work():
        try:
            run(clip, prompt, tracking, events.put)
        except Exception as error:  # noqa: BLE001
            events.put({"step": "failed", "text": str(error)[:400]})
        finally:
            events.put(None)

    threading.Thread(target=work, daemon=True).start()
    while True:
        record = events.get()
        if record is None:
            break
        yield json.dumps(record) + "\n"
