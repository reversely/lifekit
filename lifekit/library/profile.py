"""The household profile and the pull rules it triggers.

docs/content/library-schema.md 1.7 fixes the onboarding questions; on a box the
answers live in one row of library.sqlite. A pull rule (packs/pull_rules.tsv)
maps answers to a seeded question the loop works, so a match stages a document
for the owner's verdict rather than pulling one blind. Rules are data: a new
region or activity needs rows, not code.

    packs/pull_rules.tsv columns: id, predicate, question, reason
    predicate: json, a conjunction over profile columns, each a list of accepted
    values; {"activities": ["hunting"]} matches when hunting is among the answers.
    question may contain {region}, {country}, {trip} which fill from the profile.
"""

import csv
import json
from datetime import datetime, timezone

from lifekit.packs import LOCAL_PACKS

RULES = LOCAL_PACKS / "pull_rules.tsv"
COLUMNS = ("country", "region", "terrain", "activities", "household", "trips")
LIST_COLUMNS = ("terrain", "activities", "household", "trips")

# The onboarding questions and their options, one place for both the API and the app.
QUESTIONS = [
    {"key": "country", "ask": "Where do you live?", "multi": False,
     "options": [("US", "United States"), ("CA", "Canada"), ("GB", "United Kingdom"), ("AU", "Australia"), ("other", "Somewhere else")]},
    {"key": "region", "ask": "Which region?", "multi": False, "depends": "country",
     "options": []},  # filled per country below
    {"key": "terrain", "ask": "What is around you?", "multi": True,
     "options": [("forest", "Forest"), ("mountains", "Mountains"), ("desert", "Desert"), ("coast", "Coast or sea"),
                 ("river", "Rivers and lakes"), ("snow", "Snow in winter"), ("city", "City")]},
    {"key": "activities", "ask": "What do you do outdoors?", "multi": True,
     "options": [("home", "Mostly at home"), ("hiking", "Hiking"), ("camping", "Camping"), ("hunting", "Hunting"),
                 ("fishing", "Fishing"), ("boating", "Boating"), ("climbing", "Climbing"), ("cycling", "Cycling"), ("foraging", "Foraging")]},
    {"key": "household", "ask": "Who is in your household?", "multi": True,
     "options": [("adult", "Adults"), ("children", "Children"), ("elderly", "Older adults"), ("pets", "Pets"), ("chronic", "Someone with a chronic condition")]},
    {"key": "trips", "ask": "Planning a trip?", "multi": True,
     "options": [("tropics", "Tropics"), ("arctic", "Arctic or high latitude"), ("desert", "Desert"), ("high-altitude", "High altitude"),
                 ("sea", "Open sea"), ("abroad", "Another country")]},
]
REGIONS = {
    "US": [("US-WA", "Washington"), ("US-OR", "Oregon"), ("US-CA", "California"), ("US-AK", "Alaska"), ("US-AZ", "Arizona"),
           ("US-CO", "Colorado"), ("US-TX", "Texas"), ("US-FL", "Florida"), ("US-NY", "New York"), ("US-other", "Another state")],
    "CA": [("CA-BC", "British Columbia"), ("CA-AB", "Alberta"), ("CA-ON", "Ontario"), ("CA-QC", "Quebec"), ("CA-other", "Another province")],
    "GB": [("GB-ENG", "England"), ("GB-SCT", "Scotland"), ("GB-WLS", "Wales"), ("GB-NIR", "Northern Ireland")],
    "AU": [("AU-QLD", "Queensland"), ("AU-NSW", "New South Wales"), ("AU-VIC", "Victoria"), ("AU-WA", "Western Australia"), ("AU-other", "Another state")],
}
REGION_NAMES = {code: name for rows in REGIONS.values() for code, name in rows}
COUNTRY_NAMES = {code: name for code, name in QUESTIONS[0]["options"]}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get(db) -> dict:
    row = db.execute("SELECT country, region, terrain, activities, household, trips, updated_at FROM profile WHERE id = 1").fetchone()
    if row is None:
        return {"country": None, "region": None, "terrain": [], "activities": ["home"], "household": ["adult"], "trips": [], "updated_at": None}
    out = dict(zip(COLUMNS + ("updated_at",), row))
    for key in LIST_COLUMNS:
        out[key] = json.loads(out[key] or "[]")
    return out


def save(db, answers: dict) -> dict:
    current = get(db)
    for key in COLUMNS:
        if key in answers:
            current[key] = answers[key]
    db.execute(
        "INSERT OR REPLACE INTO profile (id, country, region, terrain, activities, household, trips, updated_at) VALUES (1,?,?,?,?,?,?,?)",
        (current["country"], current["region"], *(json.dumps(current[k]) for k in LIST_COLUMNS), _now()),
    )
    db.commit()
    return get(db)


def questions(profile: dict) -> list[dict]:
    """The onboarding questions with options, the region list narrowed by country."""
    out = []
    for q in QUESTIONS:
        options = q["options"]
        if q["key"] == "region":
            options = REGIONS.get(profile.get("country") or "", [])
            if not options:
                continue
        out.append({"key": q["key"], "ask": q["ask"], "multi": q["multi"],
                    "options": [{"value": v, "label": l} for v, l in options]})
    return out


def read_rules() -> list[dict]:
    if not RULES.exists():
        return []
    with RULES.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def matches(predicate: dict, profile: dict) -> bool:
    for key, accepted in predicate.items():
        value = profile.get(key)
        values = value if isinstance(value, list) else [value]
        if not any(v in accepted for v in values):
            return False
    return True


def _fill(text: str, profile: dict) -> str:
    region = REGION_NAMES.get(profile.get("region") or "", profile.get("region") or "")
    country = COUNTRY_NAMES.get(profile.get("country") or "", profile.get("country") or "")
    trip = ", ".join(profile.get("trips") or [])
    return text.replace("{region}", region).replace("{country}", country).replace("{trip}", trip)


def evaluate(db, profile: dict) -> list[dict]:
    """Seed one stored question per matching rule not yet seeded. Returns what was seeded."""
    from .loop import store_question

    seen = {r[0] for r in db.execute("SELECT origin FROM question WHERE origin != 'asked'")}
    seeded = []
    for rule in read_rules():
        origin = f"rule:{rule['id']}"
        if origin in seen:
            continue
        try:
            predicate = json.loads(rule["predicate"])
        except json.JSONDecodeError:
            continue
        if not matches(predicate, profile):
            continue
        text = _fill(rule["question"], profile)
        qid = store_question(db, text, profile, origin=origin, topic=None, wanted=_fill(rule.get("reason", ""), profile) or None)
        seeded.append({"id": qid, "text": text, "reason": _fill(rule.get("reason", ""), profile), "rule": rule["id"]})
    return seeded


def describe(profile: dict) -> str:
    """One line for the Library directory: where and what."""
    parts = []
    if profile.get("region"):
        parts.append(REGION_NAMES.get(profile["region"], profile["region"]))
    elif profile.get("country"):
        parts.append(COUNTRY_NAMES.get(profile["country"], profile["country"]))
    acts = [a for a in profile.get("activities") or [] if a != "home"]
    if acts:
        parts.append(", ".join(acts))
    return "; ".join(parts)
