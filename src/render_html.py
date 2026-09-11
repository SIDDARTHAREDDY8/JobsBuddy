"""
Station 5b: WRITE WEBSITE (GitHub Pages)
Generates index.html — a real client-side job board for visa-sponsoring tech roles.

All filtering/sorting/pagination runs in vanilla JS over the jobs embedded as
JSON. No external JS/CSS dependencies. Strictly black-and-white SaaS aesthetic.
Every "Apply" opens in a NEW TAB (target=_blank).

Backend contract: jobs are NOT pre-filtered by experience. Each job dict carries
yoe_min (int|None) and yoe_max (int|None); profile carries
experience_years_min/max which seed the default experience filter.
"""
import os
import html
import json
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
SITE_URL = "https://siddarthareddy8.github.io/JobsBuddy/"
PAGE_SIZE = 50

TIER_LABEL = {"high": "High", "medium": "Med", "low": "Low"}


def _coverage():
    try:
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "companies.json")
        c = json.load(open(p))
        return len(c), len(set(x["ats"] for x in c))
    except Exception:
        return 0, 0


def _esc(s):
    return html.escape(str(s or ""))


def _yoe_label(j):
    """Human YOE badge. Missing values handled gracefully."""
    lo, hi = j.get("yoe_min"), j.get("yoe_max")
    if lo is None and hi is None:
        return "Not specified"
    if lo is not None and hi is not None:
        return f"{lo}\u2013{hi} yrs" if lo != hi else f"{lo} yrs"
    if lo is not None:
        return f"{lo}+ yrs"
    return f"\u2264{hi} yrs"


def _posted_label(j):
    age = j.get("age_days")
    if age is None:
        return "date unknown"
    if age <= 0:
        return "today"
    if age <= 30:
        return f"{age}d ago"
    return f"{age // 30}mo ago"


def _sponsor_badge(j):
    """(kind, label) for the sponsor badge, or (None, None) when there is no
    positive sponsorship signal — the UI then renders no badge at all,
    keeping cards calm instead of stamping "unknown" everywhere."""
    tier = j.get("sponsor_tier")
    if j.get("sponsors_visa"):
        cases = j.get("sponsor_cases")
        extra = f" \u00b7 {cases} filings" if cases else ""
        t = TIER_LABEL.get(tier, "")
        label = f"Sponsors \u00b7 {t}{extra}".strip() if t else f"Sponsors{extra}"
        return ("spon", label)
    if tier:
        return ("tier", f"Sponsor history \u00b7 {TIER_LABEL.get(tier, tier)}")
    return (None, None)


def _default_exp_preset(profile):
    """The board is YOE-agnostic: it always opens unfiltered ("any") so every
    experience level is visible; the user narrows via the filter pills."""
    return "any"


def _job_payload(j, today):
    kind, slabel = _sponsor_badge(j)
    skills = j.get("matched_skills") or []
    return {
        "title": j.get("title", ""),
        "company": j.get("company", ""),
        "location": j.get("location", ""),
        "url": j.get("url", ""),
        "description": j.get("description", "") or "",
        "age_days": j.get("age_days"),
        "posted_label": _posted_label(j),
        "yoe_min": j.get("yoe_min"),
        "yoe_max": j.get("yoe_max"),
        "yoe_label": _yoe_label(j),
        "sponsor_tier": j.get("sponsor_tier"),
        "sponsors_visa": bool(j.get("sponsors_visa")),
        "sponsor_kind": kind,
        "sponsor_label": slabel,
        "is_new": j.get("first_seen") == today,
        "is_closed": not j.get("open", True),
        "match_score": j.get("match_score", 0) or 0,
        "matched_skills": [str(s) for s in skills],
        "opt_friendly": bool(j.get("opt_friendly", True)),
    }


def _build_jsonld(jobs):
    """Structured data so Google can index the listings (Google for Jobs)."""
    items = []
    # cap to open, sponsor-friendly jobs to keep the page light
    listed = [j for j in jobs if j.get("open", True)][:120]
    for i, j in enumerate(listed, 1):
        posting = {
            "@context": "https://schema.org/",
            "@type": "JobPosting",
            "title": j.get("title", ""),
            "description": (f"{j.get('title','')} at {j.get('company','')}. "
                            f"US-based, visa-sponsor-friendly role, all experience levels. "
                            f"{(j.get('description','') or '')[:300]}"),
            "datePosted": j.get("first_seen", ""),
            "employmentType": "FULL_TIME",
            "hiringOrganization": {"@type": "Organization", "name": j.get("company", "")},
            "jobLocation": {"@type": "Place", "address": {
                "@type": "PostalAddress",
                "addressLocality": (j.get("location", "") or "United States").split(",")[0],
                "addressCountry": "US"}},
            "directApply": True,
            "url": j.get("url", ""),
        }
        items.append({"@type": "ListItem", "position": i, "item": posting})
    graph = {"@context": "https://schema.org/", "@type": "ItemList",
             "name": "OPT-friendly visa-sponsoring tech jobs", "itemListElement": items}
    return ('<script type="application/ld+json">'
            + json.dumps(graph, ensure_ascii=False) + '</script>')


