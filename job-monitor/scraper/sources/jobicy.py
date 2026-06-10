"""
Jobicy scraper — Remote global jobs (JSON API).
Public API: https://jobicy.com/api-documentation
Free, no auth. Only filter is ?geo= (predefined slug); no ?search=.

NOTE: This source is heavily UK/EU sales/leadership. We use ?geo=emea
and filter client-side to frontend roles. Expect very low hit rate.
"""
from datetime import datetime, timezone
from typing import Optional

import requests

API_URL = "https://jobicy.com/api/v2/remote-jobs"
HEADERS = {"User-Agent": "job-monitor/1.0"}

FRONTEND_TOKENS = (
    "react", "next", "typescript", "javascript", "frontend",
    "front-end", "front end", "vue", "svelte", "tailwind",
    "web developer", "ui engineer", "web engineer",
)
BLOCK_TOKENS = (
    "sales", "account manager", "account executive", "marketing manager",
    "seo manager", "recruiter", "customer success", "support engineer",
)


def fetch(queries: Optional[list[str]] = None) -> list[dict]:
    """Single geo=emea call. `queries` is accepted for compat but ignored."""
    try:
        jobs = _scrape_emea()
    except Exception as e:
        print(f"[jobicy] FAILED: {e}")
        return []
    return _filter_frontend(jobs)


def _scrape_emea() -> list[dict]:
    resp = requests.get(API_URL, params={"count": 50, "geo": "emea"}, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.json().get("jobs", [])


def _filter_frontend(jobs: list[dict]) -> list[dict]:
    out: list[dict] = []
    for j in jobs:
        title = (j.get("jobTitle") or "").lower()
        excerpt = (j.get("jobExcerpt") or "").lower()
        if any(tok in title for tok in BLOCK_TOKENS):
            continue
        if not any(tok in title or tok in excerpt for tok in FRONTEND_TOKENS):
            continue
        out.append(_normalize(j))
    return _dedup(out)


def _normalize(j: dict) -> dict:
    pub_raw = j.get("pubDate", "")
    pub = pub_raw[:10] if isinstance(pub_raw, str) else ""
    age = None
    if pub:
        try:
            d = datetime.strptime(pub, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - d).days
        except ValueError:
            age = None

    skills = []
    for v in (j.get("jobIndustry") or []):
        if isinstance(v, str):
            skills.append(v)
    for v in (j.get("jobType") or []):
        if isinstance(v, str):
            skills.append(v)

    return {
        "id": f"jobicy-{j.get('id')}",
        "name": j.get("jobTitle", ""),
        "company": j.get("companyName", ""),
        "url": j.get("url", ""),
        "source": "Jobicy",
        "location": j.get("jobGeo", "") or "Remote",
        "workplace": "Remote",
        "experience_years": j.get("jobLevel", "") or "",
        "skills": skills,
        "salary": "",
        "description_excerpt": (j.get("jobExcerpt", "") or "")[:500],
        "date_posted": pub,
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
