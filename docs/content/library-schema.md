# The library schema

## Summary

LifeKit answers questions by quoting sources it carries. This document defines how those
sources are stored so that an answer can point at the page it came from, a reviewer can
approve content one page at a time, and a user's own geography and needs can add sources
without changing the app. The structure copies a library: a shelf holds volumes, a volume
has pages, a page yields passages, and a dictionary entry on the shelf's index card cites
passages and names the volumes behind it. A stock profile fills the twelve shelves with a
small core set; an onboarding flow of multiple-choice questions pulls further volumes that
match where the user lives and what they do.

## Conventions

The vocabulary below is used throughout. Each term names one table.

| Term | Names |
|---|---|
| shelf | One of the twelve encyclopedia tiles. A shelf orders volumes and entries. |
| volume | One source work: a document, a web page set, a figure collection, or a dataset. The unit that a pull fetches and a licence governs. |
| page | One addressable unit of a volume: a PDF page, a web section, a dataset partition. The unit a reviewer audits. |
| passage | One verbatim span of a page. The unit retrieval returns and a block cites. |
| entry | One dictionary entry on a shelf: the authored card a reader opens, such as "Hypothermia" or "Bowline". |
| block | One typed paragraph of an entry's authored copy. Every block cites at least one passage. |
| scope | A structured statement of where and to whom a volume, passage, or entry applies. |
| profile | The user's answers: stock values plus onboarding answers. A profile selects scopes and triggers pulls. |
| pull | The act of fetching one volume bundle into the local library. |

The document draws four relations, and no single table mixes two of them:

- `contains`: shelf to volume, volume to page, page to passage, entry to block.
- `cites`: block to passage. Only this relation carries authored copy to its source.
- `links`: entry to entry (see also), entry to volume (the books behind this card).
- `applies-to`: volume, passage, or entry to scope.

Identifiers are stable, human-readable strings. A volume id takes the form
`publisher-work-edition`, for example `ifrc-first-aid-guidelines-2020`. A page id appends the
page number: `ifrc-first-aid-guidelines-2020/p402`. A passage id appends a per-page counter:
`ifrc-first-aid-guidelines-2020/p402/3`. An entry id takes `shelf/slug`:
`medicine/hypothermia`. A revision id appends `@N`: `medicine/hypothermia@2`. A block id appends a counter to the revision: `medicine/hypothermia@2/b04`.

Asserted values come from a source page or from a reviewer and sit in the tables of section
1. Derived values are computed from asserted ones and sit in section 2. A derived value is
never stored as if asserted.

## 1. Asserted tables

### 1.1 shelf

Twelve rows, in the manual's priority order. `docs/content/sources-by-tile.md` lists the
volumes each shelf starts with.

| Column | Type | Meaning |
|---|---|---|
| id | text | `medicine`, `shelter`, `fire`, `water`, `food`, `poisonous-plants`, `animals`, `tools`, `direction`, `signaling`, `environments`, `hazards` |
| order | integer | Position 1 to 12. |
| title | text | The tile title as displayed. |
| scope_line | text | One line under the title. |

### 1.2 volume

One row per source work. The row carries everything needed to credit the work, verify the
copy, and decide whether the pack may carry it.

| Column | Type | Meaning |
|---|---|---|
| id | text | Stable id as defined in Conventions. |
| title | text | Title as printed. |
| publisher | text | Issuing body or author. |
| edition | text | Year or edition string as printed. |
| url | text | Where the copy was retrieved. |
| format | text | `pdf`, `html`, `image-set`, `dataset`. |
| licence | text | An SPDX identifier where one exists (`CC-BY-4.0`, `CC-BY-SA-4.0`, `CC0-1.0`, `CC-BY-NC-SA-3.0-IGO`), `LicenseRef-US-Gov-PD` for US federal works, `LicenseRef-OGL-3.0` for UK OGL, or one of the states in section 3. |
| licence_statement | text | The licence sentence verbatim as read on the source. |
| licence_read_at | text | URL or page where that sentence appears. |
| retrieved | date | Date the copy was fetched. |
| sha256 | text | Digest of the fetched file, or of the concatenated page set for HTML. |
| carry | text | `carry` when the pack ships the copy, `link` when terms allow only a link. |
| tier | text | `core` (in the stock profile), `regional` (pulled by a profile rule), `learned` (added by the fetch pass). |
| language | text | BCP 47 tag. |
| page_count | integer | Number of page rows. |
| freshness | text | `static` (a fixed edition), `seasonal` (rules that change on a schedule, such as trapping seasons), `live` (a value published continuously, such as a fire restriction stage or a river gauge). |
| live_source | json | For `live` volumes: endpoint and field the app reads when online. Empty otherwise. |
| superseded_by | text | Id of the volume that replaces this one, or empty. Both volumes stay in the library; section 2.2 states what happens to dependents. |