def render_html(jobs, profile, today):
    now = datetime.now(ET).strftime("%b %d, %Y \u00b7 %I:%M %p ET")
    total = len(jobs)
    open_now = sum(1 for j in jobs if j.get("open", True))
    new_today = sum(1 for j in jobs if j.get("first_seen") == today)
    sponsor_n = sum(1 for j in jobs if j.get("sponsors_visa"))
    n_companies, n_ats = _coverage()

    payload = [_job_payload(j, today) for j in jobs]
    companies = sorted({p["company"] for p in payload if p["company"]})
    default_exp = _default_exp_preset(profile)

    jobs_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    companies_json = json.dumps(companies, ensure_ascii=False).replace("</", "<\\/")

    page = _PAGE
    page = page.replace("%%NOW%%", _esc(now))
    page = page.replace("%%TOTAL%%", str(total))
    page = page.replace("%%OPEN_NOW%%", str(open_now))
    page = page.replace("%%NEW_TODAY%%", str(new_today))
    page = page.replace("%%SPONSOR_N%%", str(sponsor_n))
    page = page.replace("%%N_COMPANIES%%", str(n_companies))
    page = page.replace("%%N_ATS%%", str(n_ats))
    page = page.replace("%%SITE%%", SITE_URL)
    page = page.replace("%%JSONLD%%", _build_jsonld(jobs))
    page = page.replace("%%JOBS_JSON%%", jobs_json)
    page = page.replace("%%COMPANIES_JSON%%", companies_json)
    page = page.replace("%%DEFAULT_EXP%%", default_exp)
    page = page.replace("%%PAGE_SIZE%%", str(PAGE_SIZE))
    return page


_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>JobsBuddy — Visa Sponsorship Jobs for International Students (OPT / H-1B) | SWE, AI, Data</title>
<meta name="description" content="Free, auto-updated job board of US visa-sponsoring tech jobs for international students on OPT — all experience levels. Software Engineer, AI/ML, Full-Stack & Data Engineer roles from companies with H-1B sponsorship history. Updated daily.">
<meta name="keywords" content="visa sponsorship jobs, H1B jobs, OPT jobs, international student jobs, companies that sponsor H1B, software engineer visa sponsorship, new grad jobs sponsorship, entry level tech jobs sponsor, senior engineer visa sponsorship, AI engineer jobs, data engineer jobs, CPT OPT jobs, STEM OPT jobs USA">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="author" content="Siddartha Reddy Chinthala">
<link rel="canonical" href="%%SITE%%">
<meta property="og:type" content="website">
<meta property="og:url" content="%%SITE%%">
<meta property="og:title" content="JobsBuddy — Visa-Sponsoring Tech Jobs for International Students">
<meta property="og:description" content="Free, auto-updated board of US visa-sponsoring SWE / AI / Data jobs for international students on OPT, all experience levels. Updated daily.">
<meta property="og:site_name" content="JobsBuddy">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="JobsBuddy — Visa-Sponsoring Tech Jobs for International Students">
<meta name="twitter:description" content="Free, auto-updated board of US visa-sponsoring SWE / AI / Data jobs for international students on OPT.">
<meta name="theme-color" content="#000000">
%%JSONLD%%
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--ink:#0a0a0a;--ink2:#3d3d3d;--mut:#777;--line:#e6e6e6;--line2:#111;--bg:#fff;--soft:#fafafa}
html{-webkit-font-smoothing:antialiased}
body{background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif;font-size:15px;line-height:1.55}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
a{color:inherit}
button{font-family:inherit}

