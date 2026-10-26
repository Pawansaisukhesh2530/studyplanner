"""Read public holiday data. Never replace missing API data with sample dates."""

import json
import re
from urllib.error import URLError
from urllib.request import Request, urlopen

from growth_planner.validation import calendar_date


BASE_URL = "https://date.nager.at/api/v3"


def get_json(path):
    request = Request(BASE_URL + path, headers={"Accept": "application/json", "User-Agent": "StudentGrowthPlanner/2"})
    try:
        with urlopen(request, timeout=10) as response:
            return json.load(response)
    except (URLError, OSError, ValueError):
        raise ValueError("Holiday service is unavailable or returned unreadable data. Your saved schedule is unchanged.")


def fetch_holidays(country_code, year, subdivision=""):
    if not isinstance(country_code, str) or not re.fullmatch(r"[A-Za-z]{2}", country_code):
        raise ValueError("Use a two-letter country code, such as IN.")
    country_code = country_code.upper()
    if isinstance(year, bool) or not isinstance(year, int) or not 2000 <= year <= 2100:
        raise ValueError("Choose a year between 2000 and 2100.")
    if subdivision and not re.fullmatch(r"[A-Za-z]{2}-[A-Za-z0-9]{1,5}", subdivision):
        raise ValueError("Use a subdivision code such as IN-KA, or leave it empty.")
    countries = get_json("/AvailableCountries")
    if not isinstance(countries, list) or not all(isinstance(row, dict) for row in countries):
        raise ValueError("Holiday service returned an unexpected country list.")
    if country_code not in {row.get("countryCode") for row in countries}:
        raise ValueError("This holiday service does not currently support " + country_code + ". Check your college's official holiday calendar instead.")
    response = get_json(f"/PublicHolidays/{year}/{country_code}")
    if not isinstance(response, list):
        raise ValueError("Holiday service returned an unexpected holiday list.")
    result = []
    try:
        for row in response:
            day = calendar_date(row["date"])
            if not isinstance(row["name"], str) or not isinstance(row["global"], bool):
                raise ValueError()
            regions = row.get("counties") or []
            if subdivision and not row["global"] and subdivision.upper() not in regions:
                continue
            result.append({"date": day, "name": row["name"], "scope": "National" if row["global"] else ", ".join(regions), "types": ", ".join(row.get("types", []))})
    except (KeyError, TypeError, ValueError, AttributeError):
        raise ValueError("Holiday service returned unexpected holiday fields.")
    return result
