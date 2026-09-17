# Deployments and the curation of library additions

This document states where LifeKit runs, who curates what the online retrieval adds to the
library, and how the public demo shows that online retrieval without running it. It fixes the decisions
the repo reader made on 2026-09-12 and gives the tables and screens that follow from them.
It supersedes the page audit in `library-schema.md` (the `page.audit` columns and section 6)
and the three-part section review recorded on 2026-08-23.

## Summary

LifeKit runs as one codebase on two kinds of host. An instance on a GPU box serves one
household: it downloads documents, answers questions from them, stores questions it cannot
answer, and, when a source turns up, adds the document to the library and answers. The person
running the box adds each download to the library or removes it. The public Space on Hugging Face runs the same web app over
a fixed database and plays a recorded online retrieval so a visitor can see each pathway.

## Words

Every word in this document means what it says. A metaphor is a violation. A label with no content is a violation.

## Conventions

| Term | Names |
|---|---|
| instance | One running LifeKit: a database, an API, a web app, and a model endpoint. |
| box | A GPU host that runs a real instance for its reader. The first two are the Acer Veriton GN100 and a DGX Spark; both carry the GB10 and 121 GB of unified memory. |
| Space | The Hugging Face Space `reversely/lifekit`, a demo instance with no live online retrieval. |
| reader | The person who runs a box and curates its downloads. |
| provider | The setting that names the model endpoint an instance calls. |
| gap record | What the model writes when it cannot answer: the question, the topic, and the kind of document that would answer it. |
| new download | A document the online retrieval fetched, cut, and indexed for a stored question, not yet added to the library or removed. |
| download panel | The region of a volume page that shows a new download with its two actions. |
| curation | Adding a new download to the library, in a section, or removing it. |

## 1. Instances

### 1.1 A box

A clone of this repository plus a model endpoint makes an instance. Setting up a box takes
these steps, each a command in the README:

1. Install the Python environment and the web build.
2. Start the model endpoint. The standing choice for every prompt on the box names the
   Nemotron Nano 9B v2 FP8 NIM, which flux already runs on the GN100 on port 30081. The
   provider setting carries two endpoint names, one for short completions (topic, section,
   cover, digest line) and one for answers, so answers can move to a larger model later
   without a code change. Both point at Nano until measurement says otherwise.
3. Fetch the shelf volume lists and build `library.sqlite`. A rebuild keeps covers,
   questions, digests, and learned volumes.
4. Serve the API and the built web app on the local network.

Nothing on a box uploads. The library, the questions, and the profile stay on the host.

### 1.2 The Space

The Space serves the built web app and the API from one Docker image over a database that
ships in the image. The online retrieval does not run: a public Space has no reader to curate additions
and no per-visitor storage, so live pulls would show every visitor the admissions of every
other visitor. The demo route (section 4) plays a recorded pass instead. The provider
setting on the Space names Hugging Face inference with Llama 3.1 8B Instruct for the live
answer path, the model the covers were written with.

### 1.3 The provider setting

| Variable | Box | Space |
|---|---|---|
| `LIFEKIT_MODEL_SMALL` | `openai:http://localhost:30081/v1:nvidia/nemotron-nano-9b-v2` | `hf:meta-llama/Llama-3.1-8B-Instruct` |
| `LIFEKIT_MODEL_ANSWER` | same as small | same as small |
| `LIFEKIT_ONLINE_RETRIEVAL` | `on` | `off` |

The API reads these at start. `openai:` names an OpenAI-compatible endpoint and a model id;
`hf:` names a Hugging Face inference model. The API's model call already reaches the online retrieval as
an injected function, so the setting changes one constructor.

## 2. The gap record

When the answer prompt returns NOT ANSWERED, the model writes a gap record in the same
reply, after the ANSWERED or NOT ANSWERED word: the topic in one to four words and the kind of document that
would answer the question, in one sentence. The API stores both on the question row. The
record replaces the separate topic prompt the online retrieval runs today, so the online retrieval starts from what
the model said was missing at the moment it failed.

| Column on `question` | Holds |
|---|---|
| `topic` | The noun phrase the model filed the question under. |
| `wanted` | One sentence naming the kind of document that would answer it. |

## 3. New downloads and curation

### 3.1 The staged state

