# Job Monitor — Daily Frontend Job Scraper

A daily cron that scrapes frontend job boards (Wuzzuf, Bayt, Remotive, Jobicy,
Arbeitnow, VueJobs) and surfaces the best matches to Mohamed's profile.

- **Rule-based scoring** (no LLM API key required) — fast, deterministic, fully tunable
- **Local JSON storage** (no Notion / Supabase setup) — easy to grep, easy to back up
- **GitHub Actions daily cron** — runs free, no infra
- **GitHub Issue alert** when new high-score (≥70/100) items are found

## Architecture

```
job-monitor/
├── config.yaml                  # Tunable filters, scoring weights
├── profile/context.md           # Mohamed's profile (read by future AI)
├── scraper/
│   ├── main.py                  # Orchestrator
│   ├── filters.py               # Pre-filter + score engine
│   └── sources/                 # One file per data source
│       ├── wuzzuf.py            # HTML scraper
│       ├── bayt.py              # HTML scraper (often 403)
│       ├── remotive.py          # JSON API
│       ├── jobicy.py            # JSON API
│       ├── arbeitnow.py         # JSON API
│       └── vuejobs.py           # HTML scraper
├── storage/
│   └── json_sync.py             # Local JSON storage
├── data/                        # Output (committed back to repo)
│   ├── jobs.json                # Latest run, top items
│   ├── jobs_history.json        # Append-only archive
│   └── latest_report.md         # Human-readable summary
├── requirements.txt
└── .github/workflows/scraper.yml
```

## Quick start (local)

```bash
cd job-monitor
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m scraper.main
```

The first run will write `data/jobs.json` and `data/latest_report.md`.

## Deploy to GitHub Actions

1. **Push to GitHub** (private or public repo).
2. **No secrets required** — the cron uses only public APIs and HTML scraping.
3. The workflow at `.github/workflows/scraper.yml` will run daily at **06:00 UTC = 08:00 Cairo**.
4. On each run, the workflow:
   - Scrapes all enabled sources
   - Scores and dedupes items
   - Commits `data/jobs.json` and `data/latest_report.md` back to the repo
   - **Creates a GitHub Issue** if any new items score ≥ 70 (so you get a notification)

To adjust the schedule: edit the `cron:` line in `.github/workflows/scraper.yml`.

## Configuration

Edit `config.yaml`:

```yaml
filters:
  required_keywords: [react, next.js, typescript, ...]
  blocked_keywords: [".net", "ios native", ...]
  location_keywords: [cairo, remote, egypt, ...]
  max_age_days: 7
  min_score: 30
  alert_threshold: 70     # score ≥ this → GitHub Issue

sources:
  wuzzuf: true
  bayt: true
  remotive: true
  jobicy: true
  arbeitnow: true
  vuejobs: true

scoring:
  stack_match_react: 25
  stack_match_nextjs: 15
  # ... tune all weights
```

## Scoring (0-100)

- Baseline 30
- **Positive**: React (+25), Next.js (+15), TypeScript (+10), Cairo/Remote (+20), ≤3d (+15), AI/ML (+10), 3-5yr exp (+10), founding role (+10)
- **Negative**: blocked in title (-50), Vue-only (-20), Angular-only (-30), iOS/Android only (-40), internship (-30), 5+yr req (-10)

Full breakdown stored in `score_breakdown` per item.

## Dashboard

Open `dashboard.html` in a browser to see today's matches with filters,
trends, and one-click apply links. The file is fully static and reads
`data/jobs.json` + `data/jobs_history.json` at load.

To serve it locally (so the data fetch works under `file://` is blocked
by most browsers):

```bash
cd job-monitor
python -m http.server 8765
# open http://localhost:8765/dashboard.html
```

For a hosted view: enable GitHub Pages on the repo, set the source to
the `master` branch and `/` (root) — the dashboard is at
`/job-monitor/dashboard.html`.

## Adding a new source

1. Create `scraper/sources/<name>.py` with a `fetch() -> list[dict]` function.
2. Each item should be a dict with at least: `name`, `company`, `url`, `location`, `workplace`, `date_posted`, `age_days` (optional), `skills` (list).
3. Register it in `SOURCES` dict in `scraper/main.py`.
4. Toggle it in `config.yaml` under `sources:`.
5. Add a test scrape locally.

## Cost

- **$0** — all sources are public, no API keys, no LLM calls
- GitHub Actions: unlimited for public repos; 2,000 min/month for free private
- Each run takes ~30 seconds

## Roadmap

- [ ] LLM enrichment (Gemini Flash) for deeper skill matching
- [ ] Email digest (daily) instead of GitHub Issue
- [ ] Slack/Discord webhook support
- [ ] Auto-tailored cover-letter drafts for ≥80-score matches
- [ ] Feedback learning (mark item as "applied" / "skipped" → retrain)
