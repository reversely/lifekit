# Library schema walkthrough

This document tests `library-schema.md` against user flows and queries, tile by tile and
across tiles. Each row names a scenario, traces the path through the tables, and records
whether the schema holds or which change it needed. The changes are applied in
`library-schema.md` and listed at the end with the number each row cites.

## Conventions

- "Profile" means the user's stored answers. "Location" means a live GPS fix the app may hold.
- "Holds" means the tables as written produce the right answer path. "Change N" points at the
  numbered change at the end of this document.
- Queries are written as a reader would type or say them.

## 1. Survival Medicine

| Scenario | Path | Result |
|---|---|---|
| "How long can a tourniquet stay on?" | Retrieval returns an ATP 4-02.11 passage (under 2 hours to convert) and an FM 21-76 passage (loosen every 15 minutes). The entry's block cites the first with `supports` and the second with `diverges`. | Holds for the entry. In chat, retrieval alone has no block to mark the older passage, so the answer needs the volume's shelf role to demote it. Change 1. |
| "My toddler is choking." | Profile household includes `child`; passages from IFRC 2020 infant and child sections carry `audience: child`. Retrieval filters by scope and ranks child passages first. | Holds. The adult passage must still return when no child passage exists; ranking, not exclusion. Stated in change 6. |
| "What dose of ibuprofen?" | NHS Medicines A to Z pages under OGL, cut as `table_row` passages. The dose values need units and the profile's unit setting. | Passages have no structured values. Change 2. |
| "I am on a boat, three days from a port, and someone has a fever." | Activity `boating` pulls the MCA Ship Captain's Medical Guide. Entry `medicine/fever` links `next_step` to the maritime volume's nursing section. | Holds through pull rules and `entry_links`. |

## 2. Shelter

| Scenario | Path | Result |
|---|---|---|
| "How cold will it get tonight?" | Profile region and the current month select a climate-normals row for the nearest station. | Normals are a dataset volume. A page per station and a `table_row` passage per month works only if the passage carries the values as data. Change 2. |
| "Is my tent site safe in this wind?" | USAP field manual passages (deadman anchors, snow walls) carry scope terrain `mountain` and months of winter. Profile terrain or location selects them. | Holds. |
| "Sheltering at home during a storm, with a generator." | Ready.gov shelter page and the carbon-monoxide rule (20 feet from openings) sit on both the shelter and hazards shelves. | Holds: one volume on two shelves through `shelf_volume`, passages carrying topic codes from both. |

## 3. Fire

| Scenario | Path | Result |
|---|---|---|
| "Can I have a campfire today?" | The USFS visitor page explains restriction stages. The current stage for the reader's forest changes weekly and is published live. | The schema carries only static pages. The answer must say "as of the pack date" offline and read a live endpoint online. Change 3. |
| "Stove inside the tent?" | Universal carbon-monoxide passages (ATSDR, CDC release) with kind `warning`. | Holds. |
| "How do I put a fire out?" | NPS extinguishing procedure as `procedure_step` passages; entry `fire/extinguish` cites each step. | Holds. |

## 4. Water

| Scenario | Path | Result |
|---|---|---|
| "How much bleach for five gallons?" | CDC and EPA dose tables as `table_row` passages, values in per-gallon and per-litre forms. Profile units decide which to show. | Needs structured values with units on the passage. Change 2. |
| "Is the river safe to cross?" | NPS turn-back rules as passages; the USGS gauge reading for the nearest site is live data. | Same as the campfire case. Change 3. Offline, the rules alone answer. |
| "Agua potable, cómo hervir" | Profile languages include `es`; no Spanish volume is carried. Retrieval finds the English passage. | Holds with a stated behaviour: the model answers in the reader's language and quotes the English passage verbatim. Change 8 records the rule. |

## 5. Food

| Scenario | Path | Result |
|---|---|---|
| "Can I eat this mushroom?" | The product gives identification references and never an edibility verdict. Nothing in the schema marks the topic as verdict-free. | Topic codes need an answer policy. Change 4. |
| "Is trapping legal here?" | 36 CFR 2.1 is universal for national parks; state law is regional and changes yearly. | Scope handles the region; currency needs the freshness marker of change 3, set to `seasonal`. |
| "How long does rice keep?" | FoodKeeper dataset as `table_row` passages with the shelf-life values. | Change 2. |
| "Power is out, is the freezer food safe?" | FSIS outage rules sit on food and hazards shelves. | Holds. |

## 6. Poisonous Plants

| Scenario | Path | Result |
|---|---|---|
| "My kid ate a red berry." | Audience `child` passages first; the poison-centre number is country-specific (1-800-222-1222 in the US, 13 11 26 in Australia). Profile country selects the passage. | Holds when the profile has a country. With no country, a universal fallback passage (the WHO directory) must exist. Change 5. |
| "Dog chewed a lily." | Audience `pet`. The ASPCA list is link only, so no passage exists; the universal fallback is the poison-centre number. | Holds with change 5. The link-only volume appears through `entry_links`, never through a citation. Change 7. |
| "Rash after clearing brush." | FDA and NIOSH passages, scope universal. | Holds. |
| "Which plants here are poisonous?" | Pull rule `wa-plants` adds ARS Bulletin 415 for western states. | Holds. Outside the US, the same query falls back to Wikipedia species articles with scope by country. |

## 7. Dangerous Animals

| Scenario | Path | Result |
|---|---|---|
| "Snake bit me, what now?" | Yellow Book envenomation passages, universal; the "do not" list as `warning` passages ranked first. | Holds. |
| "Which ticks are in my county?" | The CDC county table keys on county FIPS. Scope has country and ISO 3166-2 region only. | Change 6 adds a county axis. |
| "Is this spider dangerous?" | Identification entry, species scope by region. | Holds. |
| "Bear outside the tent." | NPS encounter passages, terrain `mountain`, `forest`. | Holds. |

