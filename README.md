---
title: LifeKit
emoji: 🧭
colorFrom: green
colorTo: gray
license: mit
---

# LifeKit

A library of open survival documents that the app downloads, cuts into pages and passages,
indexes for full-text search, describes with a generated cover, and files into twelve
binders. Search quotes the page it found. A question the library cannot answer is stored,
worked when the reader is back online, and answered in a digest with the quoted passage
and its page. The pack ships in the
[lifekit-packs](https://huggingface.co/datasets/reversely/lifekit-packs) dataset, and every
file carries its source and licence.

Ported from the [flux] LifeKit app.

## Run an instance on a box

One command brings up an instance next to a local model endpoint and serves the app on
port 8008 (`docs/content/deployments-and-approval.md`):

```
git clone https://github.com/reversely/lifekit && cd lifekit
ollama pull nemotron-3-nano
bash scripts/box_up.sh
```

`LIFEKIT_MODEL_SMALL` and `LIFEKIT_MODEL_ANSWER` take `openai:<base_url>:<model>` for an
OpenAI-compatible server or `hf:<model>` for Hugging Face inference. `LIFEKIT_FETCH=off`
keeps stored questions from being worked, as on the public Space.

## Develop

```
uv sync --all-groups
uv run python -m lifekit.library.fetch <shelf>     # download a shelf's volumes
uv run python -m lifekit.library.build             # packs/library.sqlite
uv run uvicorn lifekit.api:app --port 8008         # the API, plus web/dist when built
cd web && npm install && npm run dev               # the Svelte app with live reload
```

`packs/` holds the working copy of the dataset repo and stays out of this repo's git.
