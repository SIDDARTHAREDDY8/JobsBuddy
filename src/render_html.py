"""
Station 5b: WRITE WEBSITE (GitHub Pages)
Generates index.html — a polished, strictly black-&-white SaaS-style job board.
Every "Apply" opens in a NEW TAB (target=_blank), which a README cannot do.
"""
from datetime import datetime
from zoneinfo import ZoneInfo
import html
import json

ET = ZoneInfo("America/New_York")
SITE_URL = "https://siddarthareddy8.github.io/JobsBuddy/"
TIER_LABEL = {"high": "High", "medium": "Med", "low": "Low"}


def _esc(s):
    return html.escape(str(s or ""))


def _within_day_sort(j):
    tier_rank = {"high": 3, "medium": 2, "low": 1}.get(j.get("sponsor_tier"), 0)
    return (j.get("match_score", 0), j.get("sponsors_visa", False), tier_rank)


def _posted(j):
    age = j.get("age_days")
    if age is None:
        return '<span class="muted">date unknown</span>'
    if age <= 0:
        return "today"
    if age <= 30:
        return f"{age}d ago"
    return f"{age // 30}mo ago"


def render_html(jobs, profile, today):
    now = datetime.now(ET).strftime("%b %d, %Y · %I:%M %p ET")
    total = len(jobs)
    open_now = sum(1 for j in jobs if j.get("open", True))
    new_today = sum(1 for j in jobs if j.get("first_seen") == today)
    sponsor_n = sum(1 for j in jobs if j.get("sponsors_visa"))

    by_day = {}
    for j in jobs:
        by_day.setdefault(j.get("first_seen", "unknown"), []).append(j)
    days = sorted(by_day.keys(), reverse=True)

    rows = []
    for day in days:
        group = sorted(by_day[day], key=_within_day_sort, reverse=True)
        rows.append(
            f'<tr class="daysep"><td colspan="6">{_pretty(day)}'
            f'<span class="daycount">{len(group)} roles</span></td></tr>')
        for j in group:
            is_new = j.get("first_seen") == today
            new_badge = '<span class="tag tag-new">NEW</span>' if is_new else ""
            tier = j.get("sponsor_tier")
            if j.get("sponsors_visa"):
                visa = f'<span class="tag tag-spon">Sponsors · {TIER_LABEL.get(tier,"")}</span>'
            elif not j.get("opt_friendly", True):
                visa = '<span class="tag tag-warn">May not sponsor</span>'
            else:
                visa = '<span class="muted">Unknown</span>'
            closed = "" if j.get("open", True) else '<span class="tag tag-closed">Closed</span>'
            score = j.get("match_score", 0)
            url = _esc(j.get("url", "#"))
            rows.append(f"""<tr>
<td class="c-co"><span class="co">{_esc(j.get("company"))}</span>{new_badge}</td>
<td class="c-role"><div class="role">{_esc(j.get("title"))}</div>
<div class="loc">{_esc(j.get("location"))}</div></td>
<td class="c-visa">{visa}{closed}</td>
<td class="c-match"><div class="bar"><i style="width:{score}%"></i></div><span class="pct">{score}%</span></td>
<td class="c-posted">{_posted(j)}</td>
<td class="c-apply"><a class="apply" href="{url}" target="_blank" rel="noopener noreferrer">Apply</a></td>
</tr>""")

    return _PAGE.format(now=now, total=total, open_now=open_now,
                        new_today=new_today, sponsor_n=sponsor_n, site=SITE_URL,
                        rows="\n".join(rows), jsonld=_build_jsonld(jobs))


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
                            f"US-based, visa-sponsor-friendly, early-career role. "
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


def _pretty(d):
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%B %d, %Y")
    except Exception:
        return d


