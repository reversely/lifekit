from lifekit import walks
from lifekit.walks import CELESTIAL, WEATHER, finding_for, next_question, open_questions


def run_interview(session, scripted):
    """Answer each question from the scripted map until the walk settles."""
    answers = {}
    asked = []
    while (question := next_question(session, answers)) is not None:
        asked.append(question.id)
        answers[question.id] = scripted[question.id]
    return asked, finding_for(session, answers)


def test_every_weather_finding_reachable():
    for finding in WEATHER.findings:
        assert finding_for(WEATHER, dict(finding.when)) is finding


def test_weather_fallback_when_nothing_matches():
    answers = {"trend": "no change", "wind": "steady", "halo": "no", "towers": "no"}
    assert finding_for(WEATHER, answers) is WEATHER.fallback


def test_clearing_sky_skips_settled_questions():
    scripted = {"trend": "clearing", "towers": "no"}
    asked, finding = run_interview(WEATHER, scripted)
    assert asked == ["trend", "towers"]
    assert finding.means.startswith("Improving")


def test_towers_outrank_clearing():
    scripted = {"trend": "clearing", "towers": "yes"}
    _, finding = run_interview(WEATHER, scripted)
    assert finding is WEATHER.findings[0]


def test_daytime_settles_after_one_answer():
    scripted = {"time": "day"}
    asked, finding = run_interview(CELESTIAL, scripted)
    assert asked == ["time"]
    assert finding.wait == 900


def test_hemisphere_never_asked():
    assert "hemisphere" not in open_questions(CELESTIAL, {})
    assert "hemisphere" not in open_questions(CELESTIAL, {"time": "night"})


def test_night_dipper_walk():
    scripted = {"time": "night", "seen": "big dipper"}
    asked, finding = run_interview(CELESTIAL, scripted)
    assert asked == ["time", "seen"]
    assert "North Star" in finding.quote


def test_exhausted_interview_falls_back():
    scripted = {"time": "night", "seen": "nothing yet"}
    _, finding = run_interview(CELESTIAL, scripted)
    assert finding is CELESTIAL.fallback


def test_sessions_registered():
    assert walks.session_by_id("weather") is WEATHER
    assert walks.session_by_id("celestial") is CELESTIAL
