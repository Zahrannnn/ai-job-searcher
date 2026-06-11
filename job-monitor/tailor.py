#!/usr/bin/env python3
"""
tailor.py — Generate a tailored CV (LaTeX -> PDF) and cover letter for a
job in data/jobs.json, using the candidate's profile from profile.json.

Usage:
  python tailor.py <job_id>            # generate + compile, prints JSON
  python tailor.py --list              # list job_ids and roles
  python tailor.py --status            # print current tailor_status.json

All candidate details (name, contact, experience, education, etc.) are
read from job-monitor/profile.json. To use the same project for a
different person, copy profile.example.json to profile.json and edit it.
No LaTeX editing required.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
JOBS_FILE = ROOT / "data" / "jobs.json"
PROFILE_FILE = ROOT / "profile.json"
PROFILE_EXAMPLE = ROOT / "profile.example.json"
TEMPLATES = ROOT / "templates"
CV_DIR = ROOT / "cv"
CL_DIR = ROOT.parent / "cover_letters"
STATUS_FILE = ROOT / "data" / "tailor_status.json"

# ---------------------------------------------------------------------------
# Slug + helpers
# ---------------------------------------------------------------------------

def slug(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "_", s).strip("_")
    return (s or "unknown")[:50]


def tex_escape(s: str) -> str:
    """Escape LaTeX special characters in a string intended for text mode."""
    if not s:
        return ""
    s = s.replace("\\", r"\textbackslash{}")
    s = s.replace("&", r"\&")
    s = s.replace("%", r"\%")
    s = s.replace("$", r"\$")
    s = s.replace("#", r"\#")
    s = s.replace("_", r"\_")
    s = s.replace("{", r"\{")
    s = s.replace("}", r"\}")
    s = s.replace("~", r"\textasciitilde{}")
    s = s.replace("^", r"\textasciicircum{}")
    s = s.replace("–", "--")
    s = s.replace("—", "---")
    return s


# ---------------------------------------------------------------------------
# Profile loading
# ---------------------------------------------------------------------------

def load_profile() -> dict:
    """Load the candidate profile from profile.json, falling back to
    profile.example.json so the project still works out of the box."""
    path = PROFILE_FILE
    if not path.exists():
        if not PROFILE_EXAMPLE.exists():
            raise FileNotFoundError(
                f"profile.json not found at {PROFILE_FILE}.\n"
                f"Copy {PROFILE_EXAMPLE} to {PROFILE_FILE} and fill in your details."
            )
        print(
            f"[tailor] profile.json not found; falling back to profile.example.json",
            file=sys.stderr,
        )
        path = PROFILE_EXAMPLE
    data = json.loads(path.read_text(encoding="utf-8"))
    # Tolerate the new schema where lists are wrapped in {items: [...]} dicts
    return _normalise_profile(data)


def _normalise_profile(p: dict) -> dict:
    """The example file uses {items: [...]} for list fields so we can attach
    a _what comment. The actual profile.json uses flat lists. Normalise both
    to flat lists."""
    def _flat(field):
        if isinstance(field, dict) and "items" in field:
            return list(field["items"])
        if isinstance(field, list):
            return list(field)
        return field or []

    return {
        "identity": p.get("identity", {}),
        "core_competencies": _flat(p.get("core_competencies", [])),
        "experience": _flat(p.get("experience", [])),
        "publications": _flat(p.get("publications", [])),
        "education": _flat(p.get("education", [])),
        "languages": _flat(p.get("languages", [])),
        "awards": _flat(p.get("awards", [])),
        "references": p.get("references", "Available upon request."),
    }


# ---------------------------------------------------------------------------
# Profile-statement and cover-letter body generators (job-specific)
# ---------------------------------------------------------------------------

def generate_profile(j: dict) -> str:
    skills = [s.lower() for s in j.get("skills", [])]
    role = (j.get("name") or "").lower()
    hay = " ".join(skills) + " " + role

    stack = []
    if "react" in hay: stack.append("React")
    if "next" in hay: stack.append("Next.js")
    if "typescript" in hay: stack.append("TypeScript")
    if "javascript" in hay and "TypeScript" not in stack: stack.append("JavaScript")
    if not stack:
        stack = ["React", "TypeScript"]
    stack_str = ", ".join(stack[:3])

    has_ai = any(t in hay for t in ("ai", "llm", "ml", "nlp", "machine learning", "genai", "agent"))
    has_fullstack = "full stack" in hay or "fullstack" in hay or "backend" in hay
    is_senior = "senior" in role or "lead" in role or "principal" in role
    is_remote = "remote" in (j.get("workplace", "") + " " + j.get("location", "")).lower()

    if has_ai and has_fullstack:
        opening = "Software Engineer with production experience building AI-integrated full-stack web applications"
    elif has_ai:
        opening = "Software Engineer with production experience building AI-integrated web applications"
    elif has_fullstack:
        opening = "Software Engineer with production experience building full-stack web applications"
    else:
        opening = "Software Engineer with production experience building high-performance frontend applications"

    parts = [opening, f" with {stack_str}"]
    if is_senior:
        parts.append(" at the senior / lead level")
    parts.append(". Specialises in component-driven, accessible interfaces for ")
    parts.append("remote-first SaaS" if is_remote else "modern SaaS")
    parts.append(" environments")
    if has_ai:
        parts.append(", with hands-on experience integrating large language models, voice AI, and NLP pipelines (HuggingFace, Gemini, VAPI) into customer-facing products")
    parts.append(". Maintainer of Turjuman, an open-source Arabic AI document-translation platform. Comfortable moving between frontend (React, Next.js, TypeScript) and backend-adjacent work (Python, FastAPI, Prisma) to deliver end-to-end features in fast-paced product teams.")
    return "".join(parts)


def generate_opening(j: dict, company: str) -> str:
    role = j.get("name", "this role")
    role_l = role.lower()
    if "full stack" in role_l or "fullstack" in role_l:
        return (f"I am applying for the {role} role and would welcome the chance to discuss how my experience "
                f"shipping end-to-end features across React/Next.js and Python/Node can support {company}.")
    if "frontend" in role_l or "front-end" in role_l or "front end" in role_l:
        return (f"I am applying for the {role} position. Building polished, high-performance frontend interfaces "
                f"for production users is the work I have spent the last three years doing at RICOH Europe and NedSwiss, "
                f"and it is the work I would like to keep doing at {company}.")
    if "react" in role_l:
        return (f"I am applying for the {role} position. I have shipped React-based production interfaces across multiple "
                f"SaaS products, and I would welcome the chance to bring that experience to {company}.")
    if "web developer" in role_l or "web engineer" in role_l:
        return (f"I am applying for the {role} position. My recent work has centred on React/Next.js/TypeScript for production "
                f"SaaS and CRM products, and I am confident the same craft applies to {company}.")
    return (f"I am applying for the {role} position and would welcome the opportunity to discuss how my "
            f"production frontend engineering experience can contribute to {company}.")


def generate_bullets(j: dict) -> str:
    role = (j.get("name") or "").lower()
    skills_text = " ".join(s.lower() for s in j.get("skills", []))
    hay = role + " " + skills_text

    bullets = []
    if "react" in hay or "next" in hay or "frontend" in hay or "front-end" in hay or "front end" in hay:
        bullets.append(
            "\\item \\textbf{Production React / Next.js work.} "
            "At RICOH Europe I delivered multiple production projects under the CORELIA umbrella "
            "(real-time tailgating detection with live MJPEG streaming, a 3D building viewer with React Three Fiber, "
            "an invoice lifecycle management system, and an Arabic NLP keyword-extraction interface) "
            "all on a shared Tailwind and Shadcn UI component system. "
            "At NedSwiss I built a multilingual CRM dashboard with rich data tables, chart analytics, and role-based navigation."
        )
    if "typescript" in hay:
        bullets.append(
            "\\item \\textbf{TypeScript as default, not an afterthought.} "
            "Every project I have shipped in the last three years is TypeScript-first. "
            "I lean on Zod for runtime validation, TanStack Query for server state, and a typed component-prop pattern "
            "that has scaled across multi-developer teams at both RICOH and NedSwiss."
        )
    if "ai" in hay or "llm" in hay or "ml" in hay or "nlp" in hay:
        bullets.append(
            "\\item \\textbf{Applied AI in production.} "
            "I maintain Turjuman, an open-source AI-powered Arabic document-translation platform, "
            "and have integrated Google Gemini, HuggingFace Transformers, and VAPI voice AI into customer-facing products at RICOH. "
            "I actively use AI tooling, including Claude Code, to ship faster and write better-tested code."
        )
    if "full stack" in hay or "fullstack" in hay or "backend" in hay or "node" in hay or "python" in hay:
        bullets.append(
            "\\item \\textbf{Fluid across the stack.} "
            "Beyond React, I work comfortably in Python and FastAPI on the backend, Prisma plus PostgreSQL on the data layer, "
            "and Node.js where the project calls for it. I have shipped features end-to-end, from API contract to production frontend, "
            "in fast-moving teams."
        )
    if not bullets:
        bullets.append(
            "\\item \\textbf{Production React and Next.js work.} "
            "At RICOH Europe and NedSwiss I have shipped multiple production SaaS frontends on React 18/19, Next.js 15/16, "
            "and TypeScript, with Shadcn UI, TanStack Query, and Tailwind CSS as defaults."
        )
    bullets.append(
        "\\item \\textbf{Remote-first, multicultural collaboration.} "
        "I currently work daily with European and MENA teams in a remote-friendly setup. "
        "I communicate trade-offs clearly to product, design, and QA, and I am comfortable owning features from spec to production."
    )
    return "\n    ".join(bullets[:3])


# ---------------------------------------------------------------------------
# Profile -> LaTeX block builders
# ---------------------------------------------------------------------------

def build_competencies(profile: dict) -> str:
    items = profile.get("core_competencies", []) or []
    if not items:
        return "\\item \\textbf{Add your core competencies to profile.json}."
    parts = []
    for c in items:
        label = tex_escape(c.get("label", "").strip())
        body = tex_escape(c.get("body", "").strip())
        if not label and not body:
            continue
        parts.append(f"\\item \\textbf{{{label}}}: {body}")
    return "\n\n".join(parts) or "\\item \\textbf{Add your core competencies to profile.json}."


def build_experience(profile: dict) -> str:
    items = profile.get("experience", []) or []
    if not items:
        return "\\item{\\cventry{}{Add your experience to profile.json}{}{}{}{}{}}"
    parts = []
    for i, e in enumerate(items):
        start   = tex_escape(e.get("start", "").strip())
        end     = tex_escape(e.get("end", "").strip())
        title   = tex_escape(e.get("title", "").strip())
        company = tex_escape(e.get("company", "").strip())
        loc     = tex_escape(e.get("location", "").strip())
        bullets = e.get("bullets", []) or []

        bullet_block = "\n".join(f"    \\item {tex_escape(b.strip())}" for b in bullets if b.strip())

        # moderncv \cventry has 6 args: {date}{title}{company}{location}{country}{description}
        # We leave the country arg empty so the location arg is reused.
        # We build this as plain text (no f-strings) to avoid the
        # `{}{` parser trap with consecutive empty placeholders.
        head = "\\needspace{5\\baselineskip}\n\\item{\\cventry{"
        args = start + "--" + end + "}{" + title + "}{" + company + "}{" + loc + "}{}{"
        # The vspace group `{\vspace{1pt}` IS the description arg of
        # \cventry. The three closing braces do triple duty:
        #   1. close the inner itemize (\end{itemize})
        #   2. close the vspace group / description arg
        #   3. close \item{...}
        # (The original main_maqsam.tex uses this same 3-close pattern.)
        body = "\\vspace{1pt}\n\\begin{itemize}\n" + bullet_block + "\n\\end{itemize}}}"
        entry = head + args + body + "\n\\vspace{3pt}\n"
        parts.append(entry)
    return "\n".join(parts)


def build_publications(profile: dict) -> str:
    items = profile.get("publications", []) or []
    if not items:
        return ""
    bullets = "\n".join(f"\\item {tex_escape(p)}" for p in items if p.strip())
    return (
        "\\section{Publications \\& Open Source}\n"
        "\\vspace{1pt}\n"
        "\\begin{itemize}\n"
        f"{bullets}\n"
        "\\end{itemize}\n\n"
    )


def build_education(profile: dict) -> str:
    items = profile.get("education", []) or []
    if not items:
        return "\\item{\\cventry{}{Add your education to profile.json}{}{}{}{}{}}"
    parts = []
    for e in items:
        start   = tex_escape(e.get("start", "").strip())
        end     = tex_escape(e.get("end", "").strip())
        degree  = tex_escape(e.get("degree", "").strip())
        school  = tex_escape(e.get("school", "").strip())
        loc     = tex_escape(e.get("location", "").strip())
        details = e.get("details", []) or []
        details_text = " ".join(tex_escape(d.strip()) for d in details if d.strip())
        head = "\\item{\\cventry{"
        args = start + "--" + end + "}{" + degree + "}{" + school + "}{" + loc + "}{}{"
        # The vspace group is the description arg of \cventry.
        # Two closing braces: one closes the vspace/description group,
        # one closes \item. The original main_maqsam.tex uses 2 closes.
        body = "\\vspace{1pt}\n" + details_text + "\n}}"
        parts.append(head + args + body)
    return "\n".join(parts)


def build_languages(profile: dict) -> str:
    items = profile.get("languages", []) or []
    if not items:
        return "\\item Add your languages to profile.json."
    return "\n".join(f"\\item {tex_escape(l)}." if not l.strip().endswith(".") else f"\\item {tex_escape(l)}" for l in items if l.strip())


def build_awards(profile: dict) -> str:
    items = profile.get("awards", []) or []
    if not items:
        return ""
    # Awards are rendered as plain bolded bullets, not cventry entries.
    # This mirrors the original layout (see main_maqsam.tex) where the
    # Awards section is a single bolded line per item.
    bullets = "\n".join(f"\\item{{\\textbf{{{tex_escape(a.strip())}}}}}" for a in items if a.strip())
    return (
        "\\section{Awards}\n"
        "\\vspace{1pt}\n"
        "\\begin{itemize}\n"
        f"{bullets}\n"
        "\\end{itemize}\n\n"
    )


def build_references(profile: dict) -> str:
    ref = (profile.get("references") or "Available upon request.").strip()
    # Strip any trailing punctuation; we add the period ourselves so we
    # never end up with "Available upon request..".
    ref = ref.rstrip(". ")
    return f"\\item {tex_escape(ref)}."


# ---------------------------------------------------------------------------
# LaTeX compile
# ---------------------------------------------------------------------------

def compile_latex(tex_path: Path, engine: str) -> Path | None:
    workdir = tex_path.parent
    try:
        for _ in range(2):
            r = subprocess.run(
                [engine, "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
                cwd=workdir, capture_output=True, text=True, timeout=60,
            )
        pdf = workdir / (tex_path.stem + ".pdf")
        if pdf.exists():
            return pdf
        log = workdir / (tex_path.stem + ".log")
        if log.exists():
            err = log.read_text(encoding="utf-8", errors="ignore")[-1500:]
            print(f"[tailor] {tex_path.name} did not produce a PDF. Log tail:\n{err}", file=sys.stderr)
    except subprocess.TimeoutExpired:
        print(f"[tailor] LaTeX timed out for {tex_path.name}", file=sys.stderr)
    except FileNotFoundError:
        print(f"[tailor] {engine} not found on PATH. Is MiKTeX installed?", file=sys.stderr)
    except Exception as e:
        print(f"[tailor] LaTeX failed for {tex_path.name}: {e}", file=sys.stderr)
    return None


# ---------------------------------------------------------------------------
# Main tailor entry
# ---------------------------------------------------------------------------

def safe_company(j: dict) -> tuple[str, str, bool]:
    company = j.get("company") or ""
    is_confidential = (not company) or (company.lower() == "confidential")
    if is_confidential:
        source = j.get("source") or "unknown"
        job_id = j.get("id") or "job"
        numeric = job_id.split("-", 1)[-1] if "-" in job_id else job_id
        slug_name = f"{source}_{numeric}"
        return "your team", slug_name, True
    return company, slug(company), False


def tailor(job: dict, profile: dict) -> dict:
    company, company_slug, is_confidential = safe_company(job)
    role = job.get("name") or "this role"
    role_slug = slug(role)[:30]

    profile_statement = generate_profile(job)
    opening = generate_opening(job, company)
    bullets = generate_bullets(job)

    ident = profile["identity"]
    cover_company = "the hiring team" if is_confidential else company
    cover_closing_company = "your team" if is_confidential else company

    # Build the placeholder map for the .tex templates. All values are
    # already LaTeX-escaped.
    identity_block = {
        "FIRST_NAME":      tex_escape(ident.get("first_name", "")),
        "LAST_NAME":       tex_escape(ident.get("last_name", "")),
        "FULL_NAME":       tex_escape(ident.get("full_name", "")),
        "ADDR1":           tex_escape((ident.get("address_lines") or [""])[0]),
        "ADDR2":           tex_escape((ident.get("address_lines") or ["", ""])[1] if len(ident.get("address_lines") or []) > 1 else ""),
        "PHONE":           tex_escape(ident.get("phone", "")),
        "EMAIL":           tex_escape(ident.get("email", "")),
        "LINKEDIN_URL":    tex_escape(ident.get("linkedin_url", "")),
        "LINKEDIN_LABEL":  tex_escape(ident.get("linkedin_label", "LinkedIn")),
        "PORTFOLIO_URL":   tex_escape(ident.get("portfolio_url", "")),
        "PORTFOLIO_LABEL": tex_escape(ident.get("portfolio_label", "Portfolio")),
    }

    # Per-job values
    job_block = {
        "COMPANY":          tex_escape(company),
        "COMPANY_END":      tex_escape(cover_closing_company),
        "ROLE":             tex_escape(role),
        "PROFILE_STATEMENT": tex_escape(profile_statement),
        "OPENING":          tex_escape(opening),
        "BULLETS":          bullets,
    }

    # Profile-driven blocks
    profile_blocks = {
        "COMPETENCIES":        build_competencies(profile),
        "EXPERIENCE":          build_experience(profile),
        "PUBLICATIONS_SECTION": build_publications(profile),
        "EDUCATION":           build_education(profile),
        "LANGUAGES":           build_languages(profile),
        "AWARDS_SECTION":      build_awards(profile),
        "REFERENCES":          build_references(profile),
    }

    cv_skel   = (TEMPLATES / "cv_skeleton.tex").read_text(encoding="utf-8")
    cover_skel = (TEMPLATES / "cover_skeleton.tex").read_text(encoding="utf-8")

    cv_text = _fill_placeholders(cv_skel, {**identity_block, **job_block, **profile_blocks})
    cover_text = _fill_placeholders(cover_skel, {**identity_block, **job_block, **profile_blocks})

    # For the cover-letter greeting line, we want a friendlier salutation
    # for confidential roles: "Dear the hiring team,". The placeholder
    # COMPANY in cover_skeleton.tex is set to `cover_company` above.
    cover_text = cover_text.replace("<<COMPANY>>", tex_escape(cover_company), 1)

    CV_DIR.mkdir(exist_ok=True)
    cv_tex = CV_DIR / f"main_{company_slug}.tex"
    cv_tex.write_text(cv_text, encoding="utf-8")
    cv_pdf = compile_latex(cv_tex, engine="lualatex")

    CL_DIR.mkdir(exist_ok=True)
    cover_tex = CL_DIR / f"cover_{company_slug}_{role_slug}.tex"
    cover_tex.write_text(cover_text, encoding="utf-8")
    cover_pdf = compile_latex(cover_tex, engine="xelatex")

    return {
        "job_id": job["id"],
        "company": company,
        "role": role,
        "job_url": job.get("url", ""),
        "is_confidential": is_confidential,
        "cv_tex": str(cv_tex.relative_to(ROOT)).replace("\\", "/"),
        "cv_pdf": str(cv_pdf.relative_to(ROOT)).replace("\\", "/") if cv_pdf else None,
        "cover_tex": str(cover_tex.relative_to(ROOT.parent)).replace("\\", "/"),
        "cover_pdf": str(cover_pdf.relative_to(ROOT.parent)).replace("\\", "/") if cover_pdf else None,
    }


def _fill_placeholders(template: str, values: dict) -> str:
    out = template
    for k, v in values.items():
        out = out.replace(f"<<{k}>>", v)
    return out


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def write_status(job_id: str, status: str, **extra):
    STATUS_FILE.parent.mkdir(exist_ok=True)
    current: dict = {}
    if STATUS_FILE.exists():
        try:
            current = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        except Exception:
            current = {}
    current[job_id] = {"status": status, "updated_at": time.time(), **extra}
    STATUS_FILE.write_text(json.dumps(current, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def load_job(job_id: str) -> dict | None:
    if not JOBS_FILE.exists():
        return None
    data = json.loads(JOBS_FILE.read_text(encoding="utf-8"))
    for j in data.get("items", []):
        if j.get("id") == job_id:
            return j
    return None


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 1

    cmd = sys.argv[1]

    if cmd == "--list":
        if not JOBS_FILE.exists():
            print("no data/jobs.json", file=sys.stderr)
            return 1
        data = json.loads(JOBS_FILE.read_text(encoding="utf-8"))
        for j in data.get("items", []):
            print(f"  {j.get('id'):30s} {j.get('name', '?')[:50]:50s} @ {j.get('company', '?')[:25]}")
        return 0

    if cmd == "--status":
        if STATUS_FILE.exists():
            print(STATUS_FILE.read_text(encoding="utf-8"))
        else:
            print("{}")
        return 0

    job_id = cmd
    job = load_job(job_id)
    if not job:
        print(f"job_id {job_id!r} not found in data/jobs.json", file=sys.stderr)
        write_status(job_id, "error", message="Job not found")
        return 1

    write_status(job_id, "running", message="Generating CV and cover letter...")
    try:
        profile = load_profile()
    except FileNotFoundError as e:
        print(f"[tailor] {e}", file=sys.stderr)
        write_status(job_id, "error", message=str(e))
        return 1

    result = tailor(job, profile)
    if result.get("cv_pdf") and result.get("cover_pdf"):
        write_status(
            job_id, "done",
            message="Tailored successfully",
            cv_pdf=result.get("cv_pdf"),
            cover_pdf=result.get("cover_pdf"),
            company=result.get("company"),
            role=result.get("role"),
            job_url=result.get("job_url"),
            is_confidential=result.get("is_confidential", False),
        )
    else:
        write_status(job_id, "error", message="LaTeX compilation failed")

    print("RESULT:" + json.dumps(result))
    return 0 if result.get("cv_pdf") and result.get("cover_pdf") else 2


if __name__ == "__main__":
    sys.exit(main())
