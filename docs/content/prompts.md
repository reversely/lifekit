# Prompts for the small model

This document holds the system prompts LifeKit sends to its small instruction model, the
format each one must produce, the openings and words it may not use, and one example of
acceptable output per prompt. The model is Nemotron-class (about 8 to 9 billion
parameters, or Apple's on-device model), so every rule is literal: a rule stated as a
principle is not followed; a rule stated as a banned word is.

## Conventions

- A prompt is one paragraph of plain sentences. No headings inside the prompt, no lists.
- Every prompt states the output length as a number of sentences, never "brief".
- Every prompt names the first word's job ("the first word names the subject"), because
  the model otherwise opens with "This document".
- Banned words are listed in the prompt itself, not in a separate file the model never sees.
- The example under each prompt is the acceptance test: a new output that reads like the
  example passes; one that reads like the "before" fails.
- A change to a prompt is a change to this document first; the code copies the text.

## 1. Cover

Input: title, publisher, edition, table of contents (bookmarks or headings), the first six
pages of text.

Prompt:

> Write the cover text for a document from its table of contents and first pages. Rules: at
> most three sentences. The first word names the subject, taken from the contents. Never
> begin a sentence with "This document", "The document", "It", or "This". Use the document's
> own terms. State what it covers and what questions it answers. No evaluation: do not use
> comprehensive, essential, valuable, useful, important, detailed, or quick. No advice. No
> bullet points.

Before (rejected): "This document provides a comprehensive guide to first aid, covering
fundamental criteria, basic measures, and specific injuries."

After (accepted): "First aid for a casualty in the field: evaluating the casualty, opening
the airway, restoring breathing, stopping bleeding, and treating fractures, climatic
injuries, and bites. Appendices cover first aid kits and rescue and transport procedures."

## 2. Digest line

Input: the cover text of a volume that arrived, and the list of stored questions.

Prompt:

> Write one sentence, at most 25 words, stating what a newly added document covers, from its
> cover text. The first word names the subject. Never write "document", "added", "library",
> "This", or "It". Example of the expected form: "Bee stings: venom effects, removing the
> stinger, allergic reactions, and when to seek care."

Before: "This document adds information on the symptoms and treatment of heat exhaustion."

After: "Heat exhaustion and heatstroke symptoms, cooling steps, and when to call for help,
from NHS England."

## 3. Answer

Input: the question and the top passages, each labelled with document, edition, and page.

Prompt:

> Answer the question using only the passages given. Begin your reply with the word ANSWERED
> if the passages answer the question, or NOT ANSWERED if they do not. After that word, quote
> the passage you rely on and name its document and page. If the passages do not answer the
> question, say so in one sentence.

The first word is the coverage verdict the code reads (`covers.covered`). A reply that begins
NOT ANSWERED stores the question for the fetch pass; the word is stripped before display. Measured
limitation: the 8B model sometimes writes ANSWERED over passages that only share a word with
the question (a frostbite passage for "at what temperature does seawater freeze"). The quoted
passage is always shown beside the answer so the reader sees what it rests on.

After: "Pull the tick upward with even pressure; do not twist or jerk it. Remove the whole
tick, mouthparts included, and seal it in a bag or drop it in alcohol. (ATP 4-02.11, March
2026, page 184)"

## 4. Topic name

Input: a question the library could not answer.

Prompt:

> Name the topic of this question in one to four words, as a noun phrase a librarian would
> file it under. Output the phrase only. If the question is small talk or a greeting, output
> the word none.

After: "tick-borne disease"

## What the 8B model did with the first version, and the fix

A prompt made only of rules ("never begin with This document", "do not use comprehensive")
was not followed by Llama 3.1 8B: it added a preamble ("Here is a possible cover text"), a
title line, and kept both the banned opening and the banned words. Two changes made it hold:

1. One example of the expected form inside the prompt (the "After" text above). Small models
   copy a shape more reliably than they obey a prohibition.
2. A cleaning pass after generation: drop preamble lines and heading-only lines, drop any
   sentence that begins with a banned opening, then run the banned-word check and regenerate
   once if it fails. A text that still fails is left for a hand edit and listed by
   `covers --check`.

On the medicine shelf this took the failure count from 13 of 13 texts to 3 of 26 (one
"essential" in a cover, two "comprehensive" in digest lines).

## 5. Section for a learned document

Input: the stored question and its topic.

Prompt (abridged; the code holds the section list with a gloss per section):

> Choose the one section of a survival library this document belongs in. Sections and what
> they hold: medicine (first aid, illness, medicines); shelter (...); ... Output the section id
> only.

The code takes the longest section id that appears anywhere in the reply, since the model
often adds words around it, and falls back to `tools`.

## Words and openings banned in every prompt

Openings: "This document", "The document", "It", "This", "In this".
Evaluation: comprehensive, essential, valuable, useful, important, detailed, quick,
in-depth, helpful, key.
Filler: "provides information on", "aims to", "is intended to", "covers a wide range".

## What is measured

- Covers: zero banned openings and zero banned words across the shelf, checked by a grep
  in the build. A cover that fails is regenerated once, then left for a hand edit.
- Digest lines: the same check.
- Answers: the RAG tests, which record the expected page per question.
