# The prototype format

This document fixes the format the prototype reached on 2026-08-25: five screens, the
regions of each, the table each region reads, and the backend that fills those tables. The
Survival Medicine shelf is the placed example throughout. A new shelf is added by writing
one volume list; every screen then renders it without code changes.

## Summary

LifeKit's library is a set of documents (volumes) that the app downloads, cuts into pages
and passages, indexes for full-text search, describes with a generated cover, and tags with
its traits. Twelve binders (sections) sit over the library and collect volumes by a section
tag. The reader meets the library through five screens: the Library directory, the Recent
list, a Section page, Search, and the Digest. Every screen is a query over the same tables.

## Conventions

- "Region" names a fixed area of a screen. Each region lists the table and columns it reads.
- "Trait" names a tag on a volume: `section:`, `type:`, `publisher:`, `topic:`. Filters are
  traits; sorts are columns.
- Type tokens: ground `#09090b`, surface `#0f0f12`, border `#27272a`, text `#fafafa`,
  secondary `#a8a8b3`, muted `#8e8e99` (raised for WCAG AA contrast), accent white on black. The directory keeps the app's
  cream paper (`#F6F2E8`) and gold rule (`#C98D12`).
- Type scale: screen title 40 px, card title 22 px, body 16 px, subheader 15 px, labels
  13 to 14 px uppercase.

## 1. Screens

### 1.1 Library (directory)

| Region | Reads | Placed example |
|---|---|---|
| Title | none | "Library" |
| Digest strip | `volume` added since the last online session; `question` rows now answered | "13 volumes added." |
| Contents | `shelf` rows in order; count of `volume` per `section:` tag | "1 Survival Medicine, Lifesaving steps, injuries, bites and stings, wounds, 13 volumes"; "2 Shelter, none yet" |

Tapping a row opens the Section page. The directory replicates the app's contents page:
italic numeral, title with a gold rule, scope line, count.

### 1.2 Recent

| Region | Reads | Placed example |
|---|---|---|
| Title | none | "Recent" |
| Sort | a column: `retrieved` desc or asc, `title`, `page_count` | Latest, Oldest, A to Z, Pages |
| Filters | every `section:` tag (all twelve, empty ones muted), then `type:`, then `publisher:` tags with counts | Survival Medicine 13, Shelter 0, …; fact sheet 9, manual 3; NHS 5, NIH 3 |
| Day dividers | `retrieved` date, shown only under a date sort | "24 August 2026" |
| Cards | see 1.6 | |

### 1.3 Section

| Region | Reads | Placed example |
|---|---|---|
| Title | `shelf.order`, `shelf.title`, `shelf.scope_line` | "1. Survival Medicine", "Lifesaving steps, injuries, bites and stings, wounds" |
| Sort | as Recent | |
| Filters | `type:` and `publisher:` tags counted within this section | fact sheet 9, manual 3; NHS 5 |
| Cards | volumes with this `section:` tag, see 1.6 | |

### 1.4 Search

| Region | Reads | Placed example |
|---|---|---|
| Bar | the query | "signs of hypothermia" |
| Filters | as Recent (section, type, publisher) | |
| Volumes | `volume` whose `title` or `cover.text` matches | "Hypothermia, NHS England" with its cover and "Open volume" |
| In the pages | `passage_fts` hits joined to `page` and `volume`, ranked with the volume's role and the passage kind | "ATP 4-02.11, March 2026, page 103" with the passage and "Open page 103" |
| Empty state | none | "Nothing in the library answers this. Stored for when you are online." |

"Open page N" opens the volume at `page.anchor`.

### 1.5 Digest

| Region | Reads | Placed example |
|---|---|---|
| Added | `volume` rows since the last online session, each with `cover.digest_line` | "Heat exhaustion and heatstroke symptoms, cooling steps, and when to call for help, from NHS England." |
| Answered | `question` rows resolved since then, each with the answer, the quoted passage, and the page | "You asked: how do I remove a tick" with the ATP page 184 answer |

