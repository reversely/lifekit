"""The owner's verdict on a fetch pass addition: admit, refile, or reject.

docs/content/deployments-and-approval.md 3.3. The verdict lives in
packs/volumes/<id>/verdict.json so a rebuild keeps it, and a refile also writes
the hand tag file and one filing example the section prompt reads.
"""

import csv
import json
from datetime import datetime, timezone

from lifekit.packs import LOCAL_PACKS

from .fetch import VOLUMES_DIR

EXAMPLES = LOCAL_PACKS / "filing-examples.tsv"
from . import sections


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_verdict(volume_id: str) -> dict:
    path = VOLUMES_DIR / volume_id / "verdict.json"
    return json.loads(path.read_text()) if path.exists() else {}


def rejected_ids() -> set[str]:
    """Volumes the owner rejected; the fetch pass never pulls them again."""
    out = set()
    if not VOLUMES_DIR.is_dir():
        return out
    for path in VOLUMES_DIR.glob("*/verdict.json"):
        if json.loads(path.read_text()).get("admission") == "rejected":
            out.add(path.parent.name)
    return out


def filing_examples(limit: int = 12) -> list[tuple[str, str]]:
    """(question, section) pairs from the owner's refiles, newest first."""
    if not EXAMPLES.exists():
        return []
    with EXAMPLES.open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    return [(r["question"], r["section"]) for r in rows[-limit:]][::-1]


def apply(db, volume_id: str, verdict: str, section: str | None = None, by: str = "owner") -> dict:
    """Apply one verdict and return the volume's new state."""
    if verdict not in ("admit", "refile", "reject"):
        raise ValueError(f"unknown verdict {verdict!r}")
    if verdict == "refile" and section not in sections.ids():
        raise ValueError(f"refile needs a section, got {section!r}")
    row = db.execute("SELECT id FROM volume WHERE id = ?", (volume_id,)).fetchone()
    if row is None:
        raise KeyError(volume_id)
    at = _now()
    admission = "rejected" if verdict == "reject" else "admitted"
    if verdict == "refile":
        from .tags import edit

        old = [t for (t,) in db.execute(
            "SELECT tag FROM volume_tag WHERE volume_id = ? AND tag LIKE 'section:%'", (volume_id,))]
        for tag in old:
            if tag != f"section:{section}":
                edit(volume_id, tag, add=False)
        edit(volume_id, f"section:{section}", add=True)
        db.execute("DELETE FROM shelf_volume WHERE volume_id = ?", (volume_id,))
        order = db.execute("SELECT coalesce(max(\"order\"), 0) + 1 FROM shelf_volume WHERE shelf_id = ?", (section,)).fetchone()[0]
        db.execute("INSERT INTO shelf_volume VALUES (?,?,?,?)", (section, volume_id, order, "reference"))
        question = db.execute(
            "SELECT q.text FROM question q JOIN provenance p ON p.entity_id = ? AND p.activity = 'pull'"
            " WHERE p.derived_from LIKE '%' || q.id || '%' LIMIT 1", (volume_id,)).fetchone()
        if question:
            _record_example(question[0], section)
    db.execute("UPDATE volume SET admission = ?, admitted_at = ?, admitted_by = ? WHERE id = ?",
               (admission, at, by, volume_id))
    db.execute("INSERT INTO provenance VALUES (?,?,?,?,?)",
               (volume_id, verdict, by, json.dumps([section] if section else []), at))
    db.commit()
    record = {"admission": admission, "verdict": verdict, "section": section, "at": at, "by": by}
    (VOLUMES_DIR / volume_id).mkdir(parents=True, exist_ok=True)
    (VOLUMES_DIR / volume_id / "verdict.json").write_text(json.dumps(record, indent=1))
    return record


def _record_example(question: str, section: str) -> None:
    new = not EXAMPLES.exists()
    with EXAMPLES.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["question", "section", "at"], delimiter="\t", lineterminator="\n")
        if new:
            writer.writeheader()
        writer.writerow({"question": question, "section": section, "at": _now()})
