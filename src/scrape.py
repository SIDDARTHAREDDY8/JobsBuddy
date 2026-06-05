"""
Station 1: SCRAPE
Pulls open jobs from company ATS feeds (Greenhouse, Lever, Ashby).
Uses only the Python standard library -- no pip installs needed.
Every adapter returns a list of normalized dicts:
  { company, title, location, url, description, posted_at, source }
"""
import json
import html as _html
import urllib.request
import urllib.error

UA = "opt-friendly-jobs/1.0 (+https://github.com/SIDDARTHAREDDY8)"
TIMEOUT = 20


def _get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


# ---------- Greenhouse ----------
def scrape_greenhouse(slug, company):
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    data = _get_json(url)
    out = []
    for j in data.get("jobs", []):
        loc = (j.get("location") or {}).get("name", "")
        out.append({
            "company": company,
            "title": j.get("title", ""),
            "location": loc,
            "url": j.get("absolute_url", ""),
            "description": _strip_html(j.get("content", "")),
            "posted_at": j.get("updated_at", "") or j.get("first_published", ""),
            "source": "greenhouse",
        })
    return out


# ---------- Lever ----------
def scrape_lever(slug, company):
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    data = _get_json(url)
    out = []
    for j in data:
        cats = j.get("categories", {}) or {}
        # Lever keeps the intro in description, but the REQUIREMENTS /
        # RESPONSIBILITIES bullets live in `lists` -> must include them,
        # otherwise we can't see things like "4+ years of experience".
        parts = [j.get("descriptionPlain", "") or j.get("description", "")]
        for lst in j.get("lists", []) or []:
            parts.append(lst.get("text", ""))      # section heading
            parts.append(lst.get("content", ""))   # the bullets (HTML)
        parts.append(j.get("additionalPlain", "") or j.get("additional", ""))
        full = " ".join(p for p in parts if p)
        out.append({
            "company": company,
            "title": j.get("text", ""),
            "location": cats.get("location", ""),
            "url": j.get("hostedUrl", ""),
            "description": _strip_html(full),
            "posted_at": "",
            "source": "lever",
        })
    return out


# ---------- Ashby ----------
def scrape_ashby(slug, company):
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=false"
    data = _get_json(url)
    out = []
    for j in data.get("jobs", []):
        out.append({
            "company": company,
            "title": j.get("title", ""),
            "location": j.get("location", "") or j.get("locationName", ""),
            "url": j.get("jobUrl", "") or j.get("applyUrl", ""),
            "description": _strip_html(j.get("descriptionPlain", "") or j.get("description", "")),
            "posted_at": j.get("publishedAt", ""),
            "source": "ashby",
        })
    return out


# ---------- Workday ----------
def scrape_workday(slug, company, fetch_detail=True, max_detail=80):
    # slug format: "tenant|dc|site"  e.g. "nvidia|wd5|NVIDIAExternalCareerSite"
    tenant, dc, site = slug.split("|")
    base = f"https://{tenant}.{dc}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
    cxs = f"https://{tenant}.{dc}.myworkdayjobs.com/wday/cxs/{tenant}/{site}"
    host = f"https://{tenant}.{dc}.myworkdayjobs.com/en-US/{site}"
    out, offset = [], 0
    for _ in range(5):  # up to 5 pages (100 jobs) per company
        body = json.dumps({"limit": 20, "offset": offset, "searchText": ""}).encode()
        req = urllib.request.Request(base, data=body,
                                     headers={"User-Agent": UA, "Content-Type": "application/json",
                                              "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        postings = data.get("jobPostings", [])
        if not postings:
            break
        for j in postings:
            path = j.get("externalPath", "")
            desc = j.get("title", "")
            loc = j.get("locationsText", "")
            posted = j.get("postedOn", "")
            # fetch the full job detail (real location + description + experience reqs)
            if fetch_detail and len(out) < max_detail and path:
                info = _workday_detail(cxs + path)
                if info:
                    desc = info.get("description", desc)
                    loc = info.get("location", loc) or loc
                    posted = info.get("posted", posted) or posted
            out.append({
                "company": company,
                "title": j.get("title", ""),
                "location": loc,
                "url": host + path,
                "description": desc,
                "posted_at": posted,
                "source": "workday",
            })
        offset += 20
        if offset >= data.get("total", 0):
            break
    return out


def _workday_detail(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            info = json.loads(r.read().decode("utf-8", "replace")).get("jobPostingInfo", {})
        # gather all locations (primary + additional) so foreign ones are visible
        locs = [info.get("location", "")]
        locs += info.get("additionalLocations", []) or []
        return {
            "description": _strip_html(info.get("jobDescription", "")),
            "location": "; ".join(l for l in locs if l),
            "posted": info.get("startDate", "") or info.get("postedOn", ""),
        }
    except Exception:
        return None


def _strip_html(s):
    if not s:
        return ""
    import re
    s = re.sub(r"<[^>]+>", " ", s)
    s = _html.unescape(s)          # decode ALL entities incl. numeric (&#43; -> +)
    return re.sub(r"\s+", " ", s).strip()


ADAPTERS = {
    "greenhouse": scrape_greenhouse,
    "lever": scrape_lever,
    "ashby": scrape_ashby,
    "workday": scrape_workday,
}


def scrape_all(companies):
    jobs = []
    for c in companies:
        fn = ADAPTERS.get(c["ats"])
        if not fn:
            continue
        try:
            got = fn(c["slug"], c["company"])
            jobs.extend(got)
            print(f"  [ok]   {c['company']:<14} ({c['ats']}) -> {len(got)} jobs")
        except urllib.error.HTTPError as e:
            print(f"  [skip] {c['company']:<14} ({c['ats']}) HTTP {e.code}")
        except Exception as e:
            print(f"  [skip] {c['company']:<14} ({c['ats']}) {type(e).__name__}")
    return jobs