`volume_tag` holds a volume's categories, many per volume. A tag is `namespace:value`. The
twelve sections use the namespace `section` and are the tags a binder collects on; any other
namespace is free (`topic:ticks`, `region:US-WA`, `kind:figures`). The Library screen shows
tags as bubbles and filters on them.

| Column | Type | Meaning |
|---|---|---|
| volume_id | text | References volume. |
| tag | text | `namespace:value`. |
| source | text | `rule` (the volume list or a pull rule), `model` (a classifier), `hand` (the user). A hand tag survives every rebuild; a hand removal does too. |
| at | date | When set. |

`shelf_volume` is derived from `section:` tags plus a role, and places volumes on shelves.
One volume may sit on several shelves.

| Column | Type | Meaning |
|---|---|---|
| shelf_id | text | References shelf. |
| volume_id | text | References volume. |
| order | integer | Position on the shelf, for the "books behind this shelf" list. |
| role | text | `primary` for the shelf's primary authority, `reference`, `figures`, `archive`. |

### 1.3 page

One row per addressable unit of a volume. The page is the audit unit: a reviewer sees the
page render, its extracted text, and every passage cut from it on one screen, and records one
verdict for all of them.

| Column | Type | Meaning |
|---|---|---|
| id | text | `volume_id/pNNN`. |
| volume_id | text | References volume. |
| number | integer | Page number as printed, or section ordinal for HTML. |
| anchor | text | Deep link into the copy: PDF page index, URL fragment, dataset key. |
| text | text | Extracted text of the page. |
| render | text | Pack-relative path of the page image, when one exists. |
| figures | json | List of figure ids on the page. |
| audit | text | `unaudited`, `approved`, `rejected`, `superseded`. |
| audit_by | text | Reviewer identifier. |
| audit_at | date | Date of the verdict. |
| audit_note | text | Reviewer's note, free text. |

### 1.4 passage

One row per verbatim span. A passage never contains authored words. Its text is a substring
of its page's text at the recorded offsets, and a build check fails when it is not.

| Column | Type | Meaning |
|---|---|---|
| id | text | `page_id/N`. |
| page_id | text | References page. |
| start, end | integer | Character offsets into page.text. |
| text | text | The span, verbatim. |
| kind | text | `principle`, `procedure_step`, `checklist`, `materials`, `warning`, `note`, `mnemonic`, `figure_caption`, `table_row`, `definition`, `archive`. |
| topics | json | Controlled topic codes from the shelf's topic list (section 1.8). |
| scope_id | text | References scope, or `universal`. |
| data | json | For `table_row` passages: the row's values with units, for example `{"volume": [1, "gal"], "bleach_6pct": [8, "drop"]}`. Unit conversion happens at answer time from profile.units. Empty for prose passages. |

`figure` holds one row per image the pack carries. A figure has its own licence because
image collections such as Wikimedia Commons categories license each file separately.

| Column | Type | Meaning |
|---|---|---|
| id | text | `volume_id/fNNN`. |
| volume_id | text | References volume. |
| page_id | text | References the page the figure sits on, or the file's own page for an image-set volume. |
| path | text | Pack-relative path of the image. |
| caption | text | Caption as printed, when one exists. |
| licence | text | Same vocabulary as volume.licence. |
| licence_statement | text | Verbatim. |
| url | text | Where the file was retrieved. |

### 1.5 entry

