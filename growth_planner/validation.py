"""Small validation functions shared by browser, API, and desktop forms."""

from datetime import date, datetime
import math
import re


def required(value, label, maximum=200):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + " is required.")
    value = value.strip()
    if len(value) > maximum:
        raise ValueError(f"{label} must have at most {maximum} characters.")
    return value


def identifier(value, label="ID"):
    value = required(value, label, 40).upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{1,39}", value):
        raise ValueError(label + " must have 2–40 letters, digits, underscores or hyphens.")
    return value


def email_address(value):
    value = required(value, "Email", 254)
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        raise ValueError("Enter a valid email address.")
    return value


def number(value, label, minimum=0, maximum=100000):
    if isinstance(value, bool):
        raise ValueError(label + " must be a number.")
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(label + " must be a number.")
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}.")
    return value


def calendar_date(value, label="Date"):
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError()
        return date.fromisoformat(value).isoformat()
    except (ValueError, TypeError):
        raise ValueError(label + " must use YYYY-MM-DD.")


def time_range(starts_at, ends_at):
    try:
        start = datetime.fromisoformat(starts_at)
        end = datetime.fromisoformat(ends_at)
        if start.tzinfo or end.tzinfo:
            raise ValueError()
        start = start.replace(second=0, microsecond=0)
        end = end.replace(second=0, microsecond=0)
    except (ValueError, TypeError):
        raise ValueError("Use local date and time, for example 2026-10-25T14:30.")
    if end <= start:
        raise ValueError("End time must be after start time.")
    return start.isoformat(timespec="minutes"), end.isoformat(timespec="minutes")


def tags(value):
    if not isinstance(value, str) or len(value) > 2000:
        raise ValueError("Enter tags as text separated by commas or | (maximum 2000 characters).")
    return "|".join(sorted({part.strip().lower() for part in re.split(r"[,|]", value) if part.strip()}))