_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>JobsBuddy — Visa Sponsorship Jobs for International Students (OPT / H-1B) | SWE, AI, Data</title>
<meta name="description" content="Free, auto-updated job board of US visa-sponsoring tech jobs for international students on OPT. Software Engineer, AI/ML, Full-Stack & Data Engineer roles from companies with H-1B sponsorship history. Updated daily.">
<meta name="keywords" content="visa sponsorship jobs, H1B jobs, OPT jobs, international student jobs, companies that sponsor H1B, software engineer visa sponsorship, new grad jobs sponsorship, entry level tech jobs sponsor, AI engineer jobs, data engineer jobs, CPT OPT jobs, STEM OPT jobs USA">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="author" content="Siddartha Reddy Chinthala">
<link rel="canonical" href="{site}">
<meta property="og:type" content="website">
<meta property="og:url" content="{site}">
<meta property="og:title" content="JobsBuddy — Visa-Sponsoring Tech Jobs for International Students">
<meta property="og:description" content="Free, auto-updated board of US visa-sponsoring SWE / AI / Data jobs for international students on OPT. Updated daily.">
<meta property="og:site_name" content="JobsBuddy">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="JobsBuddy — Visa-Sponsoring Tech Jobs for International Students">
<meta name="twitter:description" content="Free, auto-updated board of US visa-sponsoring SWE / AI / Data jobs for international students on OPT.">
<meta name="theme-color" content="#000000">
{jsonld}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
:root{{--ink:#0a0a0a;--ink2:#3d3d3d;--mut:#777;--line:#e6e6e6;--line2:#111;--bg:#fff;--soft:#fafafa}}
html{{-webkit-font-smoothing:antialiased}}
body{{background:var(--bg);color:var(--ink);font-family:Inter,-apple-system,Segoe UI,Roboto,sans-serif;font-size:15px;line-height:1.55}}
.mono{{font-family:'JetBrains Mono',ui-monospace,monospace}}
a{{color:inherit}}

/* top nav */
header.nav{{position:sticky;top:0;z-index:50;background:rgba(255,255,255,.9);backdrop-filter:blur(8px);border-bottom:1px solid var(--line2)}}
.nav-in{{max-width:1080px;margin:0 auto;padding:14px 22px;display:flex;align-items:center;justify-content:space-between}}
.brand{{display:flex;align-items:center;gap:10px;font-weight:800;font-size:17px;letter-spacing:-.01em}}
.mark{{width:26px;height:26px;border:1.5px solid var(--ink);border-radius:7px;display:grid;place-items:center;font-size:12px;font-weight:800}}
.nav-links{{display:flex;gap:8px;align-items:center}}
.btn{{font-size:13px;font-weight:600;padding:8px 14px;border-radius:8px;border:1.5px solid var(--ink);text-decoration:none;white-space:nowrap;transition:.12s}}
.btn-solid{{background:var(--ink);color:#fff}}.btn-solid:hover{{background:#fff;color:var(--ink)}}
.btn-ghost:hover{{background:var(--ink);color:#fff}}

/* hero */
.wrap{{max-width:1080px;margin:0 auto;padding:0 22px}}
.hero{{padding:54px 0 30px;border-bottom:1px solid var(--line)}}
.eyebrow{{font-size:12px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--mut)}}
.hero h1{{font-size:46px;line-height:1.05;letter-spacing:-.03em;margin:14px 0 14px;max-width:18ch}}
.hero p{{font-size:18px;color:var(--ink2);max-width:60ch}}
.metrics{{display:flex;gap:0;margin-top:30px;border:1px solid var(--line2);border-radius:12px;overflow:hidden;width:fit-content;max-width:100%;flex-wrap:wrap}}
.metric{{padding:16px 26px;border-right:1px solid var(--line)}}
.metric:last-child{{border-right:0}}
.metric b{{font-size:26px;font-weight:800;letter-spacing:-.02em;display:block}}
.metric span{{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--mut)}}

/* why strip */
.why{{padding:26px 0;border-bottom:1px solid var(--line);color:var(--ink2);max-width:78ch}}
.why b{{color:var(--ink)}}

/* controls */
.controls{{position:sticky;top:57px;background:var(--bg);padding:18px 0 10px;z-index:40}}
.search{{width:100%;padding:13px 16px;border:1.5px solid var(--ink);border-radius:10px;font-size:15px;font-family:inherit}}
.search::placeholder{{color:var(--mut)}}
.hint{{font-size:12.5px;color:var(--mut);margin-top:9px;display:flex;gap:18px;flex-wrap:wrap}}
.hint .k{{color:var(--ink);font-weight:600}}

/* table */
table{{width:100%;border-collapse:collapse}}
thead th{{text-align:left;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--mut);font-weight:600;padding:10px 10px;border-bottom:1.5px solid var(--ink);position:sticky;top:116px;background:var(--bg)}}
tbody td{{padding:15px 10px;border-bottom:1px solid var(--line);vertical-align:middle}}
tbody tr:hover{{background:var(--soft)}}
tr.daysep td{{background:var(--ink);color:#fff;font-weight:700;font-size:13px;letter-spacing:.02em;padding:8px 14px;border:0}}
tr.daysep .daycount{{float:right;font-weight:500;color:#cfcfcf;font-size:12px}}
.c-co{{white-space:nowrap}}
.co{{font-weight:700}}
.role{{font-weight:500}}
.loc{{font-size:12.5px;color:var(--mut);margin-top:2px}}

/* tags / pills */
.tag{{display:inline-block;font-size:10.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;padding:3px 8px;border-radius:999px;border:1.5px solid var(--ink);white-space:nowrap}}
.tag-new{{background:var(--ink);color:#fff;margin-left:8px}}
.tag-spon{{background:#fff;color:var(--ink)}}
.tag-warn{{border-style:dashed;color:var(--ink2)}}
.tag-closed{{border-color:var(--mut);color:var(--mut);margin-left:6px}}
.muted{{color:var(--mut);font-size:12.5px}}

/* match bar */
.c-match{{white-space:nowrap}}
.bar{{display:inline-block;width:64px;height:6px;background:#ececec;border-radius:999px;overflow:hidden;vertical-align:middle}}
.bar i{{display:block;height:100%;background:var(--ink)}}
.pct{{font-family:'JetBrains Mono',monospace;font-size:12.5px;font-weight:600;margin-left:9px;vertical-align:middle}}
.c-posted{{font-size:13px;color:var(--mut);white-space:nowrap}}

/* apply */
.apply{{display:inline-block;font-size:13px;font-weight:700;padding:8px 18px;border-radius:8px;background:var(--ink);color:#fff;text-decoration:none;border:1.5px solid var(--ink);transition:.12s}}
.apply:hover{{background:#fff;color:var(--ink)}}
.apply::after{{content:" ↗";font-weight:500}}

footer{{border-top:1px solid var(--line2);margin-top:40px;padding:26px 0 50px;color:var(--mut);font-size:12.5px}}
footer a{{font-weight:600}}
@media(max-width:720px){{
  .hero h1{{font-size:34px}}
  .c-match,.c-posted{{display:none}}
  thead th.h-match,thead th.h-posted{{display:none}}
}}
</style>
</head>
<body>

<header class="nav">
  <div class="nav-in">
    <div class="brand"><span class="mark">JB</span> JobsBuddy</div>
    <div class="nav-links">
      <a class="btn btn-ghost" href="https://github.com/SIDDARTHAREDDY8/JobsBuddy/subscription" target="_blank" rel="noopener">Watch</a>
      <a class="btn btn-solid" href="https://github.com/SIDDARTHAREDDY8/JobsBuddy" target="_blank" rel="noopener">★ Star on GitHub</a>
    </div>
  </div>
</header>

<div class="wrap">
  <section class="hero">
    <div class="eyebrow">For international students · OPT / H-1B</div>
    <h1>Tech jobs from companies that actually sponsor visas.</h1>
    <p>An auto-updated board of US-based Software, AI &amp; Data roles — filtered to early-career,
       no security clearance, and only employers with a real H-1B sponsorship history. Free, forever.</p>
    <div class="metrics">
      <div class="metric"><b class="mono">{open_now}</b><span>Open roles</span></div>
      <div class="metric"><b class="mono">{new_today}</b><span>Added today</span></div>
      <div class="metric"><b class="mono">{sponsor_n}</b><span>Visa sponsors</span></div>
      <div class="metric"><b class="mono">$0</b><span>Cost forever</span></div>
    </div>
  </section>

  <section class="why">
    <b>Why this exists.</b> You tailor an application, hit submit, and <i>then</i> find out the company
    won&apos;t sponsor a visa — with the OPT clock ticking. JobsBuddy scans top tech employers every few
    hours and keeps <b>only</b> the roles international students can realistically get. If it saves you one
    wasted application, <b>star the repo</b> so another student finds it too.
  </section>

  <div class="controls">
    <input class="search" id="q" placeholder="Search company, role, or location — e.g. “AI”, “remote”, “New York”" onkeyup="filt()">
    <div class="hint">
      <span><span class="k">NEW</span> = added in the latest update</span>
      <span><span class="k">Sponsors</span> = real H-1B filing history</span>
      <span><span class="k">Apply</span> opens in a new tab</span>
    </div>
  </div>

  <table id="tbl">
    <thead><tr>
      <th>Company</th><th>Role</th><th>Visa</th>
      <th class="h-match">Match</th><th class="h-posted">Posted</th><th>Apply</th>
    </tr></thead>
    <tbody>
{rows}
    </tbody>
  </table>

  <footer>
    Last updated {now}. Built with a free Python scraper + GitHub Actions — no paid APIs.<br>
    Sourced from public ATS feeds (Greenhouse, Lever, Ashby, Workday). Sponsorship tiers are indicative — always verify on the posting.
    &nbsp;·&nbsp; <a href="https://github.com/SIDDARTHAREDDY8/JobsBuddy" target="_blank" rel="noopener">View source on GitHub</a>
  </footer>
</div>

<script>
function filt(){{
  var q=document.getElementById('q').value.toLowerCase();
  document.querySelectorAll('#tbl tbody tr').forEach(function(r){{
    if(r.classList.contains('daysep')){{r.style.display='';return;}}
    r.style.display = r.innerText.toLowerCase().indexOf(q)>-1 ? '' : 'none';
  }});
}}
</script>
</body>
</html>
"""
