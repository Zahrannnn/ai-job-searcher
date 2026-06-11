"""
RemoteOK scraper — Remote global jobs (JSON API).
Public API: https://remoteok.com/api
Free, no auth. Returns ~100 jobs in descending recency order.
NOTE: First element is a metadata object, not a job; skip it.
"""
from datetime import datetime, timezone
from typing import Optional

import requests

API_URL = "https://remoteok.com/api"
HEADERS = {
    "User-Agent": "job-monitor/1.0",
    "Accept": "application/json",
}

# Tokens to keep
FRONTEND_TOKENS = (
    "react", "next", "typescript", "javascript",
    "frontend", "front-end", "front end", "vue", "svelte", "tailwind",
    "web developer", "web engineer", "ui engineer", "ui developer",
)
# Hard block: clearly non-software roles
BLOCK_TOKENS = (
    "courier", "driver", "delivery", "warehouse", "logistics",
    "mechanic", "electrician", "carpenter", "plumber",
    "waiter", "bartender", "housekeeping", "cleaner",
    "recruiter", "sales ", "marketing manager", "customer support",
    "virtual assistant", "data entry", "admin",
    "ios developer", "android developer", "mobile developer",
)


def fetch(queries: Optional[list[str]] = None) -> list[dict]:
    """Fetch all recent jobs from RemoteOK and filter client-side."""
    try:
        resp = requests.get(API_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[remoteok] FAILED: {e}")
        return []

    out: list[dict] = []
    for j in data:
        # First element is metadata, skip
        if not isinstance(j, dict) or "position" not in j:
            continue
        if _is_frontend_match(j):
            out.append(_normalize(j))
    return out


def _is_frontend_match(j: dict) -> bool:
    position = (j.get("position") or "").lower()
    tags = " ".join((t or "").lower() for t in (j.get("tags") or []))
    desc = (j.get("description") or "")[:3000].lower()
    haystack = f"{position} {tags}"

    if any(t in haystack for t in BLOCK_TOKENS):
        return False
    if not any(t in haystack for t in FRONTEND_TOKENS):
        # Fallback: scan the description for explicit mentions
        if not any(t in desc for t in FRONTEND_TOKENS):
            return False
    return True


def _normalize(j: dict) -> dict:
    # epoch -> ISO date
    epoch = j.get("epoch")
    if isinstance(epoch, (int, float)):
        try:
            dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
            pub_iso = dt.date().isoformat()
            age = (datetime.now(timezone.utc) - dt).days
        except (ValueError, OSError):
            pub_iso, age = "", None
    else:
        pub_iso, age = "", None

    # Salary: "0" or empty means undisclosed
    sal_min = j.get("salary_min") or 0
    sal_max = j.get("salary_max") or 0
    if sal_min and sal_max:
        salary = f"{sal_min}-{sal_max}"
    else:
        salary = ""

    return {
        "id": f"remoteok-{j.get('id')}",
        "name": (j.get("position") or "").strip(),
        "company": (j.get("company") or "").strip(),
        "url": j.get("url") or j.get("apply_url") or "",
        "source": "RemoteOK",
        "location": (j.get("location") or "Remote").strip(),
        "workplace": "Remote",
        "job_type": "",
        "experience_years": "",
        "skills": [t for t in (j.get("tags") or []) if t],
        "salary": salary,
        "description_excerpt": (j.get("description") or "")[:500],
        "date_posted": pub_iso,
        "age_days": age,
        "date_found": datetime.now(timezone.utc).date().isoformat(),
    }
