---
title: LifeKit
emoji: 🧭
colorFrom: green
colorTo: gray
sdk: gradio
sdk_version: 6.24.0
app_file: app.py
pinned: false
license: mit
---

# LifeKit

Field answers with the source line behind them. A walk asks short questions with tappable
answers, then gives the implication first, the quoted source second, and a page link third.
The pack (FM 21-76, NOAA normals, guide figures) ships in the
[lifekit-packs](https://huggingface.co/datasets/reversely/lifekit-packs) dataset, and every
asset carries its source and license in the manifest.

Ported from the [flux] LifeKit app. Phase 1 runs without a GPU; phase 2 adds
Cosmos-Reason2-8B on ZeroGPU for clip reading, trail summarize and ask, and generated
answers that quote retrieved passages.

## Develop

```
uv sync --all-groups
uv run pytest
uv run python app.py
```

`packs/` holds the working copy of the dataset repo and stays out of this repo's git.
