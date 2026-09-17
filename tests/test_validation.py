"""Input handling: ids, paths, sections, licences (#35, #32)."""

import pytest

from lifekit.library import online_retrieval as r


def test_ids_are_lowercase_letters_digits_hyphens():
    assert r.valid_id("bee-sting")
    assert r.valid_id("wikipedia-first-aid-kit")
    assert not r.valid_id("../etc")
    assert not r.valid_id("a b")
    assert not r.valid_id("A")
    assert not r.valid_id("x" * 90)


def test_volume_dir_refuses_escapes():
    with pytest.raises(ValueError):
        r.volume_dir("../../etc")
    with pytest.raises(ValueError):
        r.volume_dir("has/slash")


def test_slug_is_valid_id():
    assert r.valid_id(r.slug("Frostbite (2006 film)"))
    assert r.slug("Wildland–urban interface") == "wildland-urban-interface"


def test_refused_licences():
    assert r.licence_allowed("CC-BY-SA-4.0")
    assert not r.licence_allowed("CC-BY-ND-4.0")
    assert not r.licence_allowed("All rights reserved")
    assert not r.licence_allowed("")
