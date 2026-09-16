from __future__ import annotations

_NA_CLASS = frozenset({"", "na", "null", "none"})


def parse_epoch(raw: str) -> int | None:
    s = str(raw).replace(",", "").strip()
    if s.lower() in _NA_CLASS:
        return None
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


def parse_delay_reason(raw: str) -> str:
    s = str(raw).strip()
    return "UNKNOWN" if s.lower() in _NA_CLASS else s.upper()


def guard_na(raw: str) -> str | None:
    s = str(raw).strip()
    return None if s.lower() in _NA_CLASS else s
