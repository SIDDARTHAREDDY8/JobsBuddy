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

# ISO-3166 country codes -> full name, so the location filter (which matches
# full country names) catches foreign jobs. ATS like SmartRecruiters/Recruitee
# return the country as a 2-letter code (e.g. "vn"), which would otherwise slip
# past a name-based block list.
ISO_COUNTRY = {
    "us": "United States", "usa": "United States",
    "vn": "Vietnam", "in": "India", "ca": "Canada", "gb": "United Kingdom",
    "uk": "United Kingdom", "fr": "France", "de": "Germany", "es": "Spain",
    "it": "Italy", "nl": "Netherlands", "be": "Belgium", "ch": "Switzerland",
    "at": "Austria", "ie": "Ireland", "pt": "Portugal", "se": "Sweden",
    "no": "Norway", "dk": "Denmark", "fi": "Finland", "pl": "Poland",
    "cz": "Czechia", "ro": "Romania", "hu": "Hungary", "gr": "Greece",
    "ua": "Ukraine", "ru": "Russia", "tr": "Turkey", "il": "Israel",
    "ae": "United Arab Emirates", "sa": "Saudi Arabia", "qa": "Qatar",
    "eg": "Egypt", "za": "South Africa", "ng": "Nigeria", "ke": "Kenya",
    "jp": "Japan", "cn": "China", "kr": "South Korea", "tw": "Taiwan",
    "hk": "Hong Kong", "sg": "Singapore", "my": "Malaysia", "th": "Thailand",
    "ph": "Philippines", "id": "Indonesia", "au": "Australia", "nz": "New Zealand",
    "br": "Brazil", "mx": "Mexico", "ar": "Argentina", "cl": "Chile",
    "co": "Colombia", "pe": "Peru", "cr": "Costa Rica", "lk": "Sri Lanka",
    "bd": "Bangladesh", "pk": "Pakistan", "np": "Nepal", "bg": "Bulgaria",
    "hr": "Croatia", "rs": "Serbia", "si": "Slovenia", "sk": "Slovakia",
    "ee": "Estonia", "lt": "Lithuania", "lv": "Latvia", "lu": "Luxembourg",
}


def _country_name(code):
    return ISO_COUNTRY.get((code or "").strip().lower(), code)


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
            # use first_published (REAL posting date), NOT updated_at (last edit) —
            # otherwise months-old jobs that got re-touched look "fresh"
            "posted_at": j.get("first_published", "") or j.get("updated_at", ""),
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
            # Lever gives createdAt as epoch milliseconds (age_in_days parses it)
            "posted_at": str(j.get("createdAt", "")) if j.get("createdAt") else "",
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


import re as _re
_WD_TITLE_HINT = _re.compile(r"engineer|developer|programmer|software|\bsde\b|\bswe\b|"
                             r"data |machine learning|\bml\b|\bai\b|scientist|full stack|"
                             r"front.?end|back.?end|devops|sre|cloud|platform")
# search terms to surface relevant roles in large Workday job boards
_WD_SEARCH_TERMS = ["software engineer", "software developer", "data engineer",
                    "machine learning", "ai engineer", "full stack developer",
                    "backend", "frontend"]


