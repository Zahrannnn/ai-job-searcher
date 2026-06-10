"""
Rule-based filters and scoring engine for frontend jobs.
No LLM required — fast, deterministic, and tunable via config.yaml.
"""
import re
from datetime import datetime, timezone, timedelta
from typing import Optional


def _norm(s: Optional[str]) -> str:
    return (s or "").lower()


def matches_required_keywords(text: str, required: list[str]) -> bool:
    """Item must contain at least one required keyword (substring match)."""
    if not required:
        return True
    text = _norm(text)
    return any(kw.lower() in text for kw in required)


def has_blocked_keywords(text: str, blocked: list[str]) -> bool:
    """Item must not contain any blocked keyword."""
    if not blocked:
        return False
    text = _norm(text)
    return any(kw.lower() in text for kw in blocked)


def has_location(location: str, workplace: str, accepted: list[str]) -> bool:
    """Item must be in or accept one of the accepted locations."""
    if not accepted:
        return True
    blob = _norm(location) + " " + _norm(workplace)
    return any(loc.lower() in blob for loc in accepted)


def parse_age_days(text: str, today: Optional[datetime] = None) -> Optional[int]:
    """
    Parse 'Xd ago', 'X hours ago', 'X weeks ago', or 'YYYY-MM-DD' from text.
    Returns int days or None if unparseable.
    """
    text = _norm(text)
    if not text:
        return None
    today = today or datetime.now(timezone.utc)

    # Relative: "X hours/h/d/w ago" or "a minute ago"
    m = re.search(r"(\d+)\s*(hour|hours|hr|h)\s*ago", text)
    if m:
        return 0
    m = re.search(r"(\d+)\s*(minute|minutes|min|m)\s*ago", text)
    if m:
        return 0
    m = re.search(r"(\d+)\s*(day|days|d)\s*ago", text)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*(week|weeks|w)\s*ago", text)
    if m:
        return int(m.group(1)) * 7
    m = re.search(r"(\d+)\s*(month|months|mo)\s*ago", text)
    if m:
        return int(m.group(1)) * 30
    m = re.search(r"a\s*day\s*ago|yesterday", text)
    if m:
        return 1
    m = re.search(r"just\s*posted|today|new", text)
    if m:
        return 0

    # Absolute: ISO date
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        try:
            d = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
            return (today - d).days
        except ValueError:
            return None

    return None


def score(item: dict, scoring: dict) -> tuple[int, dict]:
    """
    Compute a 0-100 score for a single item.
    Returns (score, breakdown_dict).
    """
    name = _norm(item.get("name", ""))
    company = _norm(item.get("company", ""))
    location = _norm(item.get("location", ""))
    workplace = _norm(item.get("workplace", ""))
    skills = " ".join(_norm(s) for s in item.get("skills", []))
    desc = _norm(item.get("description_excerpt", ""))
    blob = f"{name} {company} {skills} {desc}"

    age = item.get("age_days")
    breakdown: dict = {}

    # --- POSITIVE ---

    # React / Next.js / TypeScript in title or skills (highest weight)
    if "react" in blob:
        breakdown["react"] = scoring.get("stack_match_react", 25)
    if "next.js" in blob or "nextjs" in blob:
        breakdown["nextjs"] = scoring.get("stack_match_nextjs", 15)
    if "typescript" in blob or "ts " in blob:
        breakdown["typescript"] = scoring.get("stack_match_typescript", 10)

    # Location match
    loc_blob = f"{location} {workplace}"
    if any(loc in loc_blob for loc in ("cairo", "egypt", "remote", "anywhere", "worldwide")):
        breakdown["location"] = scoring.get("location_cairo_remote", 20)
    elif any(loc in loc_blob for loc in ("riyadh", "saudi", "uae", "dubai", "qatar", "doha", "jordan", "amman")):
        breakdown["location_mena"] = scoring.get("location_cairo_remote", 15)
    elif "europe" in loc_blob or "uk" in loc_blob or "germany" in loc_blob:
        breakdown["location_eu"] = scoring.get("location_cairo_remote", 10)
    else:
        breakdown["location"] = -15  # wrong region

    # Freshness
    if age is not None and age <= 3:
        breakdown["fresh"] = scoring.get("posted_within_3_days", 15)
    elif age is not None and age <= 7:
        breakdown["fresh"] = scoring.get("posted_4_to_7_days", 10)
    elif age is not None and age <= 14:
        breakdown["fresh"] = 5
    elif age is not None and age > 14:
        breakdown["stale"] = -5

    # AI/ML mentioned
    ai_keywords = ("ai ", "llm", "genai", "agent", "intelligence", "ml ", "machine learning")
    if any(kw in blob for kw in ai_keywords):
        breakdown["ai"] = scoring.get("ai_or_ml_mentioned", 10)

    # Experience match
    exp_text = _norm(item.get("experience_years", ""))
    if exp_text in ("3+", "3 - 5", "3-5", "3 to 5", "3-7", "3 - 7"):
        breakdown["experience"] = scoring.get("experience_3_to_5yr", 10)
    elif exp_text in ("5+", "5+ yrs", "5 - 10", "5-10"):
        breakdown["experience_too_senior"] = scoring.get("five_plus_years_required", -10)
    elif exp_text in ("0+", "0-2", "entry level", "internship"):
        breakdown["internship"] = scoring.get("internship_role", -30)

    # Founding / early stage
    founding_signals = ("founding", "early stage", "founders", "startup", "lean", "small team")
    if any(s in blob for s in founding_signals):
        breakdown["founding"] = scoring.get("founding_or_early_role", 10)

    # Senior IC level
    if "senior" in name and "staff" not in name and "principal" not in name and "lead" not in name:
        breakdown["senior_ic"] = scoring.get("senior_ic_level", 5)

    # Salary disclosed
    sal = _norm(item.get("salary", ""))
    if sal and sal not in ("", "not specified", "unspecified"):
        breakdown["salary"] = scoring.get("salary_disclosed_competitive", 5)

    # --- NEGATIVE ---

    # Vue only
    if ("vue" in blob or "vuejs" in blob) and "react" not in blob:
        breakdown["vue_only"] = scoring.get("vuejs_only", -20)

    # Angular only
    if "angular" in blob and "react" not in blob:
        breakdown["angular_only"] = scoring.get("angular_only", -30)

    # PHP only
    if ("php" in blob or "laravel" in blob) and "react" not in blob:
        breakdown["php_only"] = scoring.get("php_only", -25)

    # .NET only
    if (".net" in blob or "c#" in blob) and "react" not in blob:
        breakdown["net_only"] = scoring.get("net_only", -25)

    # iOS / Android only
    if ("ios" in blob or "swift" in blob or "kotlin" in blob) and "react native" not in blob:
        breakdown["mobile_only"] = scoring.get("ios_or_android_only", -40)

    # US-only
    if "us-only" in loc_blob or "united states only" in loc_blob or "usa only" in loc_blob:
        breakdown["us_only"] = scoring.get("us_only", -15)

    # EU-only
    if "eu only" in loc_blob or "europe only" in loc_blob:
        breakdown["eu_only"] = scoring.get("eu_only", -10)

    # Senior management
    if any(t in name for t in ("director", "head of", "vp ", "chief", "staff principal", "principal")):
        breakdown["too_senior"] = scoring.get("senior_management_level", -15)

    # Sum
    total = sum(max(-100, min(100, v)) for v in breakdown.values())
    total = max(0, min(100, total + 30))  # baseline 30, cap 0-100

    return total, breakdown
