"""Locate the content pack.

Local development reads ./packs (the lifekit-packs working copy). The Space
downloads the dataset repo at startup. Either way the caller gets one
directory whose layout the manifest describes.
"""

import csv
from functools import lru_cache
from pathlib import Path

PACKS_REPO = "reversely/lifekit-packs"
LOCAL_PACKS = Path(__file__).resolve().parent.parent / "packs"


@lru_cache(maxsize=1)
def packs_dir() -> Path:
    if LOCAL_PACKS.is_dir():
        return LOCAL_PACKS
    from huggingface_hub import snapshot_download

    return Path(snapshot_download(PACKS_REPO, repo_type="dataset"))


def manifest_rows() -> list[dict[str, str]]:
    path = packs_dir() / "manifest.tsv"
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))
