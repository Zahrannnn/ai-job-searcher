"""
JSON storage layer.
Stores all items + history. No external DB needed.

Layout:
  data/jobs.json          — latest run, top items by score
  data/jobs_history.json  — append-only archive (all items, all runs)
  data/latest_report.md   — human-readable summary for the workflow
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _read(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_existing_urls(path: Path) -> set[str]:
    """All URLs ever seen (from history). Used for dedup + new-tracking."""
    data = _read(path)
    history = data.get("items", [])
    return {h.get("url", "") for h in history if h.get("url")}


def save_run(
    data_path: Path,
    history_path: Path,
    items: list[dict],
    new_count: int,
) -> dict:
    """
    Persist the current run.
    - jobs.json: latest run, top items sorted by score
    - jobs_history.json: append-only, deduped by URL
    Returns the run record.
    """
    # Sort by score desc
    items_sorted = sorted(items, key=lambda x: x.get("score", 0), reverse=True)
    run_record = {
        "last_run": datetime.now(timezone.utc).isoformat(),
        "total_items": len(items),
        "new_count": new_count,
        "items": items_sorted,
    }
    _write(data_path, run_record)

    # Append to history
    history = _read(history_path)
    history_items = history.get("items", [])
    seen = {h.get("url", "") for h in history_items}
    for it in items:
        url = it.get("url", "")
        if url and url not in seen:
            seen.add(url)
            history_items.append(it)
    _write(history_path, {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_unique": len(history_items),
        "items": history_items,
    })

    return run_record


def render_markdown_report(run_record: dict, alert_threshold: int = 70, top_n: int = 25) -> str:
    """Render a human-readable Markdown report for the GitHub commit."""
    lines: list[str] = []
    lines.append(f"# Job Monitor Report")
    lines.append("")
    lines.append(f"- **Last run:** {run_record.get('last_run', 'unknown')}")
    lines.append(f"- **Total items found:** {run_record.get('total_items', 0)}")
    lines.append(f"- **New since last run:** {run_record.get('new_count', 0)}")
    lines.append(f"- **Alert threshold (score ≥ {alert_threshold}):** {sum(1 for i in run_record.get('items', []) if i.get('score', 0) >= alert_threshold)} items")
    lines.append("")

    items = run_record.get("items", [])
    high = [i for i in items if i.get("score", 0) >= alert_threshold][:top_n]
    if high:
        lines.append(f"## Top {len(high)} matches (score ≥ {alert_threshold})")
        lines.append("")
        for it in high:
            loc = it.get("location", "?")
            age = it.get("age_days")
            age_str = f"{age}d ago" if age is not None else "?"
            skills = ", ".join((it.get("skills") or [])[:5])
            lines.append(f"### {it.get('name', '')} @ {it.get('company', '')}")
            lines.append(f"- **Score:** {it.get('score', 0)}/100 — **{loc}** ({age_str}) — {it.get('workplace') or 'n/a'}")
            lines.append(f"- **Source:** {it.get('source', '?')}")
            if skills:
                lines.append(f"- **Skills:** {skills}")
            lines.append(f"- **Apply:** {it.get('url', '')}")
            if it.get("score_breakdown"):
                bd = it["score_breakdown"]
                breakdown_str = ", ".join(f"{k}={v:+d}" for k, v in bd.items())
                lines.append(f"- **Score breakdown:** {breakdown_str}")
            lines.append("")
    else:
        lines.append("## No matches above alert threshold")
        lines.append("")

    # Also list the rest briefly
    rest = [i for i in items if i.get("score", 0) < alert_threshold][:top_n]
    if rest:
        lines.append(f"## Below threshold (next {len(rest)})")
        lines.append("")
        for it in rest:
            loc = it.get("location", "?")
            lines.append(f"- **{it.get('score', 0)}/100** — {it.get('name', '')} @ {it.get('company', '')} ({loc}) — {it.get('url', '')}")
        lines.append("")

    return "\n".join(lines)
