import pytest

from scrapers.common.ids import slugify
from scrapers.common.mu import split_classes
from scrapers.common.parsing import (
    find_updated_date, parse_bool, parse_date, parse_duration_seconds, parse_int, parse_number, parse_range,
)


@pytest.mark.parametrize("text, expected", [("1,234", 1234), ("+15%", 15), ("1.5", 1.5), ("abc", None), (None, None)])
def test_parse_number(text, expected):
    assert parse_number(text) == expected


def test_parse_int_rejeita_fracao():
    assert parse_int("12") == 12
    assert parse_int("12.5") is None


@pytest.mark.parametrize("text, expected", [
    ("50 ~ 60", (50, 60)), ("50-60", (50, 60)), ("1,000 to 1,200", (1000, 1200)), ("75", (75, 75)), ("", (None, None)),
])
def test_parse_range(text, expected):
    assert parse_range(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("10 sec", 10), ("10s", 10), ("2 min 30 sec", 150), ("1 minute", 60), ("00:01:30", 90), ("01:30", 90),
    ("1 hour", 3600), ("45", 45), (None, None),
])
def test_parse_duration_seconds(text, expected):
    assert parse_duration_seconds(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("Data updated May 03, 2019", "2019-05-03"), ("updated: Sept 1st 2024", "2024-09-01"),
    ("2025-05-10", "2025-05-10"), ("Feb 30, 2020", None), ("sem data", None),
])
def test_parse_date(text, expected):
    assert parse_date(text) == expected


def test_find_updated_date_olha_a_linha_seguinte():
    assert find_updated_date(["Goblin", "Last updated:", "May 03, 2019"]) == "2019-05-03"
    assert find_updated_date(["May 03, 2019"]) is None  # data sem "updated" não conta


def test_parse_bool():
    assert (parse_bool("Yes"), parse_bool("x"), parse_bool("talvez")) == (True, False, None)


def test_slugify():
    assert slugify("Dragon Armor") == "dragon-armor"
    assert slugify("Wings of Satan +1") == "wings-of-satan-1"
    assert slugify("Áxe Warrior's") == "axe-warrior-s"


def test_split_classes():
    assert split_classes("Dark Wizard, Soul Master / DK") == ["Dark Wizard", "Soul Master", "Dark Knight"]
    assert split_classes("dark knight blade knight") == ["Dark Knight", "Blade Knight"]
    assert split_classes("Classe Nova") == ["Classe Nova"]
