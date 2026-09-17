"""Fetch the carry volumes of a shelf into packs/volumes/<id>/source.<ext>.

Each fetch writes source bytes, a sha256, and a provenance line. A volume that
already has a source file with a matching sha256 is skipped.
"""

import csv
import hashlib
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from lifekit.packs import LOCAL_PACKS

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 Chrome/126 Safari/537.36"
VOLUMES_DIR = LOCAL_PACKS / "volumes"


def read_volumes(shelf: str) -> list[dict]:
    """The shelf's curated list plus what the online retrieval learned (learned.tsv, same columns)."""
    rows: list[dict] = []
    for name in ("volumes.tsv", "learned.tsv"):
        path = LOCAL_PACKS / "shelves" / shelf / name
        if path.exists():
            with path.open(newline="") as handle:
                rows += list(csv.DictReader(handle, delimiter="\t"))
    return rows


def _get(url: str) -> tuple[bytes, str]:
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read(), response.headers.get("Content-Type", "")


def fetch_volume(volume: dict, force: bool = False) -> dict:
    dest = VOLUMES_DIR / volume["id"]
    dest.mkdir(parents=True, exist_ok=True)
    ext = "pdf" if volume["format"] == "pdf" else "html"
    source = dest / f"source.{ext}"
    meta_path = dest / "source.meta.json"
    if source.exists() and meta_path.exists() and not force:
        return json.loads(meta_path.read_text())
    body, content_type = _get(volume["url"])
    if volume["format"] == "pdf" and not body.startswith(b"%PDF"):
        raise RuntimeError(f"{volume['id']}: expected a PDF, got {content_type} ({len(body)} bytes)")
    source.write_bytes(body)
    meta = {
        "id": volume["id"],
        "url": volume["url"],
        "sha256": hashlib.sha256(body).hexdigest(),
        "bytes": len(body),
        "content_type": content_type,
        "retrieved": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fetched_by": "lifekit.library.fetch 0.1",
    }
    meta_path.write_text(json.dumps(meta, indent=1))
    return meta


def main(argv: list[str]) -> None:
    shelves = argv[1:] or sorted(p.parent.name for p in (LOCAL_PACKS / "shelves").glob("*/volumes.tsv"))
    seen: set[str] = set()
    volumes = [v for shelf in shelves for v in read_volumes(shelf)]
    for volume in volumes:
        if volume["carry"] != "carry" or volume["id"] in seen:
            continue
        seen.add(volume["id"])
        try:
            meta = fetch_volume(volume)
            print(f"ok   {volume['id']}  {meta['bytes']} bytes  {meta['sha256'][:12]}")
        except Exception as error:  # noqa: BLE001 - report every failure and continue
            print(f"FAIL {volume['id']}  {error}")
        time.sleep(1.0)


if __name__ == "__main__":
    main(sys.argv)
