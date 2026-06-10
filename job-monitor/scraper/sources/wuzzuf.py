"""
Wuzzuf.net scraper — Egypt's largest job board (HTML scraping).
URL pattern: https://wuzzuf.net/search/jobs?q={query}&start={N}
Page is server-side rendered React with Emotion CSS classes.

Stable extraction strategy: identify each job card by the
`https://wuzzuf.net/jobs/careers/` link it contains, then reach
into known CSS classes for field-level data. CSS hashes may
change between Wuzzuf deployments, so the card boundary uses
a content-based XPath fallback.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

import requests
from lxml import html as lxml_html

BASE = "https://wuzzuf.net/search/jobs"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Tokens to keep (frontend roles)
FRONTEND_TOKENS = (
    "frontend", "front-end", "front end", "react", "vue", "angular",
    "next.js", "nextjs", "typescript", "javascript", "web developer",
    "ui developer", "ui engineer", "web engineer", "software engineer",
    "full stack", "fullstack", ".net", "node.js", "nodejs",
)
# Tokens to drop
BLOCK_TOKENS = (
    "sales", "marketing", "hr ", "human resources", "accountant",
    "graphic designer", "content writer", "copywriter", "recruiter",
    "customer service", "call center", "data entry", "admin",
    "operations manager", "product manager", "project manager",
    "business analyst", "data analyst", "data scientist",
    "devops engineer", "security engineer", "qa engineer",
    "test engineer", "manual tester", "automation tester",
    "ios developer", "android developer", "mobile developer",
    "senior product manager", "engineering manager",
    "internship", "intern ",
)

# Date pattern: "X days ago" | "X day ago" | "a month ago" | "X months ago"
DAYS_RE = re.compile(r"(\d+)\s+days?\s+ago", re.I)
MONTHS_RE = re.compile(r"(\d+)\s+months?\s+ago", re.I)
TODAY_RE = re.compile(r"^(today|just\s+now|an?\s+hour\s+ago)\s*$", re.I)
YESTERDAY_RE = re.compile(r"^yesterday\s*$", re.I)


def fetch(queries: Optional[list[str]] = None, max_pages: int = 2) -> list[dict]:
    """Pull first `max_pages` pages of each query, return deduplicated jobs."""
    queries = queries or [
        "react frontend",
        "next.js",
        "typescript frontend",
        "frontend developer",
    ]
    items: list[dict] = []
    for q in queries:
        for page in range(max_pages):
            start = page  # 0-indexed
            try:
                items.extend(_scrape_query(q, start))
            except Exception as e:
                print(f"[wuzzuf] q={q!r} start={start} FAILED: {e}")
    return _dedup(items)


def _scrape_query(query: str, start: int) -> list[dict]:
    url = f"{BASE}?q={requests.utils.quote(query)}&start={start}"
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return _parse_page(resp.text)


def _parse_page(html_text: str) -> list[dict]:
    tree = lxml_html.fromstring(html_text)
    # Find every job card: a div that contains a link to /jobs/careers/
    cards = tree.xpath(
        '//div[.//a[starts-with(@href, "https://wuzzuf.net/jobs/careers/")]]'
        '[.//h2[.//a]]'
    )

    out: list[dict] = []
    for card in cards:
        try:
            job = _parse_card(card)
            if job and _is_frontend(job):
                out.append(job)
        except Exception as e:
            print(f"[wuzzuf] card parse FAILED: {e}")
            continue
    return out


def _parse_card(card) -> Optional[dict]:
    # Title
    title_a = card.xpath('.//h2//a[normalize-space(text())][1]')
    if not title_a:
        return None
    title = " ".join(title_a[0].text_content().split()).strip()

    # Canonical job URL (company careers link contains numeric job ID)
    careers_a = card.xpath(
        './/a[starts-with(@href, "https://wuzzuf.net/jobs/careers/")][1]'
    )
    if not careers_a:
        return None
    careers_href = careers_a[0].get("href", "").strip()
    m = re.search(r"-(\d+)$", careers_href)
    job_id = m.group(1) if m else hash(careers_href) & 0xFFFFFFFF

    # Company name (strip trailing " -")
    company = " ".join(careers_a[0].text_content().split())
    company = re.sub(r"\s*-\s*$", "", company).strip() or "Confidential"

    # Location
    loc_spans = card.xpath(
        './/h2/following-sibling::div[1]//span[last()]'
    )
    location = ""
    if loc_spans:
        location = " ".join(loc_spans[0].text_content().split())
        # Remove HTML-comment artefacts ("<!-- -->" leaves empty segments)
        location = re.sub(r",\s*$", "", location).strip()

    # Date posted (relative)
    date_a = card.xpath(
        './/div[contains(@class,"css-eg55jf") or contains(@class,"css-1jldrig")][1]'
    )
    date_text = ""
    if date_a:
        date_text = " ".join(date_a[0].text_content().split()).strip()
    age_days = _parse_age_days(date_text)

    # Job type + work mode
    # Wuzzuf uses CSS class `eoyjyou0` on two tags: employment type
    # (Full Time / Part Time / Internship) and work mode (On-site / Remote / Hybrid).
    # The CSS hash for the type-specific class (`css-uc9rga`) may rotate between
    # deployments, so we fall back to content-based classification.
    type_spans = card.xpath('.//span[contains(@class,"eoyjyou0")]')
    employment_keywords = ("full time", "part time", "internship", "freelance", "contract")
    work_mode_keywords = ("on-site", "remote", "hybrid", "work from home")
    job_type = ""
    work_mode = ""
    for s in type_spans:
        text = " ".join(s.text_content().split()).strip()
        low = text.lower()
        if any(k in low for k in work_mode_keywords):
            work_mode = text
        elif any(k in low for k in employment_keywords):
            job_type = text

    # Experience
    exp_match = re.search(
        r"(\d+)\s*-\s*(\d+)\s*Yrs?\s*of\s*Exp", card.text_content()
    )
    experience = ""
    if exp_match:
        experience = f"{exp_match.group(1)}-{exp_match.group(2)} yrs"
    elif "Student" in card.text_content():
        experience = "Student"

    # Skills (strip Wuzzuf's "· " bullet prefix)
    skill_links = card.xpath('.//a[contains(@class,"css-5x9pm1")]')
    skills = []
    for a in skill_links:
        text = " ".join(a.text_content().split()).strip()
        if text:
            text = re.sub(r"^[·•\-\*]+\s*", "", text)
            skills.append(text)

    return {
        "id": f"wuzzuf-{job_id}",
        "name": title,
        "company": company,
        "url": careers_href,
        "source": "Wuzzuf",
        "location": location or "Egypt",
        "workplace": work_mode or "",
        "job_type": job_type or "",
        "experience_years": experience,
        "skills": skills,
        "salary": "",
        "description_excerpt": "",
        "date_posted": "",
        "age_days": age_days,
        "date_found": datetime.now(timezone.utc).date().isoformat(),
        "raw_date_text": date_text,
    }


def _parse_age_days(text: str) -> Optional[int]:
    if not text:
        return None
    if TODAY_RE.match(text):
        return 0
    if YESTERDAY_RE.match(text):
        return 1
    m = DAYS_RE.search(text)
    if m:
        return int(m.group(1))
    m = MONTHS_RE.search(text)
    if m:
        return int(m.group(1)) * 30
    if "a month" in text.lower():
        return 30
    if "month" in text.lower() and not m:
        return 60
    if "year" in text.lower():
        return 365
    return None


def _is_frontend(job: dict) -> bool:
    haystack = (
        f"{job['name']} {' '.join(job['skills'])}".lower()
    )
    if any(tok in haystack for tok in BLOCK_TOKENS):
        return False
    if not any(tok in haystack for tok in FRONTEND_TOKENS):
        return False
    # Age gate: skip jobs older than 30 days
    if job.get("age_days") is not None and job["age_days"] > 30:
        return False
    return True


def _dedup(items: list[dict]) -> list[dict]:
    seen, out = set(), []
    for it in items:
        if it["id"] in seen:
            continue
        seen.add(it["id"])
        out.append(it)
    return out
