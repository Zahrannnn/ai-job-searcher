#!/usr/bin/env python3
"""
tailor.py — Generate a tailored CV (LaTeX -> PDF) and cover letter for a
job in data/jobs.json.

Usage:
  python tailor.py <job_id>            # generate + compile, prints JSON
  python tailor.py --list              # list job_ids and roles
  python tailor.py --status            # print current tailor_status.json
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
JOBS_FILE = ROOT / "data" / "jobs.json"
TEMPLATES = ROOT / "templates"
CV_DIR = ROOT / "cv"
# Cover letters live one directory up (alongside cv/), to match the existing
# project layout where cover_letters/ is a sibling of job-monitor/.
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
    # Order matters: backslash first
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
    s = s.replace("–", "--")  # en-dash -> LaTeX en-dash
    s = s.replace("—", "---")  # em-dash -> LaTeX em-dash
    return s


def load_job(job_id: str) -> dict | None:
    if not JOBS_FILE.exists():
        return None
    data = json.loads(JOBS_FILE.read_text(encoding="utf-8"))
    for j in data.get("items", []):
        if j.get("id") == job_id:
            return j
    return None


def safe_company(j: dict) -> tuple[str, str, bool]:
    """Return (display_name, slug, is_confidential).

    Confidential companies are addressed as "your team" in the cover letter
    and "the company" in the CV; the slug uses source + numeric id to keep
    cover-letter filenames unique and short."""
    company = j.get("company") or ""
    is_confidential = (not company) or (company.lower() == "confidential")
    if is_confidential:
        source = j.get("source") or "unknown"
        job_id = j.get("id") or "job"
        numeric = job_id.split("-", 1)[-1] if "-" in job_id else job_id
        slug_name = f"{source}_{numeric}"
        return "your team", slug_name, True
    return company, slug(company), False


# ---------------------------------------------------------------------------
# Profile statement generator
# ---------------------------------------------------------------------------

def generate_profile(j: dict) -> str:
    """Build a 1-paragraph profile statement tailored to the role."""
    skills = [s.lower() for s in j.get("skills", [])]
    role = (j.get("name") or "").lower()
    hay = " ".join(skills) + " " + role

    # Identify stack focus
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
    parts.append(". Specialises in component-driven, accessible interfaces for")
    parts.append("remote-first SaaS" if is_remote else "modern SaaS")
    parts.append(" environments")
    if has_ai:
        parts.append(", with hands-on experience integrating large language models, voice AI, and NLP pipelines (HuggingFace, Gemini, VAPI) into customer-facing products")
    parts.append(". Maintainer of Turjuman, an open-source Arabic AI document-translation platform. Comfortable moving between frontend (React, Next.js, TypeScript) and backend-adjacent work (Python, FastAPI, Prisma) to deliver end-to-end features in fast-paced product teams.")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Cover letter generators
# ---------------------------------------------------------------------------

def generate_opening(j: dict, company: str) -> str:
    role = j.get("name", "this role")
    role_l = role.lower()
    role_l_stripped = re.sub(r"^(senior|junior|mid|lead|principal|staff)\s+", "", role_l)

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
    # generic
    return (f"I am applying for the {role} position and would welcome the opportunity to discuss how my "
            f"production frontend engineering experience can contribute to {company}.")


def generate_bullets(j: dict) -> str:
    role = (j.get("name") or "").lower()
    skills_text = " ".join(s.lower() for s in j.get("skills", []))
    hay = role + " " + skills_text

    bullets: list[str] = []

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

    # Always include the collaboration bullet as a closer
    bullets.append(
        "\\item \\textbf{Remote-first, multicultural collaboration.} "
        "I currently work daily with European and MENA teams in a remote-friendly setup. "
        "I communicate trade-offs clearly to product, design, and QA, and I am comfortable owning features from spec to production."
    )

    return "\n    ".join(bullets[:3])


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
        # Tail the log for diagnostics
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

def tailor(job: dict) -> dict:
    company, company_slug, is_confidential = safe_company(job)
    role = job.get("name") or "this role"
    # Keep role slug short (≤30 chars) so cover letter filenames stay under
    # the OS command-line limit when combined with the company slug.
    role_slug = slug(role)[:30]

    profile = generate_profile(job)
    opening = generate_opening(job, company)
    bullets = generate_bullets(job)

    # For the cover letter, use a confidential-safe company label.
    cover_company = "the hiring team" if is_confidential else company
    cover_closing_company = "your team" if is_confidential else company

    # Escape ALL substituted text for LaTeX
    company_tex = tex_escape(company)  # CV: uses the real name (or "your team")
    cover_company_tex = tex_escape(cover_company)
    cover_closing_company_tex = tex_escape(cover_closing_company)
    role_tex = tex_escape(role)
    profile_tex = tex_escape(profile)
    opening_tex = tex_escape(opening)

    # ---- CV
    cv_skel = (TEMPLATES / "cv_skeleton.tex").read_text(encoding="utf-8")
    cv_text = (cv_skel
        .replace("{{COMPANY}}", company_tex)
        .replace("{{ROLE}}", role_tex)
        .replace("{{PROFILE}}", profile_tex)
    )
    CV_DIR.mkdir(exist_ok=True)
    cv_tex = CV_DIR / f"main_{company_slug}.tex"
    cv_tex.write_text(cv_text, encoding="utf-8")
    cv_pdf = compile_latex(cv_tex, engine="lualatex")

    # ---- Cover letter
    cover_skel = (TEMPLATES / "cover_skeleton.tex").read_text(encoding="utf-8")
    cover_text = (cover_skel
        .replace("{{COMPANY}}", cover_company_tex)               # "Dear the hiring team,"
        .replace("{{COMPANY_END}}", cover_closing_company_tex)  # "your team" / real name in closing
        .replace("{{ROLE}}", role_tex)
        .replace("{{OPENING}}", opening_tex)
        .replace("{{BULLETS}}", bullets)
    )
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
        # CV lives inside job-monitor/, so the URL is /cv/<filename>
        "cv_tex": str(cv_tex.relative_to(ROOT)).replace("\\", "/"),
        "cv_pdf": str(cv_pdf.relative_to(ROOT)).replace("\\", "/") if cv_pdf else None,
        # Cover letter lives at the project root, so the URL is /cover_letters/<filename>
        "cover_tex": str(cover_tex.relative_to(ROOT.parent)).replace("\\", "/"),
        "cover_pdf": str(cover_pdf.relative_to(ROOT.parent)).replace("\\", "/") if cover_pdf else None,
    }


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
    result = tailor(job)
    # Persist the result into the status entry so the dashboard can
    # render PDF download links without re-querying the disk.
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

    # JSON result on stdout for the server to parse
    print("RESULT:" + json.dumps(result))
    return 0 if result.get("cv_pdf") and result.get("cover_pdf") else 2


if __name__ == "__main__":
    sys.exit(main())