### 1.6 Card

The one card every list uses.

| Element | Reads |
|---|---|
| Thumbnail, 56 × 76, left of the header only | first page render for a PDF; a typographic tile (publisher, title) for an HTML page |
| Title | `volume.title` |
| Subheader | `volume.publisher`, `volume.edition` |
| Paragraph, full width | `cover.text`, first two sentences |
| Trait bubbles | `volume_tag` rows except `section:` |
| Foot | `volume.page_count` |

## 2. Backend

### 2.1 Pipeline

```
shelves/<shelf>/volumes.tsv        one row per volume: id, title, publisher, edition, url,
        │                          format, licence, licence sentence, carry, role, tags
        ▼
fetch.py        volumes/<id>/source.pdf|html, source.meta.json (sha256, retrieved, agent)
        ▼
pages.py        one row per PDF page or HTML heading section; OCR when a page has no text
        ▼
segment.py      verbatim passages with checked offsets and a kind
        ▼
build.py        library.sqlite: volume, shelf_volume, page, passage, passage_fts,
                volume_tag, provenance
        ▼
covers.py       cover.text and digest_line per volume, through the small model; hand edit
                in volumes/<id>/cover.md wins; check() enforces prompts.md
        ▼
tags.py         hand tag edits in volumes/<id>/tags.json, applied over rule tags on rebuild
        ▼
query.py        search with role and kind ranking and a tag filter; RAG tests
render.py       the five screens from the tables (prototype renderer)
```

### 2.2 Tables the screens read

| Table | Written by | Read by |
|---|---|---|
| shelf | build | Library, Section |
| volume | build (from volumes.tsv and source.meta.json) | every screen |
| volume_tag | build (rule), tags.py (hand) | filters, bubbles |
| page | pages via build | Search (open page), thumbnails |
| passage, passage_fts | segment via build | Search, answers, RAG tests |
| cover | covers.py | cards, Search volumes, Digest |
| question, digest | the API and the loop | Digest, Search empty state |
| provenance | build, covers | "why does it say this" |

### 2.3 Files on disk

```
packs/
  library.sqlite
  shelves/<shelf>/volumes.tsv     the curated list
  shelves/<shelf>/learned.tsv     what the loop pulled, same columns
  volumes/<id>/source.<ext>, source.meta.json, cover.md, tags.json
```

`packs/` is the working copy of the dataset repo and stays out of git. A pull is one
`volumes/<id>/` directory plus its rows; the queue moves it through `queued`,
`downloading`, `extracted`, `indexed`, `shelved`.

### 2.4 The API and the loop

`lifekit/api.py` serves the app (FastAPI locally; the same functions mount beside Gradio on
the Space): `GET /api/search`, `POST /api/answer`, `POST /api/questions`, `POST /api/sync`,
`GET /api/digest`, `GET /api/library.sqlite`. `lifekit/library/loop.py` works stored
questions: name the topic (model), search an open source class (Wikipedia first), pull the
page as a learned volume (cut, indexed, tagged, recorded in the shelf's `learned.tsv` so a
rebuild keeps it), re-ask with the question and topic words, write the digest.

The app holds questions asked offline in `localStorage` (`lifekit.questions`), sends them on
the Digest screen's Sync when `navigator.onLine` is true, and reads `/api/digest`.

### 2.5 Adding a shelf

1. Write `shelves/<shelf>/volumes.tsv` from the survey table for that tile.
2. `fetch`, `build`, `covers`. The directory row gains its count; Recent, Section, and
   Search render the new volumes.
3. Run `covers --check` and the RAG tests. Fix by hand edit where the model fails.

## 3. Rules that hold

- No authored rewrite of a source. Text on screen is a document's own words, a cover the
  model wrote from its contents, or an answer that quotes a passage.
- Filters are traits; sorts are columns. Neither is a static label.
- Every generated line names its volume and page.
- Hand edits (cover, tags) survive every rebuild.
- OCR plus full-text search; no embeddings.
