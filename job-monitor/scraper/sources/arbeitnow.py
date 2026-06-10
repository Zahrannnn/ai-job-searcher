"""
Arbeitnow.com scraper — Europe/Remote jobs (JSON API).
Public API: https://www.arbeitnow.com/api
Free, no auth. Returns 100 jobs per page in creation order.

NOTE: This source is mostly German-speaking on-site roles. We pull the
first 2 pages and apply a strict English + remote filter. Expect low hit
rate but worth checking for hidden gems.
"""
from datetime import datetime, timezone
from typing import Optional

import requests

API_URL = "https://www.arbeitnow.com/api/job-board-api"
HEADERS = {"User-Agent": "job-monitor/1.0"}

# Tokens to keep
FRONTEND_TOKENS = (
    "react", "next", "typescript", "javascript", "frontend",
    "front-end", "front end", "vue", "svelte", "tailwind",
    "web developer", "ui engineer", "web engineer",
)
# Strong non-English signals
NON_ENGLISH_TOKENS = (
    " (m/w/d)", "(m/w/x)", "/w/d", "gn)", "m/w)", " (gn)",
    " mit ", " und ", " für ", " der ", " die ", " das ",
    " erfahrung", "kenntnisse", "berufserfahren", "bewerbung",
    "aufgaben", "qualifikation", "deutsch", "english und deutsch",
)


def fetch(queries: Optional[list[str]] = None) -> list[dict]:
    """Pull first 2 pages (200 jobs), filter to remote English frontend."""
    items: list[dict] = []
    for page in (1, 2):
        try:
            items.extend(_scrape_page(page))
        except Exception as e:
            print(f"[arbeitnow] page={page} FAILED: {e}")
    return _filter_frontend(items)


def _scrape_page(page: int) -> list[dict]:
    resp = requests.get(API_URL, params={"page": page}, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.json().get("data", [])


def _filter_frontend(jobs: list[dict]) -> list[dict]:
    out: list[dict] = []
    for j in jobs:
        if not j.get("remote"):
            continue
        title = (j.get("title") or "").lower()
        desc = (j.get("description") or "").lower()
        # Strip HTML to detect language
        if any(tok in desc[:3000] for tok in NON_ENGLISH_TOKENS):
            continue
        if not any(tok in title or tok in desc for tok in FRONTEND_TOKENS):
            continue

        out.append(_normalize(j))
    return _dedup(out)


def _normalize(j: dict) -> dict:
    created = j.get("created_at")
    pub_iso = ""
    if isinstance(created, (int, float)):
        try:
            pub_iso = datetime.fromtimestamp(created, tz=timezone.utc).date().isoformat()
        except (ValueError, OSError):
            pub_iso = ""
    age = None
    if pub_iso:
        d = datetime.strptime(pub_iso, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - d).days

    return {
        "id": f"arbeitnow-{j.get('slug', hash(j.get('url', '')) & 0xffffffff)}",
        "name": j.get("title", ""),
        "company": j.get("company_name", ""),
        "url": j.get("url", ""),
        "source": "Arbeitnow",
        "location": j.get("location", "") or "Remote",
        "workplace": "Remote",
        "experience_years": "",
        "skills": [t for t in (j.get("tags") or []) if isinstance(t, str)],
        "salary": "",
        "description_excerpt": (j.get("description") or "")[:500],
        "date_posted": pub_iso,
        "age_days": age,
        "date_found": datetime.now(timezone.utc).date().isoformat(),
    }


def _dedup(items: list[dict]) -> list[dict]:
    seen, out = set(), []
    for it in items:
        url = it.get("url", "")
        if url and url not in seen:
            seen.add(url)
            out.append(it)
    return out
