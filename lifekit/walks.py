"""Walk sessions and the interview engine.

A walk follows the LifeKit session shape: a short clip, questions with
tappable options, then a result that gives the implication first, the quoted
source line second, and a deep link into the source third.

Data transcribed from flux app/src/data/vss.ts. Findings hold priority order:
the first whose `when` answers all match fires. The engine asks a question
only while its answer could still change which finding fires.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Source:
    id: str
    title: str
    url: str
    licence: str


@dataclass(frozen=True)
class Question:
    id: str
    ask: str
    options: tuple[str, ...]
    because: str


@dataclass(frozen=True)
class Finding:
    when: dict[str, str]
    means: str
    quote: str
    source: str
    image: str | None = None
    wait: int | None = None
    wait_label: str | None = None


@dataclass(frozen=True)
class Session:
    id: str
    title: str
    capture: str
    clip_seconds: int
    questions: tuple[Question, ...]
    findings: tuple[Finding, ...]
    fallback: Finding
    sources: tuple[Source, ...]

    def source_by_id(self, source_id: str) -> Source | None:
        return next((s for s in self.sources if s.id == source_id), None)


def _possible(finding: Finding, answers: dict[str, str]) -> bool:
    """A finding stays possible while no given answer contradicts it."""
    return all(answers.get(q, a) == a for q, a in finding.when.items())


def open_questions(session: Session, answers: dict[str, str]) -> list[str]:
    """Question ids whose answers could still change which finding fires.

    Walk findings in priority order. A possible finding with gaps keeps its
    gaps open; the first possible finding with no gaps fires regardless of
    later answers, so collection stops there.
    """
    opens: list[str] = []
    for finding in session.findings:
        if not _possible(finding, answers):
            continue
        gaps = [q for q in finding.when if q not in answers]
        if not gaps:
            break
        opens.extend(gaps)
    order = {q.id: i for i, q in enumerate(session.questions)}
    return sorted(set(opens), key=order.__getitem__)


def next_question(session: Session, answers: dict[str, str]) -> Question | None:
    opens = open_questions(session, answers)
    if not opens:
        return None
    return next(q for q in session.questions if q.id == opens[0])


def finding_for(session: Session, answers: dict[str, str]) -> Finding:
    """The first finding whose conditions all match, else the fallback."""
    for finding in session.findings:
        if all(answers.get(q) == a for q, a in finding.when.items()):
            return finding
    return session.fallback


FAA = Source(
    id="faa-phak-12",
    title="FAA Pilot Handbook, chapter 12, Weather Theory",
    url="https://www.faa.gov/sites/faa.gov/files/14_phak_ch12.pdf#page=5",
    licence="Public domain, US government work",
)

FAA_CB = Source(
    id="faa-phak-12-cb",
    title="FAA Pilot Handbook, chapter 12, thunderstorms",
    url="https://www.faa.gov/sites/faa.gov/files/14_phak_ch12.pdf#page=16",
    licence="Public domain, US government work",
)

NOAA = Source(
    id="noaa-ten-clouds",
    title="NOAA JetStream, the ten basic clouds",
    url="https://www.noaa.gov/jetstream/clouds/ten-basic-clouds",
    licence="Public domain, US government work",
)

FM18 = Source(
    id="fm21-76-ch18",
    title="FM 21-76 Survival, chapter 18, field-expedient direction finding",
    url="https://commons.wikimedia.org/wiki/File:FM_21-76_Survival_June_1992.pdf?page=185",
    licence="Public domain, US government work",
)

WEATHER = Session(
    id="weather",
    title="What the weather will do",
    capture="Pan slowly across the sky, horizon to overhead.",
    clip_seconds=4,
    questions=(
        Question(
            id="trend",
            ask="Sky thickening or clearing since you last looked?",
            options=("thickening", "clearing", "no change"),
            because="Direction of change matters more than the sky right now.",
        ),
        Question(
            id="wind",
            ask="Wind picked up or shifted?",
            options=("picked up", "shifted", "steady"),
            because="A shift often arrives before the weather does.",
        ),
        Question(
            id="halo",
            ask="Ring around the sun or moon?",
            options=("yes", "no"),
            because="A halo means ice cloud thickening overhead.",
        ),
        Question(
            id="towers",
            ask="Any cloud growing tall and hard-edged?",
            options=("yes", "no"),
            because="Vertical growth is the thunderstorm signal.",
        ),
    ),
    findings=(
        Finding(
            when={"towers": "yes"},
            means="Thunderstorm building. Get off ridges and open water, away from lone trees.",
            quote=(
                "Cumulonimbus clouds contain large amounts of moisture and unstable air "
                "and usually produce hazardous weather phenomena, such as lightning, "
                "hail, tornadoes, gusty winds, and wind shear."
            ),
            source=FAA_CB.id,
        ),
        Finding(
            when={"halo": "yes", "trend": "thickening"},
            means="Rain or snow likely within a day. Set up shelter and water while it is dry.",
            quote=(
                "Cirrostratus ... is distinguished by a halo phenomena nearly always "
                "produced around the Sun or Moon shining through a layer of cirrostratus."
            ),
            source=NOAA.id,
        ),
        Finding(
            when={"trend": "thickening", "wind": "shifted"},
            means="Front arriving. Expect wind and rain within hours.",
            quote=(
                "Conversely, decreasing or rapidly falling pressure usually indicates "
                "approaching bad weather and, possibly, severe storms."
            ),
            source=FAA.id,
        ),
        Finding(
            when={"trend": "clearing"},
            means="Improving. Good window for travel or drying gear.",
            quote=(
                "For example, tracking a pattern of rising pressure at a single weather "
                "station generally indicates the approach of fair weather."
            ),
            source=FAA.id,
        ),
    ),
    fallback=Finding(
        when={},
        means=(
            "No strong signal. Watch for thickening cloud or a wind shift, "
            "and check again in an hour."
        ),
        quote="Clouds in this family create low ceilings, hamper visibility, and can change rapidly.",
        source=FAA.id,
    ),
    sources=(FAA, FAA_CB, NOAA),
)

CELESTIAL = Session(
    id="celestial",
    title="Find your direction",
    capture="Hold steady on the clearest part of the sky for a few seconds.",
    clip_seconds=5,
    questions=(
        Question(
            id="time",
            ask="Day or night?",
            options=("night", "day"),
            because="Stars by night, shadows by day.",
        ),
        Question(
            id="hemisphere",
            ask="North or south of the equator?",
            options=("north", "south", "not sure"),
            because="The method changes at the equator.",
        ),
        Question(
            id="seen",
            ask="What can you pick out?",
            options=("big dipper", "cassiopeia", "southern cross", "nothing yet"),
            because="Each shape points a different way.",
        ),
    ),
    findings=(
        Finding(
            when={"time": "night", "seen": "big dipper"},
            means=(
                "The two stars at the end of the cup point at the North Star, about "
                "five times their spacing. Face it: that is north."
            ),
            quote=(
                "The North Star is the last star of the Big Dipper handle. The two "
                "stars at the end of the Big Dipper bucket point to it."
            ),
            source=FM18.id,
            image="sky-north-star-big-dipper-and-cassiopeia.jpg",
        ),
        Finding(
            when={"time": "night", "seen": "cassiopeia"},
            means=(
                "Cassiopeia sits opposite the Big Dipper across the North Star. "
                "The middle star of its W points roughly north."
            ),
            quote="Cassiopeia has five stars that form a shape like a lopsided M or W on its side.",
            source=FM18.id,
            image="sky-north-star-big-dipper-and-cassiopeia.jpg",
        ),
        Finding(
            when={"time": "night", "seen": "southern cross"},
            means=(
                "Run the long axis of the cross out about four and a half times its "
                "length. That point is south."
            ),
            quote="The Southern Cross ... an imaginary line ... will point toward the south.",
            source=FM18.id,
            image="sky-southern-cross.jpg",
        ),
        Finding(
            when={"time": "day"},
            means=(
                "Push a stick upright. Mark the shadow tip now, wait, then mark it "
                "again. First mark is west, second is east, and you are facing north "
                "with west on your left."
            ),
            wait=900,
            wait_label="Mark the shadow tip again, then stand with the first mark on your left.",
            quote=(
                "The shadow-tip method ... the first mark is always west and the "
                "second mark is always east."
            ),
            source=FM18.id,
            image="sky-shadow-tip-method.gif",
        ),
    ),
    fallback=Finding(
        when={},
        means="Nothing to sight yet. Wait for a clear patch, or use a shadow once the sun is out.",
        quote=(
            "The shadow-tip method ... the first mark is always west and the "
            "second mark is always east."
        ),
        source=FM18.id,
        image="sky-shadow-tip-method.gif",
    ),
    sources=(FM18,),
)

SESSIONS: tuple[Session, ...] = (WEATHER, CELESTIAL)


def session_by_id(session_id: str) -> Session | None:
    return next((s for s in SESSIONS if s.id == session_id), None)
