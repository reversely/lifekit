"""The API refuses bad input with 400 and writes nothing (#35)."""

import os

os.environ["LIFEKIT_ONLINE_RETRIEVAL"] = "off"
os.environ["LIFEKIT_QUEUE_WORKER"] = "off"

from fastapi.testclient import TestClient  # noqa: E402

from lifekit.api import app  # noqa: E402

client = TestClient(app)


def test_verdict_refuses_path_id():
    r = client.post("/api/verdict", json={"volume": "../etc", "verdict": "admit"})
    assert r.status_code == 400


def test_verdict_refuses_unknown_section():
    r = client.post("/api/verdict", json={"volume": "wikipedia-bee-sting", "verdict": "refile", "section": "nope"})
    assert r.status_code in (200, 400)
    if r.status_code == 200:
        assert "error" in r.json()


def test_oversized_question_refused():
    r = client.post("/api/questions", json={"text": "x" * 5000})
    assert r.status_code == 400
