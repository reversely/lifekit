# Deployments and the approval of library additions

This document states where LifeKit runs, who approves what the question loop adds to the
library, and how the public demo shows that loop without running it. It fixes the decisions
the repo owner made on 2026-09-12 and gives the tables and screens that follow from them.
It supersedes the page audit in `library-schema.md` (the `page.audit` columns and section 6)
and the three-part section approval recorded on 2026-08-23.

## Summary

LifeKit runs as one codebase on two kinds of host. An instance on a GPU box serves one
household: it downloads documents, answers questions from them, stores questions it cannot
answer, and, when a source turns up, adds the document to the library and answers. The owner
of the box reviews each addition. The public Space on Hugging Face runs the same web app over
a fixed database and plays a recorded pass of the loop so a visitor can see each pathway.

## Conventions

| Term | Names |
|---|---|
| instance | One running LifeKit: a database, an API, a web app, and a model endpoint. |
| box | A GPU host that runs a real instance for its owner. The first two are the Acer Veriton GN100 and a DGX Spark; both carry the GB10 and 121 GB of unified memory. |
| Space | The Hugging Face Space `reversely/lifekit`, a demo instance with no live loop. |
| owner | The person who runs a box. The owner approves additions. |
| provider | The setting that names the model endpoint an instance calls. |
| gap record | What the model writes when it cannot answer: the question, the topic, and the kind of document that would answer it. |
| candidate | A document the loop fetched, cut, and indexed for a stored question, awaiting the owner's verdict. |
| packet | The screen that shows one candidate for a verdict. |
| verdict | The owner's decision on a candidate: admit, refile, or reject. |

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
ships in the image. The loop does not run: a public Space has no owner to approve additions
and no per-visitor storage, so live pulls would show every visitor the admissions of every
other visitor. The demo route (section 4) plays a recorded pass instead. The provider
setting on the Space names Hugging Face inference with Llama 3.1 8B Instruct for the live
answer path, the model the covers were written with.

### 1.3 The provider setting

| Variable | Box | Space |
|---|---|---|
| `LIFEKIT_MODEL_SMALL` | `openai:http://localhost:30081/v1:nvidia/nemotron-nano-9b-v2` | `hf:meta-llama/Llama-3.1-8B-Instruct` |
| `LIFEKIT_MODEL_ANSWER` | same as small | same as small |
| `LIFEKIT_LOOP` | `on` | `off` |

The API reads these at start. `openai:` names an OpenAI-compatible endpoint and a model id;
`hf:` names a Hugging Face inference model. The API's model call already reaches the loop as
an injected function, so the setting changes one constructor.

## 2. The gap record

When the answer prompt returns NOT ANSWERED, the model writes a gap record in the same
reply, after the verdict word: the topic in one to four words and the kind of document that
would answer the question, in one sentence. The API stores both on the question row. The
record replaces the separate topic prompt the loop runs today, so the loop starts from what
the model said was missing at the moment it failed.

| Column on `question` | Holds |
|---|---|
| `topic` | The noun phrase the model filed the question under. |
| `wanted` | One sentence naming the kind of document that would answer it. |

## 3. Candidates and verdicts

### 3.1 The staged state

The loop fetches, cuts, indexes, covers, and files a candidate exactly as it does now, and
marks the volume `staged`. A staged volume appears in search, in its section, and in Recent
with the marker "New download" on its card and on its page. The re-ask runs against it, so
the packet can show the answer the addition would give.

| Column on `volume` | Values |
|---|---|
| `admission` | `stock` for a volume from a shelf list; `staged` for a loop addition awaiting a verdict; `admitted`; `rejected`. |
| `admitted_at`, `admitted_by` | The verdict's date and the owner. |

Search excludes `rejected` volumes. Everything else ranks as today.

### 3.2 The packet

One screen per candidate, reached from the digest and from the marker on the card:

| Region | Reads |
|---|---|
| The question | `question.text`, `question.wanted` |
| The document | `volume` title, publisher, licence sentence, retrieved date, cover text |
| The filing | the `section:` tag the loop chose, with the twelve sections as options |
| The answer it gives | the re-ask's answer and the quoted passage with its page link |
| Verdict | Admit, Refile, Reject, under the sentence "Admit, refile, or reject this document." |

### 3.3 Verdicts

- Admit sets `admission = admitted` and removes the marker.
- Refile writes the new section to the volume's hand tag file, which already survives
  rebuilds, then admits. Each refile also appends one line to a per-instance examples file
  that the section prompt reads, so the loop's filing improves from the owner's corrections.
- Reject sets `admission = rejected`, removes the volume from search, and records the
  volume id in the shelf's `rejected.tsv` so a later pull of the same document is skipped.
  Rejection covers the one document. A rule against a publisher for a topic, or against a
  publisher outright, joins later if a rejection repeats.

The digest lists staged documents under "New downloads": what the loop added since the last digest. Each opens its volume page, where the verdict sits.

## 4. The demo route on the Space

The Space adds a route, `#/demo`, that walks a visitor through five stations. Each station
shows a real screen of the app over seeded rows and one paragraph stating what the app did
and why. The seeded rows ship in the database: one stored question, its gap record, one
staged Wikipedia candidate with its cover and marker, the re-ask's answer, and one digest.

| Station | Screen | The paragraph states |
|---|---|---|
| 1 | Search with a query the library answers | The answer quotes a page; the page opens at the passage. |
| 2 | Search with the seeded question, offline switch on | The library has nothing; the question is stored with what the model said was missing. |
| 3 | Digest, offline switch off | The loop named a topic, searched, pulled a document, filed it, and asked again. |
| 4 | The packet | The owner sees the document, the filing, and the answer it gives, and gives a verdict. |
| 5 | The section page | The admitted document sits in its binder without the marker. |

The offline switch sits in the navigation on every instance. On, it forces the app's online
state false, so a question goes to the local queue as it would with no network. Off, it
returns to the browser's own signal. On a box the switch lets the owner rehearse the loop;
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
| `GET /api/candidates` | staged volumes with their question, answer, and filing |
| `POST /api/verdict` | `{volume, verdict, section?}` applies one verdict |
| `GET /api/config` | the provider names and whether the loop is on, for the app's status line |