/* sticky header */
header.nav{position:sticky;top:0;z-index:60;background:rgba(255,255,255,.94);backdrop-filter:blur(8px);border-bottom:1px solid var(--line2)}
.nav-in{max-width:1180px;margin:0 auto;padding:12px 22px;display:flex;align-items:center;gap:14px}
.brand{display:flex;align-items:center;gap:10px;font-weight:800;font-size:17px;letter-spacing:-.01em;white-space:nowrap}
.mark{width:26px;height:26px;border:1.5px solid var(--ink);border-radius:7px;display:grid;place-items:center;font-size:12px;font-weight:800}
.hsearch{flex:1;max-width:460px;padding:10px 14px;border:1.5px solid var(--ink);border-radius:10px;font-size:14px}
.hsearch::placeholder{color:var(--mut)}
.hcount{font-size:13px;font-weight:700;white-space:nowrap}
.hcount b{font-family:ui-monospace,Menlo,Consolas,monospace}
.nav-links{display:flex;gap:8px;align-items:center;margin-left:auto}
.btn{font-size:13px;font-weight:600;padding:8px 14px;border-radius:8px;border:1.5px solid var(--ink);text-decoration:none;white-space:nowrap;transition:.12s;background:#fff;cursor:pointer}
.btn-solid{background:var(--ink);color:#fff}.btn-solid:hover{background:#fff;color:var(--ink)}
.btn-ghost:hover{background:var(--ink);color:#fff}
#filterToggle{display:none}

/* hero — one headline, one subline, quiet stat row, then stop */
.wrap{max-width:1180px;margin:0 auto;padding:0 22px}
.hero{padding:40px 0 26px;border-bottom:1px solid var(--line)}
.eyebrow{font-size:12px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--mut)}
.hero h1{font-size:38px;line-height:1.08;letter-spacing:-.03em;margin:12px 0;max-width:22ch}
.hero p{font-size:16px;color:var(--ink2);max-width:64ch}
.stats{display:flex;flex-wrap:wrap;row-gap:14px;margin-top:22px}
.stat{padding:2px 22px;border-left:1px solid var(--line)}
.stat:first-child{border-left:0;padding-left:0}
.stat b{font-size:22px;font-weight:800;letter-spacing:-.02em;display:block;font-family:ui-monospace,Menlo,Consolas,monospace}
.stat span{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--mut)}

/* layout */
.layout{display:flex;gap:32px;align-items:flex-start;padding:30px 0 12px}
aside.filters{width:272px;flex-shrink:0;position:sticky;top:76px;max-height:calc(100vh - 96px);overflow-y:auto;border:1.5px solid var(--line2);border-radius:14px;padding:18px;background:#fff}
main.results{flex:1;min-width:0}
.f-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px}
.f-head h2{font-size:15px;font-weight:800}
.clear{background:none;border:0;font-size:12.5px;font-weight:600;color:var(--ink2);text-decoration:underline;cursor:pointer}
.f-group{margin:12px 0;padding-top:12px;border-top:1px solid var(--line)}
.f-group:first-of-type{margin-top:6px}
.f-group h3{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--mut);margin-bottom:8px;font-weight:700}
.pills{display:flex;flex-wrap:wrap;gap:8px}
.pill input{position:absolute;opacity:0;pointer-events:none}
.pill span{display:inline-block;font-size:12.5px;font-weight:600;padding:7px 13px;border-radius:999px;border:1.5px solid var(--ink);cursor:pointer;transition:.12s;background:#fff;white-space:nowrap}
.pill input:checked+span{background:var(--ink);color:#fff}
.pill input:focus-visible+span{outline:2px solid var(--ink);outline-offset:2px}
.f-input{width:100%;padding:9px 12px;border:1.5px solid var(--ink);border-radius:8px;font-size:13.5px}
.f-input::placeholder{color:var(--mut)}
.co-list{max-height:200px;overflow-y:auto;border:1px solid var(--line);border-radius:8px;padding:6px 10px;margin-top:8px}
.co-item{display:flex;align-items:center;gap:9px;padding:5px 2px;font-size:13.5px;cursor:pointer}
.co-item input{accent-color:#0a0a0a;width:15px;height:15px;flex-shrink:0}
.co-item .n{color:var(--mut);font-size:12px;margin-left:auto;font-family:ui-monospace,Menlo,Consolas,monospace}
.toggle-row{display:flex;align-items:center;justify-content:space-between;font-size:13.5px;font-weight:600;cursor:pointer}
.switch{position:relative;width:42px;height:24px;flex-shrink:0}
.switch input{opacity:0;width:0;height:0}
.sl{position:absolute;inset:0;border:1.5px solid var(--ink);border-radius:999px;transition:.15s;background:#fff}
.sl:before{content:"";position:absolute;width:16px;height:16px;left:3px;top:2.5px;background:var(--ink);border-radius:50%;transition:.15s}
.switch input:checked+.sl{background:var(--ink)}
.switch input:checked+.sl:before{transform:translateX(17px);background:#fff}

/* toolbar */
.toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:18px;flex-wrap:wrap}
.toolbar .rcount{font-size:14px;color:var(--ink2)}
.toolbar .rcount b{color:var(--ink);font-family:ui-monospace,Menlo,Consolas,monospace}
.sortsel{padding:9px 12px;border:1.5px solid var(--ink);border-radius:8px;font-size:13.5px;font-weight:600;background:#fff}

/* cards */
.card{border:1px solid var(--line);border-radius:14px;padding:22px 24px;margin-bottom:16px;cursor:pointer;background:#fff;transition:border-color .15s, background .15s}
.card:hover{background:var(--soft);border-color:var(--ink)}
.card-top{display:flex;align-items:flex-start;justify-content:space-between;gap:14px}
.job-title{font-size:17px;font-weight:700;letter-spacing:-.01em}
.job-sub{font-size:13.5px;color:var(--ink2);margin-top:5px}
.job-sub .co{font-weight:700;color:var(--ink)}
.meta{font-size:13px;color:var(--mut);margin-top:9px}
.tag{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;padding:4px 10px;border-radius:999px;border:1px solid var(--ink);white-space:nowrap}
.tag-new{background:var(--ink);color:#fff;border-color:var(--ink)}
.tag-closed{border-color:var(--mut);color:var(--mut)}
.posted{font-size:12.5px;color:var(--mut)}
.card-side{display:flex;flex-direction:column;align-items:flex-end;gap:10px;flex-shrink:0}
.apply{display:inline-block;font-size:13px;font-weight:700;padding:9px 20px;border-radius:8px;background:var(--ink);color:#fff;text-decoration:none;border:1.5px solid var(--ink);transition:.12s;white-space:nowrap;flex-shrink:0}
.apply:hover{background:#fff;color:var(--ink)}
.apply::after{content:" \\2197";font-weight:500}
.more-wrap{text-align:center;padding:18px 0 8px}
#more{font-size:14px;font-weight:700;padding:12px 34px;border-radius:10px;border:1.5px solid var(--ink);background:#fff;cursor:pointer;transition:.12s}
#more:hover{background:var(--ink);color:#fff}

/* star banner + sidebar star card */
.star-banner{display:flex;align-items:center;justify-content:center;gap:8px;background:var(--soft);border:1px solid var(--line);color:var(--ink2);font-size:13px;padding:8px 44px 8px 16px;border-radius:10px;margin:16px 0 0;position:relative;text-align:center;line-height:1.45}
.star-banner a{color:var(--ink);font-weight:700;text-decoration:underline;text-underline-offset:3px;white-space:nowrap}
.star-banner button{position:absolute;right:6px;top:50%;transform:translateY(-50%);background:none;border:0;color:var(--mut);font-size:13px;cursor:pointer;padding:8px;line-height:1}
.star-banner button:hover{color:var(--ink)}
.star-card{margin:14px 0 2px;padding:14px;border:1px solid var(--line);border-radius:12px;background:var(--soft)}
.star-card-t{font-weight:800;font-size:14px;margin-bottom:6px}
.star-card p{font-size:12.5px;color:var(--ink2);margin-bottom:12px;line-height:1.5}
.star-card .btn{display:inline-block}

/* empty state */
.empty{display:none;text-align:center;padding:70px 20px;border:1.5px dashed var(--mut);border-radius:14px}
.empty h3{font-size:20px;margin-bottom:8px}
.empty p{color:var(--ink2);margin-bottom:18px}

/* modal */
.overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:100;align-items:flex-start;justify-content:center;padding:40px 18px;overflow-y:auto}
.overlay.open{display:flex}
.modal{background:#fff;border-radius:16px;max-width:720px;width:100%;padding:30px 32px;position:relative;border:1.5px solid var(--ink)}
.modal h2{font-size:22px;letter-spacing:-.02em;padding-right:36px}
.modal .m-sub{color:var(--ink2);font-size:14px;margin:6px 0 4px}
.modal .m-meta{display:flex;align-items:center;gap:10px;margin:12px 0 4px;flex-wrap:wrap}
.m-close{position:absolute;top:16px;right:16px;width:34px;height:34px;border-radius:50%;border:1.5px solid var(--ink);background:#fff;font-size:16px;cursor:pointer;line-height:1}
.m-close:hover{background:var(--ink);color:#fff}
.m-desc{white-space:pre-wrap;font-size:14.5px;color:var(--ink2);margin:16px 0;max-height:46vh;overflow-y:auto;border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding:16px 0}
.m-skills{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 20px}
.m-skills span{font-size:12px;font-weight:600;border:1px solid var(--line2);border-radius:999px;padding:4px 12px}
.m-foot{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.m-foot .note{font-size:12px;color:var(--mut)}

footer{border-top:1px solid var(--line2);margin-top:44px;padding:26px 0 56px;color:var(--mut);font-size:12.5px}
footer a{font-weight:600}
.drawer-bg{display:none}

@media(max-width:960px){
  #filterToggle{display:inline-block}
  .nav-links .btn-ghost{display:none}
  aside.filters{position:fixed;top:0;left:0;bottom:0;width:min(320px,86vw);z-index:90;border-radius:0;border:0;border-right:1.5px solid var(--line2);max-height:none;transform:translateX(-102%);transition:transform .2s ease}
  body.drawer-open aside.filters{transform:none}
  .drawer-bg{display:none;position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:80}
  body.drawer-open .drawer-bg{display:block}
  .layout{flex-direction:column}
  main.results{width:100%}
  .hero h1{font-size:32px}
  .hsearch{max-width:none}
}
</style>
</head>
<body>

<header class="nav">
  <div class="nav-in">
    <div class="brand"><span class="mark">JB</span> JobsBuddy</div>
    <input class="hsearch" id="q" type="search" placeholder="Search title, company, or description…" autocomplete="off" aria-label="Search jobs">
    <span class="hcount" id="hcount"><b>%%TOTAL%%</b> roles</span>
    <button class="btn btn-ghost" id="filterToggle" aria-label="Open filters">Filters</button>
    <div class="nav-links">
      <a class="btn btn-ghost" href="https://github.com/SIDDARTHAREDDY8/JobsBuddy" target="_blank" rel="noopener">★ Star</a>
    </div>
  </div>
</header>

<div class="wrap">
  <div class="star-banner" id="starBanner">
    <span>JobsBuddy is free &amp; open-source — a star helps other students find it.</span>
    <a href="https://github.com/SIDDARTHAREDDY8/JobsBuddy" target="_blank" rel="noopener">★ Star on GitHub</a>
    <button id="starDismiss" aria-label="Dismiss">✕</button>
  </div>

  <section class="hero">
    <div class="eyebrow">For international students · OPT / H-1B</div>
    <h1>Tech jobs from companies that actually sponsor visas.</h1>
    <p>%%OPEN_NOW%% open roles at employers with real H-1B sponsorship history — all experience levels, no security clearance. Updated every 3 hours. Free, forever.</p>
    <div class="stats">
      <div class="stat"><b>%%OPEN_NOW%%</b><span>Open roles</span></div>
      <div class="stat"><b>%%NEW_TODAY%%</b><span>Added today</span></div>
      <div class="stat"><b>%%SPONSOR_N%%</b><span>Visa sponsors</span></div>
      <div class="stat"><b>%%N_COMPANIES%%</b><span>Companies scanned</span></div>
      <div class="stat"><b>%%N_ATS%%</b><span>ATS systems</span></div>
    </div>
  </section>

  <div class="layout">
    <div class="drawer-bg" id="drawerBg"></div>
    <aside class="filters" id="sidebar" aria-label="Job filters">
      <div class="f-head">
        <h2>Filters</h2>
        <button class="clear" id="clearAll" type="button">Clear all</button>
      </div>

      <div class="f-group">
        <h3>Experience</h3>
        <div class="pills" id="expPills" role="radiogroup" aria-label="Experience level">
          <label class="pill"><input type="radio" name="exp" value="any"><span>Any</span></label>
          <label class="pill"><input type="radio" name="exp" value="entry"><span>Entry 0–2</span></label>
          <label class="pill"><input type="radio" name="exp" value="mid"><span>Mid 2–5</span></label>
          <label class="pill"><input type="radio" name="exp" value="senior"><span>Senior 5+</span></label>
          <label class="pill"><input type="radio" name="exp" value="lead"><span>Lead 8+</span></label>
        </div>
      </div>

      <div class="f-group">
        <h3>Company</h3>
        <input class="f-input" id="coSearch" type="search" placeholder="Search companies…" autocomplete="off" aria-label="Search companies">
        <div class="co-list" id="coList"></div>
      </div>

      <div class="f-group">
        <h3>Location</h3>
        <input class="f-input" id="loc" type="search" placeholder="e.g. New York, remote…" autocomplete="off" aria-label="Filter by location">
      </div>

      <div class="f-group">
        <h3>Sponsorship</h3>
        <div class="pills" id="sponPills" role="radiogroup" aria-label="Sponsorship">
          <label class="pill"><input type="radio" name="spon" value="all"><span>All</span></label>
          <label class="pill"><input type="radio" name="spon" value="confirmed"><span>Confirmed sponsors</span></label>
          <label class="pill"><input type="radio" name="spon" value="high"><span>High tier</span></label>
          <label class="pill"><input type="radio" name="spon" value="medium"><span>Med tier</span></label>
          <label class="pill"><input type="radio" name="spon" value="low"><span>Low tier</span></label>
        </div>
      </div>

      <div class="f-group">
        <h3>Posted within</h3>
        <div class="pills" id="postedPills" role="radiogroup" aria-label="Posted within">
          <label class="pill"><input type="radio" name="posted" value="any"><span>Any time</span></label>
          <label class="pill"><input type="radio" name="posted" value="today"><span>Today</span></label>
          <label class="pill"><input type="radio" name="posted" value="d3"><span>3 days</span></label>
          <label class="pill"><input type="radio" name="posted" value="d7"><span>7 days</span></label>
        </div>
      </div>

      <div class="f-group">
        <label class="toggle-row">Remote only
          <span class="switch"><input type="checkbox" id="remote"><span class="sl"></span></span>
        </label>
      </div>

      <div class="star-card">
        <div class="star-card-t">★ Enjoying JobsBuddy?</div>
        <p>It&apos;s free and open-source. A star helps other students discover it.</p>
        <a class="btn btn-solid" href="https://github.com/SIDDARTHAREDDY8/JobsBuddy" target="_blank" rel="noopener">Star the repo</a>
      </div>
    </aside>

    <main class="results">
      <div class="toolbar">
        <span class="rcount" id="rcount"></span>
        <select class="sortsel" id="sort" aria-label="Sort jobs">
          <option value="new">Sort: Newest</option>
          <option value="match">Sort: Best match</option>
          <option value="az">Sort: Company A–Z</option>
        </select>
      </div>
      <div class="hint mono" id="legend" style="font-size:12px;color:var(--mut);margin-bottom:16px">
        NEW = added in the latest update
      </div>
      <div id="cards"></div>
      <div class="empty" id="empty">
        <h3>No roles match your filters</h3>
        <p>Try widening the experience range or clearing the search.</p>
        <button class="btn btn-solid" id="emptyClear" type="button">Clear all filters</button>
      </div>
      <div class="more-wrap"><button id="more" type="button" style="display:none">Load more</button></div>
    </main>
  </div>

  <footer>
    Last updated %%NOW%%. Built with a free Python scraper + GitHub Actions — no paid APIs.<br>
    Sourced from public ATS feeds (Greenhouse, Lever, Ashby, Workday). Sponsorship tiers are indicative — always verify on the posting.
    &nbsp;·&nbsp; <a href="https://github.com/SIDDARTHAREDDY8/JobsBuddy" target="_blank" rel="noopener">View source on GitHub</a>
  </footer>
</div>

<div class="overlay" id="overlay">
  <div class="modal" role="dialog" aria-modal="true" id="modal"></div>
</div>

<script type="application/json" id="jobs-data">%%JOBS_JSON%%</script>
<script>
(function(){
"use strict";
var JOBS = JSON.parse(document.getElementById('jobs-data').textContent);
var COMPANIES = %%COMPANIES_JSON%%;
var DEFAULT_EXP = "%%DEFAULT_EXP%%";
var PAGE_SIZE = %%PAGE_SIZE%%;

var PRESETS = {
  any:    {min: null, max: null},
  entry:  {min: 0, max: 2},
  mid:    {min: 2, max: 5},
  senior: {min: 5, max: 8},
  lead:   {min: 8, max: null}
};
var POSTED_LIM = {any: null, today: 0, d3: 3, d7: 7};
var VALID = {
  exp: ["any","entry","mid","senior","lead"],
  spon: ["all","confirmed","high","medium","low"],
  posted: ["any","today","d3","d7"],
  sort: ["new","match","az"]
};

function esc(s){
  return String(s == null ? "" : s)
    .replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

var state = {
  q: "", exp: DEFAULT_EXP, companies: null, // null = all selected
  loc: "", spon: "all", posted: "any", remote: false,
  sort: "new", shown: PAGE_SIZE
};

function readHash(){
  var h = location.hash.replace(/^#/, "");
  if(!h) return;
  var p = new URLSearchParams(h);
  if(p.get("q")) state.q = p.get("q");
  if(VALID.exp.indexOf(p.get("exp")) > -1) state.exp = p.get("exp");
  if(p.get("cox") && p.get("cox").length){
    var ex = p.getAll("cox");
    var set = new Set(COMPANIES);
    ex.forEach(function(c){ set.delete(c); });
    if(set.size && set.size < COMPANIES.length) state.companies = set;
  }
  if(p.get("loc")) state.loc = p.get("loc");
  if(VALID.spon.indexOf(p.get("spon")) > -1) state.spon = p.get("spon");
  if(VALID.posted.indexOf(p.get("posted")) > -1) state.posted = p.get("posted");
  state.remote = p.get("remote") === "1";
  if(VALID.sort.indexOf(p.get("sort")) > -1) state.sort = p.get("sort");
}

function writeHash(){
  var p = new URLSearchParams();
  if(state.q) p.set("q", state.q);
  if(state.exp !== "any") p.set("exp", state.exp);
  if(state.companies){
    var ex = COMPANIES.filter(function(c){ return !state.companies.has(c); });
    ex.forEach(function(c){ p.append("cox", c); });
  }
  if(state.loc) p.set("loc", state.loc);
  if(state.spon !== "all") p.set("spon", state.spon);
  if(state.posted !== "any") p.set("posted", state.posted);
  if(state.remote) p.set("remote", "1");
  if(state.sort !== "new") p.set("sort", state.sort);
  var s = p.toString();
  history.replaceState(null, "", s ? "#" + s : location.pathname + location.search);
}

function yoeOk(j){
  var pr = PRESETS[state.exp];
  if(pr.min == null && pr.max == null) return true;
  if(j.yoe_min != null && pr.max != null && j.yoe_min > pr.max) return false;
  if(j.yoe_max != null && pr.min != null && j.yoe_max < pr.min) return false;
  return true; // unknown YOE never filters a job out
}

function matches(j){
  if(state.q){
    var hay = (j.title + " " + j.company + " " + (j.description || "")).toLowerCase();
    if(hay.indexOf(state.q) < 0) return false;
  }
  if(!yoeOk(j)) return false;
  if(state.companies && !state.companies.has(j.company)) return false;
  if(state.loc && (j.location || "").toLowerCase().indexOf(state.loc) < 0) return false;
  if(state.spon === "confirmed" && !j.sponsors_visa) return false;
  if((state.spon === "high" || state.spon === "medium" || state.spon === "low") &&
     j.sponsor_tier !== state.spon) return false;
  var lim = POSTED_LIM[state.posted];
  if(lim != null){
    if(j.age_days == null || j.age_days > lim) return false;
  }
  if(state.remote && (j.location || "").toLowerCase().indexOf("remote") < 0) return false;
  return true;
}

function sortJobs(list){
  var arr = list.slice();
  if(state.sort === "match"){
    arr.sort(function(a,b){ return (b.match_score||0) - (a.match_score||0); });
  } else if(state.sort === "az"){
    arr.sort(function(a,b){
      return (a.company||"").localeCompare(b.company||"") ||
             (a.title||"").localeCompare(b.title||"");
    });
  } else {
    arr.sort(function(a,b){
      var x = a.age_days == null ? 99999 : a.age_days;
      var y = b.age_days == null ? 99999 : b.age_days;
      return x - y;
    });
  }
  return arr;
}

function metaLine(j){
  // one quiet line: YOE (only when known) · sponsorship (only when real) · age
  var parts = [];
  if(j.yoe_min != null || j.yoe_max != null) parts.push(j.yoe_label);
  if(j.sponsors_visa){
    var t = {high:"High",medium:"Med",low:"Low"}[j.sponsor_tier];
    parts.push("Sponsors" + (t ? " (" + t + ")" : ""));
  } else if(j.sponsor_tier){
    var t2 = {high:"High",medium:"Med",low:"Low"}[j.sponsor_tier];
    parts.push("Sponsor history" + (t2 ? " (" + t2 + ")" : ""));
  }
  parts.push(j.posted_label);
  return parts.join(" \u00b7 ");
}

function cardHtml(j, idx){
  var pill = j.is_new ? '<span class="tag tag-new">NEW</span>' : '';
  if(j.is_closed) pill += '<span class="tag tag-closed">Closed</span>';
  var apply = j.url ? '<a class="apply" href="' + esc(j.url) +
    '" target="_blank" rel="noopener noreferrer">Apply</a>' : '';
  return '<article class="card" data-i="' + idx + '">' +
    '<div class="card-top"><div>' +
      '<h3 class="job-title">' + esc(j.title) + '</h3>' +
      '<div class="job-sub"><span class="co">' + esc(j.company) + '</span> · ' +
        esc(j.location) + '</div>' +
      '<div class="meta">' + esc(metaLine(j)) + '</div>' +
    '</div><div class="card-side">' + pill + apply + '</div></div></article>';
}

var filtered = [];

function applyFilters(syncHash){
  filtered = sortJobs(JOBS.filter(matches));
  state.shown = PAGE_SIZE;
  render();
  if(syncHash !== false) writeHash();
}

function render(){
  var box = document.getElementById('cards');
  var slice = filtered.slice(0, state.shown);
  var html = "";
  for(var i = 0; i < slice.length; i++) html += cardHtml(slice[i], i);
  box.innerHTML = html;
  var n = filtered.length;
  document.getElementById('hcount').innerHTML = '<b>' + n + '</b> role' + (n === 1 ? '' : 's');
  document.getElementById('rcount').innerHTML = 'Showing <b>' + slice.length + '</b> of <b>' + n + '</b> roles';
  document.getElementById('empty').style.display = n ? 'none' : 'block';
  document.getElementById('more').style.display = (state.shown < n) ? '' : 'none';
}

function openModal(j){
  var skills = (j.matched_skills || []).map(function(s){
    return '<span>' + esc(s) + '</span>';
  }).join('');
  var apply = j.url ? '<a class="apply" href="' + esc(j.url) +
    '" target="_blank" rel="noopener noreferrer">Apply</a>' : '';
  document.getElementById('modal').innerHTML =
    '<button class="m-close" id="mclose" aria-label="Close">\u2715</button>' +
    '<h2>' + esc(j.title) + '</h2>' +
    '<div class="m-sub"><b>' + esc(j.company) + '</b> · ' + esc(j.location) + '</div>' +
    '<div class="m-meta">' +
      (j.is_new ? '<span class="tag tag-new">NEW</span>' : '') +
      '<span class="meta" style="margin-top:0">' + esc(metaLine(j)) + '</span></div>' +
    (skills ? '<div class="m-skills">' + skills + '</div>' : '') +
    '<div class="m-desc">' + esc(j.description || "No description provided.") + '</div>' +
    '<div class="m-foot">' + apply +
      '<span class="note">Sponsorship data is indicative — always verify on the posting.</span></div>';
  document.getElementById('overlay').classList.add('open');
  document.body.style.overflow = 'hidden';
  document.getElementById('mclose').onclick = closeModal;
}
function closeModal(){
  document.getElementById('overlay').classList.remove('open');
  document.body.style.overflow = '';
}

/* ---- sidebar: company checkboxes ---- */
var coCounts = {};
JOBS.forEach(function(j){ if(j.company) coCounts[j.company] = (coCounts[j.company]||0) + 1; });

function renderCompanies(filter){
  var list = document.getElementById('coList');
  var q = (filter || "").toLowerCase();
  var html = "";
  COMPANIES.forEach(function(c){
    if(q && c.toLowerCase().indexOf(q) < 0) return;
    var checked = !state.companies || state.companies.has(c);
    html += '<label class="co-item"><input type="checkbox" data-co="' + esc(c) + '"' +
      (checked ? ' checked' : '') + '><span>' + esc(c) + '</span>' +
      '<span class="n">' + (coCounts[c]||0) + '</span></label>';
  });
  list.innerHTML = html || '<div class="posted" style="padding:8px">No companies match.</div>';
}

/* ---- wire up ---- */
function setPill(groupId, name, val){
  document.querySelectorAll('#' + groupId + ' input[name="' + name + '"]').forEach(function(r){
    r.checked = (r.value === val);
  });
}
function pillVal(groupId, name){
  var r = document.querySelector('#' + groupId + ' input[name="' + name + '"]:checked');
  return r ? r.value : null;
}

function syncUIFromState(){
  document.getElementById('q').value = state.q;
  document.getElementById('loc').value = state.loc;
  document.getElementById('remote').checked = state.remote;
  document.getElementById('sort').value = state.sort;
  setPill('expPills', 'exp', state.exp);
  setPill('sponPills', 'spon', state.spon);
  setPill('postedPills', 'posted', state.posted);
  renderCompanies(document.getElementById('coSearch').value);
}

function clearAll(){
  state.q = ""; state.exp = DEFAULT_EXP; state.companies = null;
  state.loc = ""; state.spon = "all"; state.posted = "any";
  state.remote = false; state.sort = "new";
  document.getElementById('coSearch').value = "";
  syncUIFromState();
  applyFilters();
}

var qTimer = null;
document.getElementById('q').addEventListener('input', function(e){
  clearTimeout(qTimer);
  qTimer = setTimeout(function(){
    state.q = e.target.value.trim().toLowerCase();
    applyFilters();
  }, 160);
});
document.getElementById('loc').addEventListener('input', function(e){
  clearTimeout(qTimer);
  qTimer = setTimeout(function(){
    state.loc = e.target.value.trim().toLowerCase();
    applyFilters();
  }, 160);
});
document.getElementById('expPills').addEventListener('change', function(){
  state.exp = pillVal('expPills', 'exp') || 'any';
  applyFilters();
});
document.getElementById('sponPills').addEventListener('change', function(){
  state.spon = pillVal('sponPills', 'spon') || 'all';
  applyFilters();
});
document.getElementById('postedPills').addEventListener('change', function(){
  state.posted = pillVal('postedPills', 'posted') || 'any';
  applyFilters();
});
document.getElementById('remote').addEventListener('change', function(e){
  state.remote = e.target.checked;
  applyFilters();
});
document.getElementById('sort').addEventListener('change', function(e){
  state.sort = e.target.value;
  applyFilters();
});
document.getElementById('coSearch').addEventListener('input', function(e){
  renderCompanies(e.target.value);
});
document.getElementById('coList').addEventListener('change', function(e){
  var cb = e.target.closest('input[data-co]');
  if(!cb) return;
  var set = state.companies;
  if(!set){ set = new Set(COMPANIES); state.companies = set; }
  if(cb.checked) set.add(cb.getAttribute('data-co'));
  else set.delete(cb.getAttribute('data-co'));
  if(set.size === COMPANIES.length) state.companies = null; // all = default
  applyFilters();
});
document.getElementById('clearAll').addEventListener('click', clearAll);
document.getElementById('emptyClear').addEventListener('click', clearAll);
document.getElementById('more').addEventListener('click', function(){
  state.shown += PAGE_SIZE;
  render();
  writeHash();
});

/* card -> modal (delegate; Apply links unaffected) */
document.getElementById('cards').addEventListener('click', function(e){
  if(e.target.closest('a')) return;
  var card = e.target.closest('.card');
  if(!card) return;
  var j = filtered[parseInt(card.getAttribute('data-i'), 10)];
  if(j) openModal(j);
});
document.getElementById('overlay').addEventListener('click', function(e){
  if(e.target === this) closeModal();
});
document.addEventListener('keydown', function(e){
  if(e.key === 'Escape') closeModal();
});

/* mobile drawer */
document.getElementById('filterToggle').addEventListener('click', function(){
  document.body.classList.add('drawer-open');
});
document.getElementById('drawerBg').addEventListener('click', function(){
  document.body.classList.remove('drawer-open');
});

/* star banner: dismiss persists in localStorage */
(function(){
  var KEY = "jb_star_hide";
  var banner = document.getElementById('starBanner');
  try {
    if (localStorage.getItem(KEY) === "1") banner.style.display = "none";
  } catch (e) {}
  document.getElementById('starDismiss').addEventListener('click', function(){
    banner.style.display = "none";
    try { localStorage.setItem(KEY, "1"); } catch (e) {}
  });
})();

/* init */
readHash();
syncUIFromState();
applyFilters(false);
writeHash();
})();
</script>
</body>
</html>
"""
