"""Build a conservative official U.S. event calendar for the thesis autopsy.

Core cross-era evidence comes only from BLS year schedules and official FOMC
statement pages. BEA's current official machine-readable schedule is retained
as a supplemental 2025-2026 family because older years are not exposed by the
current endpoint. Fixed election/inauguration dates are date-only and cannot
enter exact-time windows.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "scheduled_events"
OUT = OUT_DIR / "official_us_events_2021_2026.json"
HEADERS = {"User-Agent": "Mozilla/5.0 research@example.com"}
EASTERN = ZoneInfo("US/Eastern")
UTC = timezone.utc
BLS_FAMILIES = {
    "Consumer Price Index": "cpi",
    "Employment Situation": "employment",
    "Job Openings and Labor Turnover Survey": "jolts",
    "Producer Price Index": "ppi",
}
FIXED_DATE_EVENTS = [
    ("2021-01-20", "us_inauguration", "Inauguration Day", "https://www.inaugural.senate.gov/"),
    ("2022-11-08", "us_election", "U.S. general election", "https://www.fec.gov/help-candidates-and-committees/dates-and-deadlines/2022-dates-and-deadlines/"),
    ("2024-11-05", "us_election", "U.S. general election", "https://www.fec.gov/help-candidates-and-committees/dates-and-deadlines/2024-dates-and-deadlines/"),
    ("2025-01-20", "us_inauguration", "Inauguration Day", "https://www.inaugural.senate.gov/"),
]


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get(url):
    last_error = None
    for attempt in range(3):
        response = requests.get(url, headers=HEADERS, timeout=60)
        if response.status_code == 200:
            return response.text
        last_error = RuntimeError(f"HTTP {response.status_code} for {url}")
        time.sleep(1.5 * (attempt + 1))
    raise last_error


def eastern_to_utc(date_text, time_text):
    local = datetime.strptime(f"{date_text} {time_text}", "%A, %B %d, %Y %I:%M %p")
    return local.replace(tzinfo=EASTERN).astimezone(UTC)


def build_bls():
    events = []
    sources = []
    for year in range(2021, 2027):
        url = f"https://www.bls.gov/schedule/{year}/home.htm"
        text = get(url)
        sources.append({"url": url, "sha256": sha256(text), "evidence": "official year schedule; all times Eastern"})
        soup = BeautifulSoup(text, "html.parser")
        for row in soup.select("table.release-list tr"):
            cells = row.find_all("td")
            if len(cells) != 3:
                continue
            release = " ".join(cells[2].stripped_strings)
            family = next((v for k, v in BLS_FAMILIES.items() if release.startswith(k)), None)
            if family is None:
                continue
            date_text = " ".join(cells[0].stripped_strings)
            time_text = " ".join(cells[1].stripped_strings)
            dt = eastern_to_utc(date_text, time_text)
            events.append({
                "timestamp_utc": dt.isoformat().replace("+00:00", "Z"),
                "date_local": dt.astimezone(EASTERN).date().isoformat(),
                "timezone": "US/Eastern", "family": "bls", "event_type": family,
                "name": release, "evidence": "scheduled_exact_utc",
                "known_in_advance": True, "source_url": url,
                "conversion": "IANA US/Eastern -> UTC",
            })
    return events, sources


def statement_timestamp(text, source_url):
    soup = BeautifulSoup(text, "html.parser")
    page_text = " | ".join(soup.stripped_strings)
    match = re.search(r"For release at\s+(\d{1,2}:\d{2})\s+p\.m\.\s+(EST|EDT)", page_text, re.I)
    date_match = re.search(r"Last Update:\s*([A-Z][a-z]+ \d{1,2}, \d{4})", page_text)
    if not match or not date_match:
        raise RuntimeError(f"official FOMC statement missing exact release time/date: {source_url}")
    local = datetime.strptime(f"{date_match.group(1)} {match.group(1)} PM", "%B %d, %Y %I:%M %p")
    offset = -4 if match.group(2).upper() == "EDT" else -5
    return (local.replace(tzinfo=UTC) - timedelta(hours=offset))


def build_fomc():
    calendar_url = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
    calendar_text = get(calendar_url)
    soup = BeautifulSoup(calendar_text, "html.parser")
    events = []
    sources = [{"url": calendar_url, "sha256": sha256(calendar_text), "evidence": "official historical meeting calendar"}]
    seen = set()
    for panel in soup.select("div.panel"):
        heading = panel.find(["h3", "h4"])
        if not heading or not re.search(r"202[1-6] FOMC Meetings", heading.get_text(" ", strip=True)):
            continue
        for meeting in panel.select("div.fomc-meeting"):
            statement = next((a for a in meeting.find_all("a", href=True) if "newsevents/pressreleases/monetary" in a["href"] and a.get_text(strip=True) == "HTML"), None)
            if statement is None:
                continue
            source_url = urljoin("https://www.federalreserve.gov", statement["href"])
            if source_url in seen:
                continue
            seen.add(source_url)
            page = get(source_url)
            dt = statement_timestamp(page, source_url)
            events.append({
                "timestamp_utc": dt.isoformat().replace("+00:00", "Z"),
                "date_local": dt.astimezone(EASTERN).date().isoformat(),
                "timezone": "EST/EDT from official statement", "family": "fomc",
                "event_type": "fomc_statement", "name": "FOMC monetary policy statement",
                "evidence": "scheduled_exact_utc", "known_in_advance": True,
                "source_url": source_url, "calendar_url": calendar_url,
                "conversion": "explicit official release clock abbreviation -> UTC",
            })
            sources.append({"url": source_url, "sha256": sha256(page), "evidence": "official statement gives exact release clock"})
    return events, sources


def build_bea_current():
    url = "https://apps.bea.gov/api/signup/release_dates.json"
    text = get(url)
    data = json.loads(text)
    events = []
    for release_name in ("Gross Domestic Product", "Personal Income and Outlays"):
        for stamp in data[release_name]["release_dates"]:
            year = int(stamp[:4])
            if year not in (2025, 2026):
                continue
            event_type = "gdp" if release_name == "Gross Domestic Product" else "pce"
            events.append({
                "timestamp_utc": stamp,
                "date_local": datetime.fromisoformat(stamp).astimezone(EASTERN).date().isoformat(),
                "timezone": "UTC from BEA API", "family": "bea",
                "event_type": event_type, "name": release_name,
                "evidence": "scheduled_exact_utc_current_api",
                "known_in_advance": True, "source_url": url,
                "conversion": "none; API timestamp is UTC",
            })
    return events, [{"url": url, "sha256": sha256(text), "evidence": "official current API; only 2025-2026 rows exposed"}]


def build_fixed_dates():
    return ([{
        "timestamp_utc": None, "date_utc": date,
        "family": "political", "event_type": event_type, "name": name,
        "evidence": "fixed_date_only", "known_in_advance": True,
        "source_url": source,
        "conversion": "not applicable; excluded from exact-time windows",
    } for date, event_type, name, source in FIXED_DATE_EVENTS], [])


def main():
    bls, bls_sources = build_bls()
    fomc, fomc_sources = build_fomc()
    bea, bea_sources = build_bea_current()
    fixed, _ = build_fixed_dates()
    result = {
        "schema": "official_us_scheduled_events_v1",
        "built_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "scope": {
            "exact_cross_era": ["bls", "fomc"],
            "date_only": ["political"],
            "supplemental_current_api": ["bea"],
        },
        "policy": {
            "hindsight_reaction_labels": False,
            "surprise_events": False,
            "exact_time_requires_official_scheduled_timestamp": True,
        },
        "events": sorted(
            bls + fomc + bea + fixed,
            key=lambda e: (e.get("timestamp_utc") or e.get("date_utc") or "", e["family"], e["event_type"]),
        ),
        "sources": bls_sources + fomc_sources + bea_sources,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    counts = {}
    for event in result["events"]:
        key = f"{event['family']}:{event['evidence']}"
        counts[key] = counts.get(key, 0) + 1
    print(f"wrote {OUT} ({len(result['events'])} events)")
    for key, count in sorted(counts.items()):
        print(f"  {key}: {count}")


if __name__ == "__main__":
    main()

