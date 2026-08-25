"""Tags on volumes: many per volume, editable, surviving rebuilds.

A tag is "namespace:value". Sections use the namespace "section" and match
the twelve shelves; anything else is free. Three sources: a rule (the volume
list or a pull rule), a model, or a hand edit. Hand edits live in
packs/volumes/<id>/tags.json and win over the other two on rebuild.

    uv run python -m lifekit.library.tags add  <volume_id> <tag>
    uv run python -m lifekit.library.tags drop <volume_id> <tag>
    uv run python -m lifekit.library.tags show <volume_id>
"""

import json
import sys
from datetime import datetime, timezone

from .fetch import VOLUMES_DIR


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def hand_file(volume_id: str):
    return VOLUMES_DIR / volume_id / "tags.json"


def load_hand(volume_id: str) -> dict:
    path = hand_file(volume_id)
    return json.loads(path.read_text()) if path.exists() else {"add": [], "drop": []}


def apply_tags(db, volume_id: str, rule_tags: list[str]) -> None:
    """Write a volume's tags: rule tags, then hand adds, minus hand drops."""
    hand = load_hand(volume_id)
    db.execute("DELETE FROM volume_tag WHERE volume_id = ?", (volume_id,))
    for tag in rule_tags:
        if tag not in hand["drop"]:
            db.execute("INSERT OR IGNORE INTO volume_tag VALUES (?,?,?,?)", (volume_id, tag, "rule", _now()))
    for tag in hand["add"]:
        db.execute("INSERT OR REPLACE INTO volume_tag VALUES (?,?,?,?)", (volume_id, tag, "hand", _now()))


def tags_of(db, volume_id: str) -> list[tuple[str, str]]:
    return db.execute(
        "SELECT tag, source FROM volume_tag WHERE volume_id = ? ORDER BY tag", (volume_id,)
    ).fetchall()


def edit(volume_id: str, tag: str, add: bool) -> None:
    hand = load_hand(volume_id)
    for key in ("add", "drop"):
        if tag in hand[key]:
            hand[key].remove(tag)
    hand["add" if add else "drop"].append(tag)
    hand_file(volume_id).write_text(json.dumps(hand, indent=1))
    from .build import DB_PATH, connect

    db = connect(DB_PATH)
    if add:
        db.execute("INSERT OR REPLACE INTO volume_tag VALUES (?,?,?,?)", (volume_id, tag, "hand", _now()))
    else:
        db.execute("DELETE FROM volume_tag WHERE volume_id = ? AND tag = ?", (volume_id, tag))
    db.commit()


if __name__ == "__main__":
    verb, volume_id = sys.argv[1], sys.argv[2]
    if verb == "show":
        from .build import DB_PATH, connect

        for tag, source in tags_of(connect(DB_PATH), volume_id):
            print(f"{tag}  ({source})")
    else:
        edit(volume_id, sys.argv[3], add=(verb == "add"))
        print("ok")
