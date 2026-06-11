"""
Jobicy scraper — Remote global jobs (JSON API).
Public API: https://jobicy.com/api-documentation
Free, no auth.

Strategy: pull 50 jobs from `?industry=engineering` (closest match to
software engineering), then filter client-side. Some items will be
non-frontend (electrical, mechanical) — we drop those via BLOCK_TOKENS.
"""
from datetime import datetime, timezone
from typing import Optional

import requests

API_URL = "https://jobicy.com/api/v2/remote-jobs"
HEADERS = {
    "User-Agent": "job-monitor/1.0",
    "Accept": "application/json",
}

# Tokens to keep
FRONTEND_TOKENS = (
    "react", "next", "typescript", "javascript",
    "frontend", "front-end", "front end", "vue", "svelte", "tailwind",
    "web developer", "web engineer", "ui engineer", "ui developer",
    "full stack", "fullstack", "software engineer", "software developer",
)
# Hard block non-software engineering roles
BLOCK_TOKENS = (
    "sales engineer", "account manager", "account executive",
    "marketing manager", "seo manager", "field engineer",
    "mechanical engineer", "electrical engineer", "civil engineer",
    "industrial engineer", "process engineer", "manufacturing engineer",
    "quality engineer", "qa engineer", "test engineer", "automation engineer",
    "systems engineer", "network engineer", "security engineer",
    "devops engineer", "cloud engineer", "data engineer",
    "machine learning engineer", "ml engineer", "ai engineer",
    "ios developer", "android developer", "mobile developer",
    "recruiter", "sales ", "support engineer",
)


def fetch(queries: Optional[list[str]] = None) -> list[dict]:
    """Fetch one batch from the engineering industry."""
    try:
        resp = requests.get(
            API_URL,
            params={"count": 50, "industry": "engineering"},
            headers=HEADERS,
            timeout=20,
        )
        resp.raise_for_status()
        jobs = resp.json().get("jobs", [])
    except Exception as e:
        print(f"[jobicy] FAILED: {e}")
        return []

    out: list[dict] = []
    for j in jobs:
        if _is_frontend_match(j):
            out.append(_normalize(j))
    return out


def _is_frontend_match(j: dict) -> bool:
    title = (j.get("jobTitle") or "").lower()
    excerpt = (j.get("jobExcerpt") or "").lower()
    haystack = title
    if any(t in haystack for t in BLOCK_TOKENS):
        return False
    if not any(t in haystack for t in FRONTEND_TOKENS):
        if not any(t in excerpt for t in FRONTEND_TOKENS):
            return False
    return True


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
        "name": (j.get("jobTitle") or "").strip(),
        "company": (j.get("companyName") or "").strip(),
        "url": j.get("url", ""),
        "source": "Jobicy",
        "location": (j.get("jobGeo") or "Remote").strip(),
        "workplace": "Remote",
        "job_type": "",
        "experience_years": (j.get("jobLevel") or "").strip(),
        "skills": skills,
        "salary": "",
        "description_excerpt": (j.get("jobExcerpt") or "")[:500],
        "date_posted": pub,
        "age_days": age,
        "date_found": datetime.now(timezone.utc).date().isoformat(),
    }
