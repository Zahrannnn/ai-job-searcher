"""Quick smoke test for the scraper sources.
Run from the job-monitor/ directory:  python test_smoke.py
"""
import json
import sys

from scraper.sources import wuzzuf, remotive, arbeitnow, jobicy


def run(name: str, fn) -> None:
    print(f"\n{'=' * 60}\n{name}\n{'=' * 60}")
    try:
        items = fn()
    except Exception as e:
        print(f"  EXCEPTION: {e}")
        return
    print(f"  Got {len(items)} items")
    for j in items[:3]:
        print(f"  - {j.get('name', '?')[:60]} @ {j.get('company', '?')[:30]}")
        print(f"    url: {j.get('url', '')[:80]}")
        print(f"    age: {j.get('age_days')}d | loc: {j.get('location', '')}")
        print(f"    skills: {j.get('skills', [])[:5]}")


if __name__ == "__main__":
    sources = sys.argv[1:] or ["wuzzuf", "remotive"]
    for s in sources:
        if s == "wuzzuf":
            run("Wuzzuf", lambda: wuzzuf.fetch(max_pages=1))
        elif s == "remotive":
            run("Remotive", remotive.fetch)
        elif s == "arbeitnow":
            run("Arbeitnow", arbeitnow.fetch)
        elif s == "jobicy":
            run("Jobicy", jobicy.fetch)
        else:
            print(f"Unknown source: {s}")
