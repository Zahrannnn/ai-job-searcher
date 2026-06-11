"""
LinkedIn scraper — Public guest job search (HTML scraping, no auth).

LinkedIn exposes job search at:
  https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search

The response is HTML (not JSON, despite the JSON-flavored URL path).
Each job card has:
  - data-entity-urn="urn:li:jobPosting:<numeric_id>"
  - <h3 class="base-search-card__title"> for the title
  - <h4 class="base-search-card__subtitle"> for the company
  - <span class="job-search-card__location"> for the location
  - <time datetime="YYYY-MM-DD"> for the post date
  - <a class="base-card__full-link" href="..."> for the job URL

Pagination: ?start=0, 10, 20, ... (about 10 jobs per page).

We fire 4 queries that cover Cairo + Remote + Egypt, deduplicate by
the numeric posting ID, then filter client-side to frontend roles.
This stays well under LinkedIn's public rate limit.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import unquote

import requests

API_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml",
}

# (keywords, location) pairs to cover Cairo + Egypt + Remote
QUERIES = [
    ("react frontend developer", "Egypt"),
    ("nextjs typescript",         "Egypt"),
    ("frontend developer",        "Cairo, Cairo, Egypt"),
    ("react typescript",          "Remote"),
]

# Tokens to keep
FRONTEND_TOKENS = (
    "react", "next", "nextjs", "typescript", "javascript",
    "frontend", "front-end", "front end", "vue", "svelte", "tailwind",
    "web developer", "web engineer", "ui engineer", "ui developer",
    "full stack", "fullstack", "software engineer", "software developer",
)
BLOCK_TOKENS = (
    "ios developer", "android developer", "mobile developer",
    "recruiter", "sales ", "marketing manager", "seo manager",
    "data scientist", "data analyst", "data engineer",
    "machine learning engineer", "ml engineer", "ai engineer",
    "devops engineer", "cloud engineer", "network engineer",
    "security engineer", "qa engineer", "test engineer",
    "mechanical engineer", "electrical engineer", "civil engineer",
)

# Regex patterns — LinkedIn's HTML is whitespace-heavy and we
# can't use lxml reliably on the data-* attribute layout, so we
# parse each card with a single combined regex anchored on the
# urn attribute.
CARD_RE = re.compile(
    r'data-entity-urn="urn:li:jobPosting:(?P<id>\d+)"'
    r'.*?'                                                                          # card attrs
    r'class="base-card__full-link[^"]*" href="(?P<url>[^"]+)"'                       # job link
    r'.*?'                                                                          # inside <a>
    r'<h3 class="base-search-card__title">(?P<title>.*?)</h3>'                       # title
    r'.*?'                                                                          # subtitle
    r'class="base-search-card__subtitle">.*?</a>\s*</h4>'                           # company <a>...</a>
    r'(?P<company>.*?)'                                                              # captured after <a>
    r'(?=<!---->)|<h4 class="base-search-card__subtitle">\s*<a[^>]*>\s*(?P<company2>[^<]+)',  # alt: company in first <a> after subtitle
    re.DOTALL,
)
# The above regex is too fragile. Use a simpler two-step approach:
# 1. Find each <div ...job-search-card ...>...</div> block
# 2. Inside each, extract fields with small targeted regexes

URN_RE    = re.compile(r'data-entity-urn="urn:li:jobPosting:(\d+)"')
TITLE_RE  = re.compile(r'<h3 class="base-search-card__title">\s*(.*?)\s*</h3>', re.DOTALL)
COMPANY_RE = re.compile(
    r'<h4 class="base-search-card__subtitle">\s*<a[^>]*>\s*([^<]+?)\s*</a>',
    re.DOTALL,
)
LOC_RE    = re.compile(
    r'<span class="job-search-card__location">\s*(.*?)\s*</span>',
    re.DOTALL,
)
TIME_RE   = re.compile(r'<time[^>]*datetime="([^"]+)"')
HREF_RE   = re.compile(r'class="base-card__full-link[^"]*" href="([^"]+)"')

# Find each card by its opening <div ... job-search-card ...> tag
CARD_OPEN_RE = re.compile(r'<div class="base-card[^"]*?job-search-card[^"]*"', re.DOTALL)
# Use a simpler approach: split on the job-search-card opening tag
CARD_END = re.compile(r'</li>\s*</ul>|<li>\s*<!---->\s*</li>|</li>\s*</ul>', re.DOTALL)


def fetch(queries: Optional[list[str]] = None) -> list[dict]:
    """Fetch the configured queries, paginate 2 pages each, dedupe,
    filter to frontend roles, return normalized dicts."""
    queries_to_run = QUERIES
    out: list[dict] = []
    seen_ids: set[str] = set()

    for keywords, location in queries_to_run:
        for start in (0, 10):  # 2 pages per query = 20 jobs per query
            try:
                resp = requests.get(
                    API_URL,
                    params={"keywords": keywords, "location": location, "start": start},
                    headers=HEADERS,
                    timeout=20,
                )
                if resp.status_code != 200:
                    continue
                html = resp.text
            except Exception as e:
                print(f"[linkedin] FAILED {keywords!r} start={start}: {e}")
                continue

            for j in _parse_page(html):
                if j["id"] in seen_ids:
                    continue
                if not _is_frontend_match(j):
                    continue
                seen_ids.add(j["id"])
                out.append(j)

    return out


def _parse_page(html: str) -> list[dict]:
    """Split the page on each card's opening tag, then extract fields."""
    if "base-search-card" not in html:
        return []
    # Find the first card, then slice from there
    parts = re.split(r'<div class="base-card[^"]*?job-search-card[^"]*"', html)
    # parts[0] is everything before the first card
    jobs: list[dict] = []
    for chunk in parts[1:]:
        # End the chunk at the first </li> after the opening
        end = re.search(r'</li>', chunk)
        if end:
            chunk = chunk[:end.start()]
        job = _extract_job(chunk)
        if job:
            jobs.append(job)
    return jobs