One row per dictionary card. The entry carries the authored copy the reader sees, and every
paragraph of it cites passages.

| Column | Type | Meaning |
|---|---|---|
| id | text | `shelf_id/slug`. |
| shelf_id | text | References shelf. |
| order | integer | Position in the shelf's index. |
| title | text | Card title. |
| gloss | text | One line in plain words, shown in the index and used at first mention. |
| kind | text | `topic` (reading), `procedure` (steps), `identification` (traits), `card` (a reference table). |
| scope_id | text | References scope, or `universal`. |

`entry_revision` holds every version of an entry's copy. The entry row names the card; a
revision carries the words. Old revisions stay in the library, so a link or a test that named
them still resolves.

| Column | Type | Meaning |
|---|---|---|
| id | text | `entry_id@N`, N counting from 1. |
| entry_id | text | References entry. |
| approval | text | `draft`, `audited`, `copy_reviewed`, `rag_tested`, `approved`, `retired`. The three review parts advance this value in order. |
| reviewer | text | Who moved it to its current state. |
| at | date | When. |
| reason | text | Why this revision exists: a new edition cited, a copy fix, a rejected page. |

`block` holds a revision's paragraphs.

| Column | Type | Meaning |
|---|---|---|
| id | text | `revision_id/bNN`. |
| revision_id | text | References entry_revision. |
| order | integer | Position in the entry. |
| kind | text | Same set as passage.kind, plus `divergence` for a paragraph that states where an archived source differs from the current authority. |
| text | text | Authored copy, in field-guide fragments. |
| figure_id | text | Optional figure. |

`block_cites` links a block to its evidence. Every block has at least one row, and every row
references a passage of a volume with `carry = carry`. A link-only volume reaches the reader
through `entry_links` with kind `on_shelf`, never through a citation.

| Column | Type | Meaning |
|---|---|---|
| block_id | text | References block. |
| passage_id | text | References passage. |
| role | text | `supports` (the block restates this passage), `figure` (the passage captions the figure), `diverges` (the block reports that this passage disagrees with the primary authority). |

`entry_links` holds the explicit shelf links.

| Column | Type | Meaning |
|---|---|---|
| from_revision | text | References entry_revision. |
| to_entry | text | References entry, for `see_also`. The reader's view resolves it to that entry's latest approved revision, so a draft never shows through a neighbour's link. Null for a volume link. |
| to_volume | text | References volume, for `on_shelf`. Null for an entry link. |
| kind | text | `see_also`, `on_shelf`, `prerequisite`, `next_step`. |
| label | text | The link text shown on the card. |

### 1.6 scope

A scope states applicability. Every column is optional. An empty column means the scope does
not restrict on that axis. The row `universal` has every column empty.

| Column | Type | Meaning |
|---|---|---|
| id | text | Stable id, for example `us-wa-winter`. |
| country | json | ISO 3166-1 alpha-2 codes. |
| region | json | ISO 3166-2 codes. |
| admin2 | json | County FIPS codes in the US, the national equivalent elsewhere. Used by county-keyed datasets such as tick distribution tables. |
| hemisphere | text | `north` or `south`, for celestial methods and seasons. |
| climate | json | Köppen-Geiger classes, for example `Csb`, `Dfc`. |
| terrain | json | `coast`, `mountain`, `desert`, `forest`, `urban`, `river`, `sea`. |
| months | json | 1 to 12. |
| activity | json | `home`, `day_hike`, `backpacking`, `boating`, `winter_travel`, `driving`, `foraging`. |
| audience | json | `adult`, `child`, `infant`, `pregnancy`, `pet`, `elderly`. |
| hazards | json | `wildfire`, `flood`, `earthquake`, `hurricane`, `tornado`, `avalanche`, `radiation`, `outage`. |

Scope matching ranks on `audience` and filters on the other axes. A passage for children
ranks above the adult passage when the profile includes a child, and the adult passage still
returns when no child passage exists.

### 1.7 profile and pull rules

`profile` holds one user's answers. The stock profile ships with every column at its default,
and onboarding fills the rest.

