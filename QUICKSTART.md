# Quickstart — Job Search Workspace

A workspace for running an automated, tailored frontend job-search pipeline.
The pipeline scrapes fresh roles from public job boards, scores them
against your profile, and lets you one-click generate a tailored CV and
cover letter for any match.

**You do not need to know how to code to use this.** The whole flow is:

1. Install Python and MiKTeX
2. Drop in your details in one file (`job-monitor/profile.json`)
3. Run one command
4. Open a browser

---

## 1. Prerequisites

| Tool | Why | Where to get it |
| --- | --- | --- |
| **Python 3.11+** | runs the scraper and the tailor | <https://python.org/downloads/> |
| **MiKTeX** (Windows) or **TeX Live** (Mac/Linux) | compiles CV and cover letter PDFs | <https://miktex.org/download> (Win) or `sudo apt install texlive-full` (Linux) or MacTeX (Mac) |
| **Git** | pulls this repo | <https://git-scm.com/downloads> |

The first time `lualatex` or `xelatex` runs, MiKTeX will offer to install
the small set of LaTeX packages it needs. Click "Install" on each prompt
(or run `mpm --update-db && mpm --install ...` once to pre-fetch).

## 2. Get the code

```bash
git clone https://github.com/Zahrannnn/ai-job-searcher.git
cd ai-job-searcher
```

If your friend is sharing a private fork with you, use their URL instead.

## 3. Put in your details

Open `job-monitor/profile.json` in any text editor and replace my data
with yours. The schema is documented in
`job-monitor/profile.example.json` (just read the `_what` fields and the
examples).

The fields you must fill in:

- `identity`: name, email, phone, address, LinkedIn, portfolio
- `core_competencies`: 4-6 short skill cards for the CV body
- `experience`: list of jobs (newest first), with 2-5 bullets each
- `education`: degrees in reverse-chronological order
- `publications`, `awards`, `languages`: optional lists
- `references`: one line, e.g. "Available upon request."

You do **not** need to edit any LaTeX files. The CV and cover letter are
generated automatically from `profile.json` + a job listing.

## 4. Install Python dependencies

```bash
pip install -r job-monitor/requirements.txt
```

(There are only a few: `requests`, `lxml`, `pyyaml`, `beautifulsoup4`.)

## 5. Run the dashboard

```bash
cd job-monitor
python server.py            # default port 8765
```

Then open <http://localhost:8765/dashboard.html> in your browser.

You will see:

- **Pipeline** bar at the top with a **Scrape now** button. Click it to
  trigger a fresh scrape of all job boards. The status text pulses
  while it runs and the dashboard reloads when done.
- A list of every job the monitor found, sorted by match score
  (React/Next.js/TypeScript + Cairo/Remote + fresh + 3-5 yr exp).
- For each row, a **Tailor & apply** button. Click it to:
  - generate a CV PDF and cover letter PDF tailored to that job
  - show download links for both PDFs in the same row
  - show the original **Apply now** link to the company's posting
  - let you mark the job as applied

## 6. Optional: daily cron via GitHub Actions

The repo ships with `.github/workflows/scraper.yml` that runs the scraper
once a day on GitHub's free runners and posts a GitHub Issue for every
high-match (score >= 70) job. To enable it:

1. Push your fork to GitHub.
2. Open the **Actions** tab in your fork and click "enable workflows".
3. From then on, every morning you'll get a GitHub Issue listing the
   fresh matches.

The `apply/tailor` actions are intentionally local — they need your
LaTeX toolchain to compile PDFs, so run `python server.py` on your own
machine when you want to apply.

## File map

```
ai-job-searcher/
├── QUICKSTART.md               <- you are here
├── CLAUDE.md                   <- profile used by the AI assistant
├── README.md                   <- project overview
├── cv/                         <- generated CVs land here
│   └── main_<company>.pdf
├── cover_letters/              <- generated cover letters
│   └── cover_<company>_<role>.pdf
└── job-monitor/                <- the pipeline package
    ├── profile.json            <- YOUR data lives here
    ├── profile.example.json    <- schema reference
    ├── server.py               <- the local dashboard server
    ├── tailor.py               <- CV/CL generator
    ├── dashboard.html          <- the dashboard UI
    ├── config.yaml             <- filters, scoring, sources
    ├── requirements.txt
    ├── scraper/                <- the actual scrapers
    │   ├── main.py
    │   ├── filters.py
    │   └── sources/
    │       ├── wuzzuf.py
    │       ├── remotive.py
    │       ├── jobicy.py
    │       ├── linkedin.py
    │       ├── himalayas.py
    │       ├── arbeitnow.py
    │       ├── vuejobs.py
    │       ├── bayt.py         (disabled, Cloudflare 403s)
    │       └── remoteok.py     (disabled, broken tag filter)
    ├── storage/
    │   └── json_sync.py
    ├── data/                    <- output directory
    │   ├── jobs.json
    │   ├── jobs_history.json
    │   ├── latest_report.md
    │   ├── scrape_status.json
    │   └── tailor_status.json
    └── templates/              <- parameterized LaTeX skeletons
        ├── cv_skeleton.tex
        ├── cover_skeleton.tex
        └── cover.cls
```

## Troubleshooting

- **"profile.json not found"** — copy `profile.example.json` to
  `profile.json` and edit it.
- **LaTeX compile fails with "File `cover.cls' not found"** — the cover
  letter needs `cover_letters/cover.cls` next to it. It's already
  shipped in `cover_letters/`. If you moved things, copy it back.
- **Scrape shows 0 items everywhere** — the source websites are down
  or blocking. Check `job-monitor/data/jobs.json` to see the last
  successful run.
- **Tailor produces empty PDFs** — usually a missing LaTeX package.
  Run `mpm --install <package>` (MiKTeX) or `sudo tlmgr install
  <package>` (TeX Live).
- **The Scrape button does nothing** — make sure `python server.py` is
  actually running. The browser talks to it over HTTP.

## License

This workspace includes code, LaTeX templates, and example data.
Adapt freely for your own job search.
