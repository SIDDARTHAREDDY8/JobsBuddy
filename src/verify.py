"""
Verify Apply links are still live. Removes jobs whose link is confirmed dead
(404/410) so nobody clicks through to a missing posting.

Conservative on purpose: a network blip, timeout, or bot-block (403/405/429)
is treated as ALIVE — we only drop links the server explicitly says are gone.
"""
import json
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

UA = "Mozilla/5.0 (compatible; jobsbuddy-linkcheck/1.0)"


def _alive(url):
    if not url or not url.startswith("http"):
        return True
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status < 400
    except urllib.error.HTTPError as e:
        # HEAD is unreliable on SPA/CDN-hosted boards: Workable's global view URLs
        # (and others) return 404/405 to HEAD but 200 to a real GET. NEVER trust a
        # HEAD 404/410/405 — confirm with a GET before declaring a link dead.
        if e.code in (404, 410, 405):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=10) as r:
                    return r.status < 400
            except urllib.error.HTTPError as e2:
                return e2.code not in (404, 410)
            except Exception:
                return True
        return True                      # 403/429/etc -> assume alive
    except Exception:
        return True                      # timeout / DNS blip -> don't drop


import re as _re


def _ashby_live_ids(slug):
    """Authoritative set of LIVE job UUIDs for an Ashby company board."""
    try:
        req = urllib.request.Request(
            f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
            headers={"User-Agent": UA, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        return {j.get("jobUrl", "").rstrip("/").split("/")[-1] for j in data.get("jobs", [])}
    except Exception:
        return None        # board unreachable -> can't judge, treat all as alive


def _ashby_status(slug):
    """Ashby liveness, robust to two distinct failure modes:
      'GHOST' — the company's PUBLIC board is dead/disabled (they moved to a custom
                domain). The posting-API still serves jobs with jobs.ashbyhq.com
                URLs that 404, so EVERY link is broken. Detected by the board-root
                <title>: a live board renders '<Company> Jobs', a dead one renders
                bare 'Jobs' / 'Page not found'.
      set      — live board; the set of currently-open job UUIDs (catches filled jobs).
      None     — couldn't determine (network error) -> caller keeps the jobs.
    """
    try:
        req = urllib.request.Request(f"https://jobs.ashbyhq.com/{slug}",
                                     headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=12) as r:
            html = r.read(120000).decode("utf-8", "replace")
        m = _re.search(r"<title>([^<]*)</title>", html)
        title = (m.group(1).strip().lower() if m else "")
        if title in ("jobs", "page not found", ""):
            return "GHOST"
    except Exception:
        return None
    return _ashby_live_ids(slug)


def verify_links(jobs, workers=40):
    """Returns the list of jobs whose Apply link is confirmed dead.

    Ashby links can't be checked by HTTP status (the SPA serves 200 even for a
    removed job, landing the user on a generic 'Jobs' board). For those we verify
    the UUID against the company's LIVE Ashby board API — one fetch per company.
    Everything else uses the HTTP 404/410 check.
    """
    targets = [j for j in jobs if j.get("open", True)]
    ashby = [j for j in targets if "jobs.ashbyhq.com/" in j.get("url", "")]
    other = [j for j in targets if "jobs.ashbyhq.com/" not in j.get("url", "")]
    dead = []

    # --- Ashby: authoritative liveness via the board API (one fetch per company) ---
    by_slug = {}
    for j in ashby:
        slug = j["url"].split("jobs.ashbyhq.com/")[1].split("/")[0]
        by_slug.setdefault(slug, []).append(j)

    def _check_slug(slug):
        status = _ashby_status(slug)
        if status == "GHOST":
            return by_slug[slug]                       # public board dead -> all broken
        if status is None:
            return []                                  # unreachable -> keep all
        return [j for j in by_slug[slug]               # live board -> drop filled jobs
                if j["url"].rstrip("/").split("/")[-1] not in status]

    if by_slug:
        with ThreadPoolExecutor(max_workers=min(workers, 24)) as ex:
            for gone in ex.map(_check_slug, list(by_slug.keys())):
                dead.extend(gone)

    # --- everything else: HTTP check ---
    if other:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for j, ok in zip(other, ex.map(lambda x: _alive(x.get("url", "")), other)):
                if not ok:
                    dead.append(j)
    return dead
