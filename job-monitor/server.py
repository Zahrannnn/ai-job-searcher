#!/usr/bin/env python3
"""
server.py — Local HTTP server for the job-monitor dashboard.

Exposes the dashboard UI, a /api/scrape endpoint that triggers a fresh
scrape in the background, and a /api/apply/<job_id> endpoint that runs
the tailor to produce a CV and cover letter for that job.

Usage:
  python server.py [port]            # default 8765
  python server.py 9000

Then open http://localhost:<port>/dashboard.html
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
CV_DIR = ROOT / "cv"
CL_DIR = ROOT.parent / "cover_letters"  # cover letters live one dir up

SCRAPE_STATUS = DATA / "scrape_status.json"
TAILOR_STATUS = DATA / "tailor_status.json"
SCRAPE_LOCK = DATA / ".scrape.lock"
TAILOR_LOCKS = DATA / ".tailor_locks"

DATA.mkdir(exist_ok=True)
TAILOR_LOCKS.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Status writers (thread-safe via lock)
# ---------------------------------------------------------------------------

_status_lock = threading.Lock()


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_scrape_status() -> dict:
    with _status_lock:
        return _read_json(SCRAPE_STATUS, {"status": "idle"})


def set_scrape_status(status: str, **extra):
    with _status_lock:
        current = _read_json(SCRAPE_STATUS, {"status": "idle"})
        current.update({"status": status, "updated_at": time.time(), **extra})
        _write_json(SCRAPE_STATUS, current)


def get_tailor_status() -> dict:
    with _status_lock:
        return _read_json(TAILOR_STATUS, {})


def set_tailor_status(job_id: str, status: str, **extra):
    with _status_lock:
        current = _read_json(TAILOR_STATUS, {})
        current[job_id] = {"status": status, "updated_at": time.time(), **extra}
        _write_json(TAILOR_STATUS, current)


# ---------------------------------------------------------------------------
# Background jobs
# ---------------------------------------------------------------------------

def run_scrape():
    if SCRAPE_LOCK.exists():
        return False
    SCRAPE_LOCK.touch()
    set_scrape_status("running", message="Starting scraper...")
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "scraper.main"],
            cwd=ROOT, capture_output=True, text=True, timeout=600,
        )
        if proc.returncode == 0:
            set_scrape_status("done", message="Scrape complete", log_tail=proc.stdout[-1500:])
        else:
            set_scrape_status("error", message="Scraper failed", log_tail=proc.stderr[-1500:])
    except subprocess.TimeoutExpired:
        set_scrape_status("error", message="Scraper timed out after 10 minutes")
    except Exception as e:
        set_scrape_status("error", message=f"Scraper crashed: {e}")
    finally:
        SCRAPE_LOCK.unlink(missing_ok=True)
    return True


def run_tailor(job_id: str):
    lock = TAILOR_LOCKS / f"{job_id}.lock"
    if lock.exists():
        return False
    lock.touch()
    set_tailor_status(job_id, "running", message="Starting tailor...")
    try:
        proc = subprocess.run(
            [sys.executable, "tailor.py", job_id],
            cwd=ROOT, capture_output=True, text=True, timeout=180,
        )
        # Parse "RESULT:..." from stdout
        result = None
        for line in proc.stdout.splitlines():
            if line.startswith("RESULT:"):
                try:
                    result = json.loads(line[len("RESULT:"):])
                except Exception:
                    result = None
                break

        if proc.returncode == 0 and result:
            # Flatten the result onto the status entry so the dashboard can
            # read cv_pdf / cover_pdf / job_url directly.
            set_tailor_status(
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
            set_tailor_status(
                job_id, "error",
                message="Tailor failed",
                log_tail=proc.stderr[-1500:] or proc.stdout[-1500:],
            )
    except subprocess.TimeoutExpired:
        set_tailor_status(job_id, "error", message="Tailor timed out after 3 minutes")
    except Exception as e:
        set_tailor_status(job_id, "error", message=f"Tailor crashed: {e}")
    finally:
        lock.unlink(missing_ok=True)
    return True


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):  # silence default access log
        sys.stderr.write(f"[server] {self.address_string()} {fmt % args}\n")

    # ---- helpers ----
    def _send_json(self, obj, code=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path):
        if not path.exists() or not path.is_file():
            self.send_error(404, f"Not found: {path.name}")
            return
        # Basic MIME by extension
        ext = path.suffix.lower()
        mime = {
            ".html": "text/html; charset=utf-8",
            ".css":  "text/css; charset=utf-8",
            ".js":   "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".pdf":  "application/pdf",
            ".png":  "image/png",
            ".svg":  "image/svg+xml",
            ".ico":  "image/x-icon",
        }.get(ext, "application/octet-stream")
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store" if ext == ".json" else "public, max-age=60")
        self.end_headers()
        self.wfile.write(body)

    # ---- GET ----
    def do_GET(self):
        path = self.path

        if path == "/api/status":
            return self._send_json({
                "scrape": get_scrape_status(),
                "tailor": get_tailor_status(),
            })

        if path == "/" or path == "/dashboard.html":
            return self._send_file(ROOT / "dashboard.html")

        # Strip query string
        clean = path.split("?", 1)[0]

        # Serve /data/* from data/
        if clean.startswith("/data/"):
            return self._send_file(ROOT / clean.lstrip("/"))

        # Serve /cv/* from cv/
        if clean.startswith("/cv/"):
            return self._send_file(ROOT / clean.lstrip("/"))

        # Serve /cover_letters/* from parent/cover_letters/
        if clean.startswith("/cover_letters/"):
            rel = clean.lstrip("/")
            return self._send_file(ROOT.parent / rel)

        # Generic static (templates, scraper, etc.) — last resort
        return self._send_file(ROOT / clean.lstrip("/"))

    # ---- POST ----
    def do_POST(self):
        path = self.path

        if path == "/api/scrape":
            started = run_scrape()
            if not started:
                return self._send_json({"status": "running", "message": "Scrape already in progress"})
            return self._send_json({"status": "running", "message": "Scrape started"})

        m = re.match(r"^/api/apply/([^/]+)$", path)
        if m:
            job_id = m.group(1)
            started = run_tailor(job_id)
            if not started:
                return self._send_json({"status": "running", "job_id": job_id, "message": "Tailor already running"})
            return self._send_json({"status": "running", "job_id": job_id, "message": "Tailor started"})

        self.send_error(404)


# ---------------------------------------------------------------------------

def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    host = "127.0.0.1"
    print(f"\n  Job-monitor dashboard")
    print(f"  ----------------------")
    print(f"  Open:  http://{host}:{port}/dashboard.html")
    print(f"  Stop:  Ctrl+C\n")
    try:
        ThreadingHTTPServer((host, port), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")
    except OSError as e:
        if e.errno == 10048:  # address in use on Windows
            print(f"  Port {port} is busy. Try: python server.py 9000")
        raise


if __name__ == "__main__":
    main()
