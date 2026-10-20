"""Conversão de textos de página em números, faixas, durações e datas."""
from __future__ import annotations

import re
from datetime import date

_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
_RANGE = re.compile(r"(\d[\d,]*)\s*(?:~|-|–|—|to)\s*(\d[\d,]*)")
_CLOCK = re.compile(r"\b(?:(\d+):)?(\d{1,2}):(\d{2})\b")
_DURATION_PART = re.compile(
    r"(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|minutes?|mins?|m|seconds?|secs?|s)\b", re.IGNORECASE
)
_MONTH_DATE = re.compile(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b")
_ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def parse_number(text: str | None) -> int | float | None:
    """Primeiro número do texto. Vírgula é separador de milhar: '1,234' -> 1234."""
    if not text:
        return None
    match = _NUMBER.search(text)
    if not match:
        return None
    raw = match.group().replace(",", "")
    return float(raw) if "." in raw else int(raw)


def parse_int(text: str | None) -> int | None:
    value = parse_number(text)
    if value is None or (isinstance(value, float) and not value.is_integer()):
        return None
    return int(value)


def parse_range(text: str | None) -> tuple[int | None, int | None]:
    """'50 ~ 60' -> (50, 60). Valor único vira (n, n)."""
    if not text:
        return None, None
    match = _RANGE.search(text)
    if match:
        low, high = (int(g.replace(",", "")) for g in match.groups())
        return min(low, high), max(low, high)
    value = parse_int(text)
    return value, value


def parse_duration_seconds(text: str | None) -> int | None:
    """'10 sec' -> 10, '2 min 30 s' -> 150, '00:01:30' -> 90. Número puro é tratado como segundos."""
    if not text:
        return None
    clock = _CLOCK.search(text)
    if clock:
        hours, minutes, seconds = (int(g) if g else 0 for g in clock.groups())
        return hours * 3600 + minutes * 60 + seconds
    parts = _DURATION_PART.findall(text)
    if parts:
        total = 0.0
        for value, unit in parts:
            unit = unit.lower()
            total += float(value) * (3600 if unit.startswith("h") else 60 if unit.startswith("m") else 1)
        return int(round(total))
    return parse_int(text)


def parse_date(text: str | None) -> str | None:
    """Data em ISO 8601 ('May 03, 2019' -> '2019-05-03') ou None."""
    if not text:
        return None
    for match in _MONTH_DATE.finditer(text):
        month = _MONTHS.get(match.group(1)[:3].lower())
        if month:
            try:
                return date(int(match.group(3)), month, int(match.group(2))).isoformat()
            except ValueError:
                continue
    match = _ISO_DATE.search(text)
    if match:
        try:
            return date(*(int(g) for g in match.groups())).isoformat()
        except ValueError:
            return None
    return None


def find_updated_date(lines: list[str]) -> str | None:
    """Procura 'updated ... <data>' (ex.: 'Data updated May 03, 2019') nas linhas da página."""
    for i, line in enumerate(lines):
        if "updated" in line.lower():
            found = parse_date(line) or (parse_date(lines[i + 1]) if i + 1 < len(lines) else None)
            if found:
                return found
    return None


TRUTHY = {"yes", "y", "o", "true", "available", "possible", "✓", "✔", "v", "1", "ok"}
FALSY = {"no", "n", "x", "false", "none", "-", "✗", "✘", "0", "n/a", "na", "not available"}


def parse_bool(text: str | None) -> bool | None:
    if text is None:
        return None
    value = text.strip().lower().rstrip(".")
    if value in TRUTHY:
        return True
    if value in FALSY:
        return False
    return None