| Column | Type | Default | Onboarding question |
|---|---|---|---|
| country, region | text | unset | "Where do you live?" (picker) |
| admin2 | text | unset, or derived from location when the app holds one | none |
| climate | json | derived from region via the Köppen dataset, a list when the region spans several classes; narrowed by location when present | none |
| location | json | unset; a live coordinate the app may hold. It is never written into a pack or a pull request. | none (device permission) |
| trips | json | empty; a list of `{region, months}` | "Planning a trip?" (region picker and months) |
| terrain | json | unset | "What is around you?" (multiple choice) |
| activities | json | `home` | "What do you do outdoors?" (multiple choice) |
| household | json | `adult` | "Who is in your household?" (multiple choice) |
| hazards | json | derived from region via the hazard dataset | "Which of these worry you?" (multiple choice, pre-ticked from the derived list) |
| units | text | by country | "Metric or imperial?" |
| languages | json | by country | "Languages you read" |

Scope matching at answer time uses `location` when the app holds one and the profile's home
region otherwise. Pull rules match the home region and every trip, so volumes for a planned
destination arrive before departure.

`pull_rule` maps a profile to volumes. Rules are data, so a new region needs rows, not code.

| Column | Type | Meaning |
|---|---|---|
| id | text | Stable id. |
| predicate | json | A conjunction over profile columns, for example `{"country": ["US"], "region": ["US-WA"]}`. |
| volume_ids | json | Volumes to pull when the predicate matches. |
| shelf_id | text | Shelf the volumes join. |
| reason | text | One line shown to the user in the pull feed. |

Example rows:

| id | predicate | volumes | reason |
|---|---|---|---|
| wa-plants | country US, region US-WA | `usda-ars-bulletin-415-2011`, `wa-dnr-poisonous-plants` | Poisonous plants of the western states |
| pnw-ticks | region US-WA, US-OR, US-ID | `cdc-tickborne-manual-2024`, `cdc-ixodes-county-table` | Ticks recorded in your county |
| boating | activity boating | `navcen-vhf-channels`, `nws-coldwater` | Marine radio and cold water |
| infant | household infant | `ifrc-first-aid-guidelines-2020` pages 300 to 340 | Infant CPR and choking |
| cold-climate | climate Dfb, Dfc, Dsc, ET | `tc-21-3-1986`, `tb-med-508-2005` | Snow shelters and cold injury |

### 1.8 topic codes

Each shelf owns a flat list of topic codes, for example `water/boiling`, `water/chlorine`,
`water/crossing`, `medicine/bleeding`, `medicine/hypothermia`. Passages and entries carry
topic codes. Retrieval filters on them when the question classifier names a topic, and the
shelf index groups entries by them. The lists live in `topics.tsv` with columns
`shelf_id, code, label, gloss, policy` and change only through the approval process.

`policy` states what an answer on that topic may do: `answer` (quote and advise),
`reference_only` (show identification references and sources, give no verdict; every edibility
topic takes this value), `emergency_only` (show the procedure behind a banner stating it is for
a declared emergency and illegal otherwise; snares, deadfalls, and fish traps take this value).

### 1.9 question and rag_test

`question` stores every question the fetch pass handles, as designed for the fetch pass.

| Column | Type | Meaning |
|---|---|---|
| id | text | Stable id. |
| text | text | As asked. |
| profile_snapshot | json | The profile at the time. |
| asked_at | date | Timestamp. |
| state | text | `stored`, `named`, `searching`, `staged`, `extracted`, `indexed`, `re_asked`, `resolved`, `exhausted`. |
| topic | text | Model-named topic, once online. |
| answer_passages | json | Passage ids the resolving answer quoted. |

`rag_test` holds the regression set. Every approved entry contributes rows, and every resolved
question adds one.

| Column | Type | Meaning |
|---|---|---|
| id | text | Stable id. |
| question | text | The query. |
| profile | json | Profile the test runs under. |
| expected_passages | json | Passage ids that must appear in the top three. |
| origin | text | `revision:<id>` or `question:<id>`. |
| last_run, last_pass | date, boolean | Latest result. |

### 1.10 stream and observation