def _extract_job(chunk: str) -> dict | None:
    urn_m   = URN_RE.search(chunk)
    title_m = TITLE_RE.search(chunk)
    href_m  = HREF_RE.search(chunk)
    company_m = COMPANY_RE.search(chunk)
    loc_m   = LOC_RE.search(chunk)
    time_m  = TIME_RE.search(chunk)

    if not (urn_m and title_m and href_m):
        return None

    job_id = urn_m.group(1)
    title = _clean(title_m.group(1))
    href = unquote(href_m.group(1))
    # Strip trackingId / refId params to get a clean public URL
    href = re.sub(r'\?.*$', '', href)

    company = _clean(company_m.group(1)) if company_m else ""
    location = _clean(loc_m.group(1)) if loc_m else ""

    pub = time_m.group(1) if time_m else ""
    age = None
    if pub:
        try:
            d = datetime.strptime(pub, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - d).days
        except ValueError:
            age = None

    return {
        "id": f"linkedin-{job_id}",
        "name": title,
        "company": company,
        "url": href,
        "source": "LinkedIn",
        "location": location or "Egypt",
        "workplace": "On-site",  # LinkedIn doesn't expose workplace type in card HTML
        "job_type": "",
        "experience_years": "",
        "skills": [],  # not exposed in card HTML
        "salary": "",
        "description_excerpt": "",
        "date_posted": pub,
        "age_days": age,
        "date_found": datetime.now(timezone.utc).date().isoformat(),
    }


def _clean(s: str) -> str:
    """Strip HTML tags and collapse whitespace."""
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _is_frontend_match(j: dict) -> bool:
    haystack = (j["name"] + " " + j["company"]).lower()
    if any(t in haystack for t in BLOCK_TOKENS):
        return False
    if not any(t in haystack for t in FRONTEND_TOKENS):
        return False
    return True
