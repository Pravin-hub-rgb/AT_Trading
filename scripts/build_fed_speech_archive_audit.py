"""Audit official Federal Reserve Powell speech/testimony archives.

The annual Fed pages provide event dates and official event URLs, but not a
historical advance-publication timestamp. Therefore these rows are recorded as
archive-date-only and are explicitly excluded from the pre-announced event
study. FOMC statement exact timestamps are already covered by Stage 22; press
conference time is not guessed when the official page does not expose it.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "scheduled_events"
OUT = OUT_DIR / "official_fed_speech_archive_audit_2021_2026.json"
HEADERS = {"User-Agent": "Mozilla/5.0 research@example.com"}
YEARS = range(2021, 2027)


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get(url):
    response = requests.get(url, headers=HEADERS, timeout=60)
    if response.status_code != 200:
        raise RuntimeError(f"HTTP {response.status_code}: {url}")
    return response.text


def audit_year(year, kind):
    url = f"https://www.federalreserve.gov/newsevents/{year}-{kind}.htm"
    response = requests.get(url, headers=HEADERS, timeout=60)
    if response.status_code == 404:
        return [], {"url": url, "status": 404, "kind": kind, "year": year,
                    "note": "official annual page not yet published"}
    if response.status_code != 200:
        raise RuntimeError(f"HTTP {response.status_code}: {url}")
    text = response.text
    soup = BeautifulSoup(text, "html.parser")
    rows = []
    for row in soup.select("div.row"):
        time_node = row.select_one(".eventlist__time time")
        event_node = row.select_one(".eventlist__event")
        if not time_node or not event_node:
            continue
        speaker = event_node.select_one(".news__speaker")
        if not speaker or "Jerome H. Powell" not in speaker.get_text(" ", strip=True):
            continue
        date_text = time_node.get_text(" ", strip=True)
        try:
            date_value = datetime.strptime(date_text, "%m/%d/%Y").date().isoformat()
        except ValueError:
            continue
        link = next((a for a in event_node.find_all("a", href=True)
                     if "/speech/" in a["href"] or "/testimony/" in a["href"]), None)
        title = link.get_text(" ", strip=True) if link else "Powell event"
        event_url = urljoin("https://www.federalreserve.gov", link["href"]) if link else url
        rows.append({
            "date": date_value,
            "year": year,
            "kind": kind,
            "title": title,
            "speaker": speaker.get_text(" ", strip=True),
            "event_url": event_url,
            "source_url": url,
            "exact_time_available": False,
            "advance_publication_timestamp_available": False,
            "eligibility": "archive_date_only_excluded_from_pre_announced_study",
        })
    return rows, {"url": url, "sha256": digest(text), "kind": kind, "year": year}


def main():
    events = []
    sources = []
    for year in YEARS:
        for kind in ("speeches", "testimony"):
            rows, source = audit_year(year, kind)
            events.extend(rows)
            sources.append(source)
    result = {
        "schema": "official_fed_speech_archive_audit_v1",
        "built_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scope": "official annual Federal Reserve speech/testimony archive pages",
        "events": sorted(events, key=lambda e: (e["date"], e["kind"], e["title"])),
        "sources": sources,
        "policy": {
            "exact_time": "not exposed by annual archive pages; no guessed times",
            "advance_known": "not proven by archive pages; excluded from Stage 22-style causal gate",
            "unscheduled_or_hindsight_events": "not added",
        },
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    counts = Counter((e["year"], e["kind"]) for e in events)
    print(f"wrote {OUT}: {len(events)} Powell archive events")
    for key, value in sorted(counts.items()):
        print(f"  {key}: {value}")
    print("eligible exact pre-announced rows: 0")


if __name__ == "__main__":
    main()