A `live` or `seasonal` volume describes a stream: a value that changes in the world, such as
a river gauge, a fire restriction stage, an avalanche rating, or a boil-water notice. The rule
text stays in passages ("turn back above the knee"). The values live in an append-only
observation log with two clocks, so a reading is never edited and a correction adds a row.

| Column | Type | Meaning |
|---|---|---|
| stream_id | text | `volume_id/streamkey`, for example `usgs-nwis/12113000`. |
| valid_from, valid_to | datetime | When the value held in the world. valid_to is empty for the latest reading. |
| recorded_at | datetime | When the library learned it. |
| value | json | The reading with units, or the stage, or the rating. |
| source_url | text | The exact request that produced it. |
| fetched_by | text | Agent and version: the app's fetcher, the pack builder, the fetch pass. |
| supersedes | text | Id of an earlier observation this one corrects, or empty. |

A passage that applies a rule to a stream names the stream id in `data`, and the answer reads
the latest observation at answer time. No entry and no test pins a reading.

### 1.11 provenance

One row per entity the library holds, stating what produced it. The vocabulary follows the
W3C PROV model: an entity, the activity that made it, the agent that ran the activity, and the
entities it was derived from.

| Column | Type | Meaning |
|---|---|---|
| entity_id | text | A volume, page, passage, figure, revision, observation, or learned volume. |
| activity | text | `fetch`, `segment`, `render`, `audit`, `author`, `review`, `extract`, `resolve`, `pull`. |
| agent | text | A script with its version, a model with its name, or a reviewer. |
| derived_from | json | Entity ids the activity read. |
| at | datetime | When. |

"Why does the app say this" walks this table upward from a block to a passage to a page to a
sha256-pinned volume, or to a timestamped observation. "What changed since a date" is a query
over `at`.

## 2. Derived tables

These are rebuilt from section 1 and never edited by hand.

- `user_shelf`: for a profile, the ordered union of core volumes and the volumes every matching
  pull rule names, per shelf. The shelf screen shows this as "books on this shelf". A regional
  volume that no rule matches any more (the user moved) leaves the shelf and joins a removal
  list the library screen offers.
- `search_index`: an FTS5 index over passage.text, and an embedding per passage (model name and
  dimension recorded in the pack manifest). Each passage carries an authority rank derived from
  `shelf_volume.role`: `primary` ranks first, then `reference` and `figures`, then `archive`.
  Retrieval filters passages whose scope matches the profile or location, ranks by combined
  score and authority, and returns passage, page, volume, role, and edition so an answer can
  name the edition it quotes and label an archive passage as such. The reviewer's audit screen
  and the reader's "show me the page" screen are the same view.
- `credits.md`: rendered from volume and figure rows with `carry = carry`.
- `coverage`: per shelf, the count of entries by the approval state of their latest revision, the count of pages by audit
  state, and every topic code with no `universal` entry or passage. The approval process reads
  this to pick the next packet, and the build refuses a pack with a topic that has no universal
  answer.
- `entry_sources`: the numbered source list at the foot of each card, derived from block_cites
  through passage to volume.
- `entry_terms`: the strictest licence among an entry's cited volumes and figures, shown in the
  source footer. An entry that cites a CC BY-SA passage carries CC BY-SA terms.
- `cited_by`: the reverse index over block_cites and entry_links: for a passage, page, volume,
  figure, or entry, every revision that depends on it.
- `work_list`: every approved revision that depends on a superseded volume, a rejected page, or
  a retired entry, with the dependency that changed. Section 2.2 states how it is worked.

### 2.2 Versions and dependents

The dictionary is a graph. A card cites passages on several shelves and links to cards on
others, so a change to one node reaches every node that points at it. Three rules keep the
graph consistent without a global "current" version.

1. Every citation pins an exact version. A block cites one passage of one edition. A link names
   an entry and resolves, in the reader's view only, to that entry's latest approved revision.
2. Versions coexist. A new edition adds a volume row and a `superseded_by` link on the old one.
   A copy change adds a revision. Nothing that was cited is edited or removed.