The online retrieval fetches, cuts, indexes, covers, and files a new download exactly as it does now, and
marks the volume `staged`. A staged volume appears in search, in its section, and in Recent
with the marker "New download" on its card and on its page. The re-ask runs against it, so
the panel can show the answer the addition gives.

| Column on `volume` | Values |
|---|---|
| `admission` | `stock` for a volume from a shelf list; `staged` for a online retrieval addition not yet added or removed; `admitted`; `rejected`. |
| `admitted_at`, `admitted_by` | The date of the add or remove, and who did it. |

Search excludes `rejected` volumes. Everything else ranks as today.

### 3.2 The download panel

One panel per new download, on its volume page, reached from the digest and from the marker on the card:

| Region | Reads |
|---|---|
| The question | `question.text`, `question.wanted` |
| The document | `volume` title, publisher, licence sentence, retrieved date, cover text |
| The filing | the `section:` tag the online retrieval chose, with the twelve sections as options |
| The answer it gives | the re-ask's answer and the quoted passage with its page link |
| Actions | "Add to library" and "Remove", under the sentence "Add this document to the library, or remove it." A changed section plus Add is the refile. |

### 3.3 Curation

- Add to library (admit) sets `admission = admitted` and removes the marker.
- Add to library with a changed section (refile) writes the new section to the volume's hand tag file, which already survives
  rebuilds, then admits. Each refile also appends one line to a per-instance examples file
  that the section prompt reads, so the online retrieval's filing improves from the reader's corrections.
- Remove (reject) sets `admission = rejected`, removes the volume from search, and records the
  volume id in the shelf's `rejected.tsv` so a later pull of the same document is skipped.
  Rejection covers the one document. A rule against a publisher for a topic, or against a
  publisher outright, joins later if a rejection repeats.

The digest lists staged documents under "New downloads": what the online retrieval added since the last digest. Each opens its volume page, where the two actions sit.

## 4. The demo route on the Space

The Space adds a route, `#/demo`, that walks a visitor through five stations. Each station
shows a real screen of the app over seeded rows and one paragraph stating what the app did
and why. The seeded rows ship in the database: one stored question, its gap record, one
staged Wikipedia download with its cover and marker, the re-ask's answer, and one digest.

| Station | Screen | The paragraph states |
|---|---|---|
| 1 | Search with a query the library answers | The answer quotes a page; the page opens at the passage. |
| 2 | Search with the seeded question, offline switch on | The library has nothing; the question is stored with what the model said was missing. |
| 3 | Digest, offline switch off | The online retrieval named a topic, searched, pulled a document, filed it, and asked again. |
| 4 | The download panel | The reader sees the document, its section, and the answer it gives, and adds it or removes it. |
| 5 | The section page | The admitted document sits in its binder without the marker. |

The offline switch sits in the navigation on every instance. On, it forces the app's online
state false, so a question goes to the local queue as it would with no network. Off, it
returns to the browser's own signal. On a box the switch lets the reader rehearse the online retrieval;
on the Space it lets the visitor reach station 2.

## 5. Tables this document changes

| Table | Change |
|---|---|
| `question` | add `wanted` |
| `volume` | add `admission`, `admitted_at`, `admitted_by` |
| `page` | drop `audit`, `audit_by`, `audit_at`, `audit_note` |
| shelf files | add `rejected.tsv` (id, url, rejected_at, note) and `filing-examples.tsv` (question, section) |

## 6. Endpoints this document adds

| Endpoint | Does |
|---|---|
| `GET /api/candidates` | new downloads with their question, answer, and section (the path keeps its name) |
| `POST /api/verdict` | `{volume, verdict: admit or reject, section?}` adds to the library or removes (the path and verbs keep their names) |
| `GET /api/config` | the provider names and whether the online retrieval is on, for the app's status line |
| `GET /api/vss/clips` | the clips in `packs/vss-demo` with their length in seconds, and the vision model name |
| `POST /api/vss/stream` | `{clip, prompt, tracking}`: video summarization, one JSON record per step (frames cut, each ten-second chunk described, the report); when LIFEKIT_TOKEN is set on the box, the token is required |
| `GET /vss/{name}` | one clip file for the player; the name is confined to `packs/vss-demo` |
