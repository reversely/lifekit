# Concepts

This document names the concepts of LifeKit as the product is now defined, in the order a
reader meets them, and states what each one holds, how it appears, and which text a model
generates for it. It supersedes the entry-and-block model in `library-schema.md` sections
1.5 and 2.2, which a later revision of that document will bring in line.

## Summary

LifeKit is a compendium of resources. A reader downloads documents into a library, and
the app organises them into twelve binders by subject. Each document shows a cover that
describes its content in the document's own terms. When the reader comes back online, new
documents arrive one by one, and a digest reports what was added and answers the questions
the reader asked while offline. The app rewrites nothing; every generated line describes a
document or quotes one.

## Conventions

| Term | Names |
|---|---|
| volume | One document in the library: its file, its extracted text with page anchors, its licence, edition, and checksum. |
| cover | The face of a volume in the interface: generated text stating what the document contains and what it answers. |
| queue | Volumes in flight, one row per volume, with a state and a reason. |
| digest | The screen shown on return to connectivity: volumes added and stored questions answered. |
| binder | One of twelve subjects. A binder collects the volumes that serve it. |
| topic index | A later layer inside a binder: plain pointers from a topic into volumes and pages. |
| question | Something the reader asked: answered now from the library, or stored and answered in a later digest. |
| profile | The reader's location, activities, household, and trips. It decides which volumes the queue fetches. |

## 1. Library

The library holds volumes. A volume enters through the queue and leaves only when nothing
refers to it.

| Field of a volume | Source |
|---|---|
| file, sha256, retrieved date | the fetch |
| extracted text with page anchors | text extraction, OCR where the file carries no text |
| licence, licence sentence, where read | the volume list or the fetch |
| edition, publisher, title | the document |
| cover text | generated once from the contents and first pages, editable by hand |
| topics covered | computed from the extracted text |

The library screen lists volumes latest first. Each item shows the cover. Opening a volume
shows its contents outline and opens any page at its anchor.

## 2. Queue

One row per volume, whatever put it there:

- the stock set for the twelve binders on first install;
- profile and trip rules, when onboarding or a change of place matches;
- the question loop, when a stored question is worked online and a source is found.

States: `queued`, `downloading`, `extracted`, `indexed`, `shelved`, `failed` with the
reason. A volume shelves into its binders automatically at `indexed`; the reader can move
or remove it afterwards.

## 3. Digest

Produced when the app regains connectivity and the queue drains. Two parts:

1. Volumes added, each with one generated sentence saying what it adds.
2. Stored questions now answered, each with the answer, the quoted passage, and the page
   link.

The digest is kept, so the reader can scroll back through earlier ones.

## 4. Binders

Twelve subjects in the manual's priority order. A binder shows its volumes, latest first,
each with its cover and its role (primary, reference, figures, archive). Membership is
automatic from the volume list and editable by hand.

The topic index comes after the raw material is settled. It is a plain list of topics
under a binder, each with a one-line gloss and pointers into volumes and pages. It carries
no advice and no rewritten source text.

## 5. Questions and chat

A question asked with the library reachable is answered from it: the answer quotes the
passage it rests on and links the page. A question the library cannot answer is stored
with the profile of the moment. Online, the loop names a topic, finds a source, queues it
as a volume, and, once the volume is indexed, asks the question again. An answered
question appears in the next digest.

## 6. Profile

Location (live, never written to a pack), home region, activities, household, trips. Pull
rules match the profile to volumes. A profile change re-evaluates the rules and queues what
is now matched and absent.

## 7. Generated text

Three prompts, each one paragraph. The model is a Nemotron-class instruction model, so
the instruction is literal.

Cover:

> You are given the table of contents and the first pages of a document. Write, in plain
> words, what this document contains and what questions it can answer. Use the document's
> own terms. Five lines at most. Do not evaluate the document and do not add advice.

Digest line:

> A document was added to the library. Given its cover text, write one sentence saying
> what it adds. If it answers a stored question, say which.

Answer:

> Answer the question using only the passages given. Quote the passage you rely on and
> name its document and page. If the passages do not answer the question, say so in one
> sentence.

## 8. Rules across concepts

- No rewrite of a source anywhere. Generated text describes a document or quotes one.
- Automatic by default, editable by hand: shelving, binder membership, cover text.
- Every generated line names the volume and page behind it.
- Sorting is by arrival everywhere until the topic index exists.
- The library and the binders are separate: a volume exists once, and binders point at it.
