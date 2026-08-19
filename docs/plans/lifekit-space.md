# LifeKit on Hugging Face: plan

LifeKit ships in the flux repo as a React Native app backed by a Python server, an inference box,
and a content pipeline. This plan ports a subset of it to a public Gradio Space at
`reversely/lifekit`, backed by a dataset repo at `reversely/lifekit-packs`. The flux repo keeps
shipping unchanged; this repo holds everything new.

## Conventions

- "Walk" names the interview-driven session shape from the flux PRD 1.6: a short clip, questions
  with tappable options, then a result that gives the implication first, the quoted source line
  second, and a deep link into the source third.
- "Pack" names the versioned content set the app answers from: documents, figures, structured data,
  each row carrying its source URL and license.
- Phases number the delivery order. A phase ships as a working public Space before the next starts.

## Repos

- `reversely/lifekit`: the Gradio Space. Code, tests, this plan. Starts private.
- `reversely/lifekit-packs`: the dataset repo. One directory per surface (`walks/`, `reference/`,
  `encyclopedia/`, `clips/`), a root `manifest.tsv` with columns
  `path, surface, source_url, author, license, retrieved, note`, and a `CREDITS.md` generated from
  it. The Space downloads this repo at startup and renders its credits tab from the manifest, so an
  asset with an empty license cell fails a check before it ships uncredited.
- Local development: `~/Repos/lifekit` holds both, with `packs/` as the dataset repo's working copy.

## Phase 1: no GPU

Surfaces, each a tab in one Gradio Blocks app:

- **Walks**: the weather and celestial sessions transcribed from
  `flux/app/src/data/vss.ts` into Python data plus a gap-tracking engine. The engine asks a
  question only while its answer could still change the outcome: findings hold priority order, and
  the interview ends early when the leading satisfiable finding has every listed answer and no
  higher-priority finding remains satisfiable. The fallback finding answers when nothing matches.
  With no GPU, the clip step waits for phase 2; a session that starts with zero settled
  observations already works because the engine treats an uninformative clip the same as no clip.
- **Reference**: the FM 21-76 PDF rendered page by page with a chapter jump table
  (23 chapters, first-page numbers carried over from `flux/app/src/data/reference.ts`).
- **Encyclopedia**: the 12 tiles and 3 authored guides from `guide-corpus.json`, each tile linking
  to its chapter in the reference tab.
- **Quote search**: retrieval over per-page FM 21-76 text. A query returns the matching passages
  verbatim with page links. Generated answers wait for phase 2's model, and the tab says so.
- **Credits**: rendered from the packs manifest.

Copy follows the flux field-guide rule: fragments, expert terms from the sources, a plain gloss at
first use.

## Phase 2: ZeroGPU

`nvidia/Cosmos-Reason2-8B` (gating: auto; accepted by the reversely account, token as a Space
secret) loads once at startup. `@spaces.GPU` functions keep short duration budgets, and ffmpeg
frame extraction runs CPU-side so GPU seconds go only to inference. The one model serves:

- **Sky read**: frames from an uploaded clip pre-settle walk observations before the interview.
- **Trail summarize and ask**: a clip-upload port of the `VideoHandoff` protocol from
  `flux/server/src/flux_server/vss.py`, reusing its prompts.
- **Chat**: the quote-search tab gains generated answers that quote retrieved passages.

Cosmos-Reason2 fine-tunes Qwen3-VL-8B, so it handles text-only chat as well as frames; no separate
chat model. If measured latency on ZeroGPU quotas disappoints, `Cosmos-Reason2-2B` replaces it, at
the cost of retraining any 8B adapter.

## Phase 3: coach

The coach walks (knots, fire, tourniquet) from `flux/server/src/flux_server/coach.py` need
reconfiguration before a public Space carries them, plus new procedures from Ego-Exo4D keysteps.

- Ego-Exo4D downloads to the flux box with the `ego4d` CLI using the `ego_id`/`ego_secret`
  credentials. Raw clips stay on the box.
- The T3 tourniquet adapter uploads to a private model repo the Space reads by token. Publication
  gets decided per adapter once each exists.
- An Ego-Exo4D coach adapter trains on the box with the `flux/docs/training/t3_train.py` recipe
  over keystep annotations.

### Ego-Exo4D license reading

From the license agreement's grant clause: §2 permits using the database to research, develop,
train, and evaluate models, for academic, commercial, or noncommercial development, and places no
restriction on distributing resulting weights, which fall outside the agreement's "Database"
definition. §3 permits creating and distributing annotations, so keystep-derived guide text can
ship publicly in lifekit-packs. §1 limits redistribution of the images and videos themselves to
research publications and their websites, so no clip enters a public repo.

## Excluded surfaces

Every edibility surface (mushrooms, berries, their trait tables and species images) stays out: a
public tool does not tell a stranger something is safe to eat. The map (pmtiles too large for a
Space), the conditions strip (no device sensors in a browser tab), and the library queue (a
box-side worker) stay in the app.

## Dataset hygiene track (parallel, in flux)

A check of all 69 URLs in `flux/box/data/universal.tsv` on 2026-08-18 returned 68 live and one
500 (the WHO prehospital pocket reference on the IRIS server). Repair scope: that row, the three
`pending` rows (WMM 2025, the unabridged FM family, WHO snakebite), a license column for
`universal.tsv` and `box/corpora/manifest.tsv`, and a scheduled link check. Ten `cloud-*.jpg` and
several fire figures in `flux/app/assets/guides/` lack traced per-image attribution; they join
lifekit-packs only after the manifest can cite them.

## Validation

- Pytest over the walk engine: every finding reachable, no question asked once the outcome settles,
  fallback fires when nothing matches.
- A manifest check: every pack file has a row, every row has a license.
- The link checker run against the packs manifest.
- Phase 3 coach walks run against Ego-Exo4D clips on the box before each release.
