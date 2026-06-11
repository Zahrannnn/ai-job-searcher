"""
Job Monitor — main orchestrator.

Workflow:
  1. Load config + filter rules
  2. For each enabled source: fetch items
  3. Apply pre-filters (required / blocked / location / age)
  4. Score each surviving item (rule-based, 0-100)
  5. Persist to data/jobs.json + data/jobs_history.json
  6. Render Markdown report
  7. Print summary to stdout (visible in GitHub Actions log)

Usage:
  python -m scraper.main
"""
import json
import sys
import yaml
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 on Windows so the ≥, →, 🆕 characters print cleanly
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Make `scraper` importable when run as `python -m scraper.main`
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from scraper import filters
from scraper.sources import wuzzuf, bayt, remotive, jobicy, arbeitnow, vuejobs
from scraper.sources import remoteok, himalayas, linkedin
from storage.json_sync import load_existing_urls, save_run, render_markdown_report

SOURCES = {
    "wuzzuf": wuzzuf.fetch,
    "bayt": bayt.fetch,
    "remotive": remotive.fetch,
    "jobicy": jobicy.fetch,
    "arbeitnow": arbeitnow.fetch,
    "vuejobs": vuejobs.fetch,
    "remoteok": remoteok.fetch,
    "himalayas": himalayas.fetch,
    "linkedin": linkedin.fetch,
}


def _load_config() -> dict:
    cfg_path = ROOT / "config.yaml"
    return yaml.safe_load(cfg_path.read_text(encoding="utf-8"))


def _passes_pre_filter(item: dict, cfg: dict) -> bool:
    f = cfg["filters"]
    blob = f"{item.get('name','')} {item.get('description_excerpt','')} {' '.join(item.get('skills', []))}"
    if not filters.matches_required_keywords(blob, f.get("required_keywords", [])):
        return False
    if filters.has_blocked_keywords(blob, f.get("blocked_keywords", [])):
        return False
    if not filters.has_location(item.get("location", ""), item.get("workplace", ""), f.get("location_keywords", [])):
        return False
    age = item.get("age_days")
    if age is not None and age > f.get("max_age_days", 14):
        return False
    return True


def main():
    print(f"[main] Starting job monitor at {datetime.now(timezone.utc).isoformat()}")
    cfg = _load_config()
    sources_cfg = cfg.get("sources", {})

    data_path = ROOT / cfg["storage"]["data_path"]
    history_path = ROOT / cfg["storage"]["history_path"]

    # Fetch from all enabled sources
    all_items: list[dict] = []
    for name, fetch_fn in SOURCES.items():
        if not sources_cfg.get(name, True):
            print(f"[{name}] disabled — skipping")
            continue
        try:
            items = fetch_fn()
            print(f"[{name}] fetched {len(items)} items")
            all_items.extend(items)
        except Exception as e:
            print(f"[{name}] FAILED: {e}")

    # Dedupe by URL across all sources
    seen_urls, deduped = set(), []
    for it in all_items:
        url = it.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            deduped.append(it)
    print(f"[main] Unique items across sources: {len(deduped)}")

    # Pre-filter
    pre_filtered = [it for it in deduped if _passes_pre_filter(it, cfg)]
    print(f"[main] After pre-filter: {len(pre_filtered)} items")

    # Score
    scoring = cfg.get("scoring", {})
    for it in pre_filtered:
        score, breakdown = filters.score(it, scoring)
        it["score"] = score
        it["score_breakdown"] = breakdown

    # Apply min_score
    min_score = cfg["filters"].get("min_score", 0)
    scored = [it for it in pre_filtered if it.get("score", 0) >= min_score]
    print(f"[main] After min_score filter (>={min_score}): {len(scored)} items")

    # Mark new vs existing
    history_urls = load_existing_urls(history_path)
    new_count = 0
    for it in scored:
        is_new = it.get("url", "") not in history_urls
        it["is_new"] = is_new
        if is_new:
            new_count += 1
    print(f"[main] New items (not in history): {new_count}")

    # Save
    run_record = save_run(data_path, history_path, scored, new_count)
    print(f"[main] Saved {len(scored)} items to {data_path.relative_to(ROOT)}")

    # Render markdown
    md = render_markdown_report(run_record, alert_threshold=cfg["filters"].get("alert_threshold", 70))
    md_path = ROOT / "data" / "latest_report.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"[main] Rendered Markdown report to {md_path.relative_to(ROOT)}")

    # Print stdout summary
    print()
    print("=" * 60)
    print(f"SUMMARY: {len(scored)} items, {new_count} new")
    print("=" * 60)
    for it in sorted(scored, key=lambda x: x.get("score", 0), reverse=True)[:15]:
        marker = "🆕" if it.get("is_new") else "  "
        print(f"  {marker} {it.get('score', 0):3d}/100  {it.get('source','?'):12s}  {it.get('name','')[:60]:60s}  @ {it.get('company','')[:25]}")

    # Emit the new count for GitHub Actions to consume
    gh_out = ROOT / "data" / "new_count.txt"
    gh_out.write_text(str(new_count), encoding="utf-8")
    print(f"\n[main] Wrote {new_count} to {gh_out.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
