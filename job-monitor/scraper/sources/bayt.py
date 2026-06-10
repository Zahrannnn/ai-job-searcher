"""
Bayt.com scraper — Egypt/MENA secondary.
Bayt often blocks scrapers (403); we try with realistic headers and
fall back gracefully. The page is mostly server-rendered HTML.
"""
from datetime import datetime, timezone
from typing import Optional
import re

import requests
from bs4 import BeautifulSoup

from scraper.filters import parse_age_days

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

BASE = "https://www.bayt.com"


def fetch(queries: Optional[list[str]] = None) -> list[dict]:
    queries = queries or ["react-developer", "front-end-developer", "nextjs"]
    items: list[dict] = []
    for q in queries:
        try:
            items.extend(_scrape_search(q))
        except Exception as e:
            print(f"[bayt] query={q!r} FAILED: {e}")
    return _dedup(items)


def _dedup(items: list[dict]) -> list[dict]:
    seen, out = set(), []
    for it in items:
        url = it.get("url", "")
        if url and url not in seen:
            seen.add(url)
            out.append(it)
    return out


def _scrape_search(query: str) -> list[dict]:
    url = f"{BASE}/en/egypt/jobs/{query}-jobs/"
    resp = requests.get(url, headers=HEADERS, timeout=20)
    if resp.status_code == 403:
        print(f"[bayt] 403 forbidden for {url} — skipping this query")
        return []
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    items: list[dict] = []
    # Each job is in an <a href="/en/egypt/jobs/<slug>/"> with a <h2> title
    for a in soup.select("a[href*='/en/egypt/jobs/']"):
        href = a.get("href", "")
        if "/jobs/" not in href or href.endswith("/jobs/"):
            continue
        if not href.startswith("http"):
            href = BASE + href
        # Title
        title_tag = a.select_one("h2")
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        if not title or len(title) < 5:
            continue

        # Company
        company = ""
        comp_tag = a.find("img", alt=True)
        if comp_tag:
            company = comp_tag.get("alt", "")
        if not company:
            for span in a.select("span"):
                txt = span.get_text(strip=True)
                if 3 < len(txt) < 50 and "ago" not in txt.lower():
                    company = txt
                    break

        # Location (often in the text)
        location = ""
        for span in a.select("span"):
            txt = span.get_text(strip=True)
            if "," in txt and any(c in txt for c in ("Egypt", "Cairo", "Arabia", "Saudi", "Qatar", "UAE", "Jordan", "Amman", "Dubai")):
                location = txt
                break

        # Posted
        posted = ""
        for span in a.select("span"):
            txt = span.get_text(strip=True)
            if re.search(r"\d+\s*(hour|day|week|month|minute)|ago|yesterday|today", txt, re.IGNORECASE):
                posted = txt
                break

        age = parse_age_days(posted)

        items.append({
            "id": f"bayt-{hash(href) & 0xffffffff}",
            "name": title,
            "company": company,
            "url": href,
            "source": "Bayt",
            "location": location or "Egypt",
            "workplace": "",
            "experience_years": "",
            "skills": [],
            "salary": "",
            "description_excerpt": "",
            "date_posted": posted,
            "age_days": age,
            "date_found": datetime.now(timezone.utc).date().isoformat(),
        })

    return items