3. A change produces work, not breakage. Superseding a volume, rejecting a page, or retiring an
   entry adds each dependent revision to `work_list`. The dependent keeps serving its approved
   revision until an author writes a new revision against the new version and it passes the
   three-part approval. A water entry can cite the 2028 edition while a hazards entry still cites
   2026; each block names the edition it quotes.

A version is removable only when `cited_by` returns nothing for it and no `rag_test` names it.
The pack builder enforces this; a build that would drop a cited version fails.

The reader-facing update log is the manifest diff between two pack versions plus the
observation rows recorded since the last pull: volumes added, editions superseded, regional
volumes pulled for a trip, readings refreshed.

### 2.1 Retrieval rules

- Language: retrieval prefers passages in a profile language and falls back to any language.
  The model answers in the reader's language and quotes the passage verbatim in its own.
- Topic filter: when the question classifier names a topic and the filtered search returns
  nothing above threshold, retrieval retries with no topic filter before the answer declares
  non-coverage and stores the question.
- Freshness: an answer that quotes a `seasonal` or `live` volume states the pack's retrieved
  date when offline and reads `live_source` when online.
- Learned volumes: passages extracted by the fetch pass take the scope of the question's
  profile snapshot, and the entry that resolves the question links to them with `on_shelf`.
- Policy: an answer on a `reference_only` topic returns references and sources and no verdict;
  an `emergency_only` topic returns its procedure behind the banner.

## 3. States of a field without a plain value

| Field | State | Meaning |
|---|---|---|
| volume.licence | `unknown` | The source carries no statement, and the search for one was made and recorded in licence_read_at. |
| volume.licence | `all-rights-reserved` | A statement was read that reserves rights. carry must be `link`. |
| volume.licence | `gated` | Access needs an agreement or account. carry must be `link`. |
| scope_id | `universal` | The item applies everywhere. The column stores this as a value rather than as an absence. |
| scope_id | `unassessed` | No one has decided applicability yet. Retrieval treats it as universal and the audit screen lists it. |
| page.render | null | The volume has no page image (HTML, dataset). The anchor still resolves. |
| block_cites | no rows | Forbidden. The build fails. |

## 4. Files in a pack

A pack is a directory the app reads and a pull extends.

```
pack/
  manifest.tsv            volume rows, one per line (the current lifekit-packs manifest, extended)
  library.sqlite          every table in sections 1 and 2 except embeddings
  topics.tsv
  pull_rules.tsv
  volumes/<volume_id>/
    source.<ext>          the carried copy, when carry = carry
    pages.jsonl           page rows for this volume
    passages.jsonl        passage rows for this volume
    renders/pNNN.png      page images, when they exist
```

A pull fetches one `volumes/<volume_id>/` directory and merges its rows into `library.sqlite`.
The stock pack ships the core tier. A profile change re-evaluates pull rules and queues the
volumes that are now matched and absent. Learned volumes from the fetch pass use the same
directory shape with `tier = learned`.

## 5. How a source in the survey becomes rows

1. The volume row is written from the survey table: title, publisher, edition, url, licence,
   licence statement, retrieved date. carry follows the licence.
2. The fetcher stores the copy, computes sha256, and cuts pages: one row per PDF page or per
   heading section for HTML, with text and anchor.
3. A segmenter cuts passages from each page by structure (numbered steps, warnings, table rows,
   captions) and assigns kind. Offsets are recorded and checked.
4. A reviewer audits pages: the page render, its text, and its passages on one screen, one
   verdict per page.
5. An author writes an entry revision and its blocks, citing passages. The build refuses a
   block with no citation and a new citation to a passage on a rejected page.
6. The three-part approval advances the revision's approval. Each approved revision adds its
   rag_test rows.
7. When a page is rejected after approval, or a volume gains `superseded_by`, every approved
   revision that cites it joins `work_list` and keeps serving until a new revision is approved
   (section 2.2).

## 6. Open decisions

- Retrieval is OCR plus full-text search: Tesseract for scanned pages without a text layer,
  FTS5 over passages, ranked with the volume's role and the passage kind. No embeddings.
- Whether HTML volumes are snapshotted as PDF renders so every page has an image, or kept as
  text with anchors only.
- The topic code lists for each shelf. They are the first artifact of each tile's approval.
