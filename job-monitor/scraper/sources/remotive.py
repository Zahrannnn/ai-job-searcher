"""
Remotive.com scraper — Remote global jobs (JSON API).
Public API: https://remotive.com/api-documentation
Free, no auth. Category-based filtering only (no ?search=).
We pull category=software-dev and filter client-side by tag/title.
"""
from datetime import datetime, timezone
from typing import Optional

import requests

API_URL = "https://remotive.com/api/remote-jobs"
HEADERS = {"User-Agent": "job-monitor/1.0"}

# Frontend skill tokens to keep (case-insensitive substring match)
FRONTEND_TOKENS = (
    "react", "next", "typescript", "javascript", "frontend",
    "front-end", "front end", "vue", "svelte", "tailwind", "css",
    "web developer", "ui engineer", "web engineer",
)

# Tokens that disqualify a job (blocklist, applies even if frontend is in tags)
BLOCK_TOKENS = (
    "ios developer", "android developer", "mobile developer",
    "native (ios", "native (android", "machine learning engineer",
    "data scientist", "data engineer", "devops engineer",
    "salesforce", "sales engineer", "account executive",
    "customer success", "recruiter", "marketing manager",
)


def fetch(queries: Optional[list[str]] = None) -> list[dict]:
    """Single category call. `queries` arg is accepted for interface compat
    with the orchestrator but ignored — Remotive has no keyword search."""
    try:
        jobs = _scrape_software_dev()
    except Exception as e:
        print(f"[remotive] FAILED: {e}")
        return []
    return _filter_frontend(jobs)


def _scrape_software_dev() -> list[dict]:
    resp = requests.get(
        API_URL,
        params={"category": "software-dev", "limit": 50},
        headers=HEADERS,
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json().get("jobs", [])


def _filter_frontend(jobs: list[dict]) -> list[dict]:
    """Keep only jobs that mention a frontend token in title/tags/description
    AND do not contain a block token anywhere."""
    out: list[dict] = []
    for j in jobs:
        title = (j.get("title") or "").lower()
        tags = " ".join(t.lower() for t in (j.get("tags") or []))
        desc = (j.get("description") or "").lower()[:2000]
        haystack_tags_title = f"{title} {tags}"

        if not any(tok in haystack_tags_title for tok in FRONTEND_TOKENS):
            continue
        if any(tok in haystack_tags_title or tok in desc for tok in BLOCK_TOKENS):
            continue

        out.append(_normalize(j))
    return _dedup(out)


def _normalize(j: dict) -> dict:
    pub_raw = j.get("publication_date", "")
    pub = pub_raw[:10] if isinstance(pub_raw, str) else ""
    age = None
    if pub:
        try:
            d = datetime.strptime(pub, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - d).days
        except ValueError:
            age = None

    return {
        "id": f"remotive-{j.get('id')}",
        "name": j.get("title", ""),
        "company": j.get("company_name", ""),
        "url": j.get("url", ""),
        "source": "Remotive",
        "location": j.get("candidate_required_location", "") or "Remote",
        "workplace": "Remote",
        "experience_years": "",
        "skills": [t for t in (j.get("tags") or []) if isinstance(t, str)],
        "salary": j.get("salary", "") or "",
        "description_excerpt": (j.get("description") or "")[:500],
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