# ---------- Workday ----------
def scrape_workday(slug, company, fetch_detail=True, max_detail=70):
    # slug format: "tenant|dc|site"  e.g. "nvidia|wd5|NVIDIAExternalCareerSite"
    tenant, dc, site = slug.split("|")
    base = f"https://{tenant}.{dc}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
    cxs = f"https://{tenant}.{dc}.myworkdayjobs.com/wday/cxs/{tenant}/{site}"
    host = f"https://{tenant}.{dc}.myworkdayjobs.com/en-US/{site}"

    # Big companies (banks/enterprises) have 100s-1000s of jobs. Fetching only the
    # first 60 in default order misses most software roles. Instead, SEARCH by
    # keyword so we find relevant roles wherever they are in a huge job board.
    out, seen, detail_count = [], set(), 0
    for term in _WD_SEARCH_TERMS:
        offset = 0
        for _ in range(2):  # up to 40 results per search term
            body = json.dumps({"limit": 20, "offset": offset, "searchText": term}).encode()
            try:
                req = urllib.request.Request(base, data=body,
                    headers={"User-Agent": UA, "Content-Type": "application/json",
                             "Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                    data = json.loads(r.read().decode("utf-8", "replace"))
            except Exception:
                break
            postings = data.get("jobPostings", [])
            if not postings:
                break
            for j in postings:
                path = j.get("externalPath", "")
                if not path or path in seen:
                    continue
                seen.add(path)
                desc = j.get("title", "")
                loc = j.get("locationsText", "")
                # Workday URL path embeds the location: /job/{Location}/{Title}_{ReqID}
                # Use it when locationsText is empty or vague ("2 Locations"), so the
                # location filter can see foreign jobs (Taguig, São Paulo, etc.)
                if not loc or _re.match(r"^\d+\s+locations?$", loc.strip(), _re.I):
                    segs = path.strip("/").split("/")
                    if len(segs) >= 2 and segs[0] == "job":
                        loc = segs[1].replace("---", ", ").replace("--", " ").replace("-", " ").strip()
                posted = j.get("postedOn", "")
                relevant = _WD_TITLE_HINT.search(j.get("title", "").lower())
                if fetch_detail and relevant and detail_count < max_detail:
                    info = _workday_detail(cxs + path)
                    if info:
                        desc = info.get("description", desc)
                        loc = info.get("location", loc) or loc
                        posted = info.get("posted", posted) or posted
                        detail_count += 1
                out.append({
                    "company": company, "title": j.get("title", ""),
                    "location": loc, "url": host + path,
                    "description": desc, "posted_at": posted, "source": "workday",
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


# ---------- SmartRecruiters ----------
def scrape_smartrecruiters(slug, company, max_detail=60):
    base = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
    out, offset = [], 0
    for _ in range(3):
        data = _get_json(f"{base}?limit=100&offset={offset}")
        content = data.get("content", [])
        if not content:
            break
        for p in content:
            loc = p.get("location", {}) or {}
            locstr = ", ".join(x for x in [loc.get("city", ""), loc.get("region", ""),
                                           _country_name(loc.get("country", ""))] if x)
            desc = p.get("name", "")
            if len(out) < max_detail:
                try:
                    d = _get_json(f"{base}/{p.get('id','')}")
                    secs = (d.get("jobAd", {}) or {}).get("sections", {}) or {}
                    desc = " ".join(_strip_html((secs.get(k, {}) or {}).get("text", ""))
                                    for k in ("jobDescription", "qualifications", "responsibilities"))
                except Exception:
                    pass
            out.append({
                "company": company, "title": p.get("name", ""),
                "location": locstr,
                "url": f"https://jobs.smartrecruiters.com/{slug}/{p.get('id','')}",
                "description": desc, "posted_at": p.get("releasedDate", ""),
                "source": "smartrecruiters",
            })
        offset += 100
        if offset >= data.get("totalFound", 0):
            break
    return out


# ---------- Workable ----------
def scrape_workable(slug, company):
    url = f"https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true"
    data = _get_json(url)
    out = []
    for j in data.get("jobs", []):
        locstr = ", ".join(x for x in [j.get("city", ""), j.get("state", ""),
                                       j.get("country", "")] if x)
        out.append({
            "company": company, "title": j.get("title", ""),
            "location": locstr,
            "url": j.get("url", "") or j.get("application_url", ""),
            "description": _strip_html(j.get("description", "") + " " + j.get("requirements", "")),
            "posted_at": j.get("published_on", "") or j.get("created_at", ""),
            "source": "workable",
        })
    return out


# ---------- Recruitee ----------
def scrape_recruitee(slug, company):
    url = f"https://{slug}.recruitee.com/api/offers/"
    data = _get_json(url)
    out = []
    for o in data.get("offers", []):
        locstr = ", ".join(x for x in [o.get("city", ""), _country_name(o.get("country_code", ""))] if x)
        out.append({
            "company": company, "title": o.get("title", ""),
            "location": o.get("location", "") or locstr,
            "url": o.get("careers_url", "") or o.get("careers_apply_url", ""),
            "description": _strip_html(o.get("description", "") + " " + o.get("requirements", "")),
            "posted_at": o.get("published_at", ""),
            "source": "recruitee",
        })
    return out


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
    "smartrecruiters": scrape_smartrecruiters,
    "workable": scrape_workable,
    "recruitee": scrape_recruitee,
}


def _scrape_one(c):
    fn = ADAPTERS.get(c["ats"])
    if not fn:
        return (c, [], "no-adapter")
    try:
        return (c, fn(c["slug"], c["company"]), "ok")
    except urllib.error.HTTPError as e:
        return (c, [], f"HTTP{e.code}")
    except Exception as e:
        return (c, [], type(e).__name__)


def scrape_all(companies, workers=20):
    """Scrape all companies concurrently (fast at 1000+ companies)."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    jobs, ok, failed = [], 0, 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(_scrape_one, c) for c in companies]
        for i, f in enumerate(as_completed(futs), 1):
            c, got, status = f.result()
            if got:
                jobs.extend(got)
                ok += 1
            elif status != "ok":
                failed += 1
            if i % 100 == 0:
                print(f"  ...scraped {i}/{len(companies)} companies, {len(jobs)} raw jobs so far")
    print(f"  scrape complete: {ok} companies returned jobs, {failed} failed/empty, {len(jobs)} raw jobs")
    return jobs
