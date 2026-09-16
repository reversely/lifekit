"""The twelve sections, read from packs/sections.tsv.

Columns: id, order, title, scope (the line under the title), gloss (what the
section holds, for the filing prompt), icon (a Feather icon name). Every list
of sections in the code reads this file; nothing names a section elsewhere.
"""

import csv
from functools import lru_cache

from lifekit.packs import LOCAL_PACKS

PATH = LOCAL_PACKS / "sections.tsv"


@lru_cache(maxsize=1)
def rows() -> list[dict]:
    with PATH.open(newline="") as handle:
        out = [dict(r) for r in csv.DictReader(handle, delimiter="\t")]
    for r in out:
        r["order"] = int(r["order"])
    return sorted(out, key=lambda r: r["order"])


def ids() -> list[str]:
    return [r["id"] for r in rows()]


def by_id(section_id: str) -> dict | None:
    return next((r for r in rows() if r["id"] == section_id), None)


def filing_list() -> str:
    """The sections and their glosses, for the filing prompt."""
    return "; ".join(f"{r['id']} ({r['gloss']})" for r in rows())
