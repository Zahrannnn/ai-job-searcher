"""
VueJobs scraper — Vue-focused but covers React Native & React roles too.
HTML scraping; public site with no API.
"""
from datetime import datetime, timezone
from typing import Optional
import re

import requests
from bs4 import BeautifulSoup

from scraper.filters import parse_age_days

BASE = "https://vuejobs.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; job-monitor/1.0)"
}


def fetch(queries: Optional[list[str]] = None) -> list[dict]:
    """VueJobs is a single search page; we scrape once and filter by query."""
    try:
        return _scrape_listings()
    except Exception as e:
        print(f"[vuejobs] FAILED: {e}")
        return []


def _scrape_listings() -> list[dict]:
    resp = requests.get(f"{BASE}/jobs", headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    items: list[dict] = []
    # Each job link points to /jobs/<slug>
    for a in soup.select("a[href^='/jobs/']"):
        href = a.get("href", "")
        if href == "/jobs" or href == "/jobs/" or "/jobs?" in href or "/jobs/post" in href:
            continue
        # Title is usually inside the <a>
        title = a.get_text(strip=True)
        if not title or len(title) < 5 or "Job" in title and len(title) < 20:
            continue

        # Company
        company = ""
        # Look for img with company alt nearby
        for img in a.find_all("img", alt=True):
            alt = img.get("alt", "")
            if alt and alt != title:
                company = alt
                break

        # Posted time (e.g., "1 day ago")
        posted = ""
        for span in a.find_all("span"):
            txt = span.get_text(strip=True)
            if re.search(r"\d+\s*(hour|day|week|month|minute)|ago|yesterday|today", txt, re.IGNORECASE):
                posted = txt
                break

        # Location
        location = ""
        for span in a.find_all("span"):
            txt = span.get_text(strip=True)
            if "remote" in txt.lower() or "on-site" in txt.lower() or "hybrid" in txt.lower():
                location = txt
                break

        full_url = BASE + href
        age = parse_age_days(posted)

        items.append({
            "id": f"vuejobs-{hash(full_url) & 0xffffffff}",
            "name": title,
            "company": company,
            "url": full_url,
            "source": "VueJobs",
            "location": location or "Remote",
            "workplace": "Remote" if "remote" in location.lower() else "",
            "experience_years": "",
            "skills": [],
            "salary": "",
            "description_excerpt": "",
            "date_posted": posted,
            "age_days": age,
            "date_found": datetime.now(timezone.utc).date().isoformat(),
        })

    return items