## 8. Tools and Cordage

| Scenario | Path | Result |
|---|---|---|
| "Show me the bowline step by step." | Procedure entry; each block cites a TC 3-97.61 step passage and a figure. The figures come from a Commons category where every file carries its own licence. | A figure has no licence of its own in the schema. Change 9. |
| "How much weight does paracord hold?" | MIL-C-5040H values as `table_row` with data. | Change 2. |
| "Sharpen an axe." | USFS An Ax to Grind procedure passages. | Holds. |

## 9. Direction Finding

| Scenario | Path | Result |
|---|---|---|
| "Which way is north, at night?" | Celestial entry. The method differs by hemisphere; scope has no hemisphere axis and country only implies it. | Change 6 adds hemisphere. |
| "What is the declination here?" | WMM is a model, computed from a coordinate and a date. Profile region gives no coordinate. | Change 10 adds a live location to the profile that the app may hold and never writes into a pack. |
| "I am lost." | USFS STOP and NPS Hike Smart passages, universal, kind `procedure_step`. | Holds. |

## 10. Signaling and Rescue

| Scenario | Path | Result |
|---|---|---|
| "What is the emergency number here?" | Country-scoped passages (911, 112, 000). | Holds with the universal fallback of change 5 (112 works on GSM phones worldwide, quoted from its source). |
| "I am hiking in Japan next month." | Profile country is US. Pull rules run on the profile, so Japanese volumes never arrive. | Change 10 adds trips to the profile; pull rules match trips as well as home. |
| "My PLB went off by accident." | NOAA SARSAT false-alert passage. | Holds. |

## 11. Environments

| Scenario | Path | Result |
|---|---|---|
| "What environment am I in?" | Profile climate derives from region. A state such as California spans several Köppen classes. | Change 6 makes climate a list, and location refines it when available. |
| "Is there avalanche danger today?" | Avalanche Handbook explains mechanism; today's danger is live and the open authority is link only. | Change 3 marks the entry `live`; the answer names the regional centre as a link. |
| "Will it storm this afternoon?" | The weather walk (existing engine) plus SKYWARN passages. | Holds. |

## 12. Man-Made Hazards

| Scenario | Path | Result |
|---|---|---|
| "Radiation alert, I have a baby." | Ready.gov sequence entry; FDA KI dosing as `table_row` by age with audience `infant`. | Holds with change 2 for the dose values. |
| "AQI is 180, should I go running?" | EPA AQI band table as `table_row` with data. | Change 2. |
| "Sealing a room for a chemical release." | Ready.gov steps, universal. | Holds. |

## Cross-cutting flows

| Scenario | Path | Result |
|---|---|---|
| Onboarding skipped entirely. | Profile at stock defaults; every scope filter passes universal items only. | Holds. Change 5 guarantees a universal answer exists per topic. |
| User moves from Washington to Arizona. | Pull rules re-evaluate; new volumes pull. The old regional volumes still match nothing. | `user_shelf` must exclude unmatched regional volumes and offer to remove them. Change 11. |
| Offline question, resolved a week later. | The learned volume's passages take the scope of the question's profile snapshot. | Holds; change 8 records the rule. |
| Yellow Book 2028 replaces 2026. | New volume id; entries cite 2026 passages. | Change 12 adds `superseded_by` on volume, and every entry citing a superseded volume returns to `draft`. |
| A reviewer rejects a page that approved entries cite. | Build refuses the citations. | Change 12 states that the citing entries return to `draft`. |
| An entry quotes a CC BY-SA passage next to a public-domain one. | The entry's own terms follow the strictest cited licence. | Change 13 derives `entry_terms`. |
| The question classifier picks the wrong shelf. | Topic filter returns nothing relevant. | Change 8: retrieval retries without the topic filter before declaring non-coverage. |

## Changes applied to library-schema.md

1. `search_index` derives an authority rank from `shelf_volume.role`; `archive` passages rank
   below `primary` and are quoted with the volume's edition.
2. `passage.data`: a json column of structured values with units, for `table_row` passages.
   Unit conversion happens at answer time from `profile.units`.
3. `volume.freshness` (`static`, `seasonal`, `live`) and `volume.live_source` (endpoint and
   field). An answer from a `seasonal` or `live` volume states the pack date offline and reads
   the endpoint online.
4. `topics.tsv` gains `policy` (`answer`, `reference_only`, `emergency_only`).
5. Coverage rule: for every topic code, at least one entry or passage with scope `universal`.
   The coverage table reports violations.
6. Scope gains `admin2` (county FIPS or national equivalent) and `hemisphere`; `climate` on the
   profile becomes a list. Audience scope ranks, never excludes.
7. `block_cites` may reference only passages of volumes with `carry = carry`. Link-only volumes
   reach the reader through `entry_links` with kind `on_shelf`.
8. Retrieval rules section: language fallback, topic-filter retry, learned-volume scope.
9. `figure` table with per-file licence, statement, url, and page reference.
10. Profile gains `location` (live, optional, never written to a pack) and `trips` (region and
    months). Scope matching uses location when present, otherwise profile; pull rules match
    home and trips.
11. `user_shelf` excludes regional volumes no rule matches and lists them for removal.
12. `volume.superseded_by`. Revised after review: dependents do not regress. Every citation
    pins an exact version, versions coexist, and a change adds dependents to a work list while
    their approved revision keeps serving (schema section 2.2, with `entry_revision`,
    `cited_by`, `work_list`, the observation log, and the provenance table).
13. `entry_terms` derived: the strictest licence among cited volumes, shown in the entry's
    source footer.
