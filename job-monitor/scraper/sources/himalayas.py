"""
Himalayas scraper — Remote global jobs (JSON API).
Public API: https://himalayas.app/jobs/api
Free, no auth. Returns up to 50 jobs in `jobs` array.
Hit rate is lower than Remotive (mix of frontend + non-tech roles),
but adds geographic diversity.
"""
from datetime import datetime, timezone
from typing import Optional

import requests

API_URL = "https://himalayas.app/jobs/api"
HEADERS = {
    "User-Agent": "job-monitor/1.0",
    "Accept": "application/json",
}

# Tokens to keep
FRONTEND_TOKENS = (
    "frontend", "front-end", "front end", "react", "next", "typescript",
    "javascript", "vue", "svelte", "tailwind", "web developer", "web engineer",
    "ui engineer", "ui developer", "full stack", "fullstack",
    "software engineer", "software developer",
)
BLOCK_TOKENS = (
    "content writer", "copywriter", "legal advisor", "course facilitator",
    "tutor", "teacher", "recruiter", "sales ", "marketing manager",
    "customer support", "virtual assistant", "data entry",
    "ios developer", "android developer", "mobile developer",
    "mechanical engineer", "civil engineer", "electrical engineer",
)


def fetch(queries: Optional[list[str]] = None) -> list[dict]:
    """Fetch up to 50 jobs from Himalayas and filter client-side."""
    try:
        resp = requests.get(API_URL, params={"limit": 50}, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        jobs = data.get("jobs", []) if isinstance(data, dict) else data
    except Exception as e:
        print(f"[himalayas] FAILED: {e}")
        return []

    out: list[dict] = []
    for j in jobs:
        if not isinstance(j, dict):
            continue
        if _is_frontend_match(j):
            out.append(_normalize(j))
    return out


def _is_frontend_match(j: dict) -> bool:
    title = (j.get("title") or "").lower()
    cats = " ".join((c or "").lower() for c in (j.get("categories") or []))
    excerpt = (j.get("excerpt") or "").lower()
    haystack = f"{title} {cats}"

    if any(t in haystack for t in BLOCK_TOKENS):
        return False
    if not any(t in haystack for t in FRONTEND_TOKENS):
        if not any(t in excerpt for t in FRONTEND_TOKENS):
            return False
    return True


def _normalize(j: dict) -> dict:
    pub_epoch = j.get("pubDate")
    if isinstance(pub_epoch, (int, float)):
        try:
            dt = datetime.fromtimestamp(pub_epoch, tz=timezone.utc)
            pub_iso = dt.date().isoformat()
            age = (datetime.now(timezone.utc) - dt).days
        except (ValueError, OSError):
            pub_iso, age = "", None
    else:
        pub_iso, age = "", None

    # Normalize list fields to strings
    def _join_or(v, default="", sep=", "):
        if v is None or v == "":
            return default
        if isinstance(v, list):
            return sep.join(str(x) for x in v if x) or default
        return str(v)

    salary = ""
    smin = j.get("minSalary")
    smax = j.get("maxSalary")
    if smin and smax:
        salary = f"{smin}-{smax} {j.get('currency', '')}".strip()

    return {
        "id": f"himalayas-{j.get('companySlug','')}-{abs(hash(j.get('title',''))) & 0xffffff}",
        "name": (j.get("title") or "").strip(),
        "company": (j.get("companyName") or "").strip(),
        "url": j.get("applicationLink") or j.get("guid") or j.get("url") or "",
        "source": "Himalayas",
        "location": _join_or(j.get("locationRestrictions"), "Remote"),
        "workplace": "Remote",
        "job_type": _join_or(j.get("employmentType"), ""),
        "experience_years": _join_or(j.get("seniority"), ""),
        "skills": [c for c in (j.get("categories") or []) if c],
        "salary": salary,
        "description_excerpt": (j.get("excerpt") or "")[:500],
        "date_posted": pub_iso,
        "age_days": age,
        "date_found": datetime.now(timezone.utc).date().isoformat(),
    }
