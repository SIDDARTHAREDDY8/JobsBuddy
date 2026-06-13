"""
Station 5: WRITE PAGE  (accumulating archive)
Lists EVERY job ever found, grouped by the date it was added.
Newest day on top, older days below. Within a day: sponsors + best match first.
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from freshness import age_in_days
import os
import json as _json

ET = ZoneInfo("America/New_York")


def _coverage():
    """How many companies + ATS systems we scrape (read from companies.json)."""
    try:
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "companies.json")
        c = _json.load(open(p))
        return len(c), len(set(x["ats"] for x in c))
    except Exception:
        return 0, 0


def _age_bucket(j):
    """Group jobs by how long ago they were POSTED (freshest first)."""
    a = age_in_days(j.get("posted_at"))
    if a is None:
        return (99, "🗓️ Posted: date unknown")
    if a <= 0:
        return (0, "🔥 Posted Today")
    if a == 1:
        return (1, "🔥 Posted Yesterday")
    return (a, f"🗓️ Posted {a} days ago")

BADGE = {"high": "✅ Sponsors (High)", "medium": "✅ Sponsors (Med)", "low": "✅ Sponsors (Low)"}


def _visa_cell(job):
    if job.get("sponsors_visa"):
        base = BADGE.get(job.get("sponsor_tier"), "✅ Sponsors")
        cases = job.get("sponsor_cases")
        if cases:
            return f"{base} · {cases} H1B filings"
        return base
    if not job.get("opt_friendly", True):
        return "⚠️ May not sponsor"
    return "— unknown"


def _within_day_sort(j):
    tier_rank = {"high": 3, "medium": 2, "low": 1}.get(j.get("sponsor_tier"), 0)
    return (j.get("sponsors_visa", False), tier_rank, j.get("match_score", 0))


def render_readme(jobs, profile, today):
    now = datetime.now(ET).strftime("%Y-%m-%d %I:%M %p ET")
    total = len(jobs)
    open_now = sum(1 for j in jobs if j.get("open", True))
    new_today = sum(1 for j in jobs if j.get("first_seen") == today)

    # group by POSTING freshness (freshest first) so brand-new jobs are on top,
    # not by when we happened to discover them
    by_age = {}
    for j in jobs:
        rank, label = _age_bucket(j)
        by_age.setdefault((rank, label), []).append(j)
    buckets = sorted(by_age.keys())   # rank ascending = freshest first, unknown last

    L = []
    L.append("# 🌍 JobsBuddy — Visa-Sponsoring Tech Jobs for International Students")
    L.append("")
    L.append("<p align=\"center\">")
    L.append("<a href=\"https://github.com/SIDDARTHAREDDY8/JobsBuddy/stargazers\">"
             "<img src=\"https://img.shields.io/github/stars/SIDDARTHAREDDY8/JobsBuddy?"
             "style=for-the-badge&logo=github&color=gold\" alt=\"Stars\"></a>")
    L.append("<img src=\"https://img.shields.io/badge/updated-every%206%20hours-brightgreen?"
             "style=for-the-badge\" alt=\"Auto-updated\">")
    L.append(f"<img src=\"https://img.shields.io/badge/open%20jobs-{open_now}-blue?"
             "style=for-the-badge\" alt=\"Open jobs\">")
    L.append("<img src=\"https://img.shields.io/badge/cost-%240%20forever-success?"
             "style=for-the-badge\" alt=\"Free\">")
    n_companies, n_ats = _coverage()
    L.append(f"<img src=\"https://img.shields.io/badge/companies-{n_companies}-blueviolet?"
             "style=for-the-badge\" alt=\"Companies\">")
    L.append(f"<img src=\"https://img.shields.io/badge/ATS%20systems-{n_ats}-orange?"
             "style=for-the-badge\" alt=\"ATS systems\">")
    L.append("</p>")
    L.append("")
    L.append(f"📡 **Scanning {n_companies:,} companies** across **{n_ats} ATS systems** "
             "(Greenhouse, Lever, Ashby, Workday, SmartRecruiters, Workable, Pinpoint, Breezy) "
             "+ The Muse aggregator — re-scraped **every 6 hours.**")
    L.append("")
    L.append("> ### 🛂 Every job here is at a company with a **real H1B visa-sponsorship history.**")
    L.append("> No more applying to 500 jobs only to hear *“sorry, we don’t sponsor.”*")
    L.append("")
    L.append("### 👉 **[Open the live job board ↗](https://siddarthareddy8.github.io/JobsBuddy/)** "
             "— cleaner UI, search bar, and **Apply opens in a new tab.**")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 💭 Why I built this")
    L.append("")
    L.append("I'm an international student. If you are too, you know the feeling: you spend "
             "hours tailoring an application, hit submit, and *then* find out the company "
             "won't sponsor a visa. Multiply that by hundreds of applications and a ticking "
             "**OPT clock**, and the job hunt stops being about skill — it becomes about luck "
             "and information you don't have.")
    L.append("")
    L.append("So I built a robot to fix the information part. It scans top tech companies "
             "every few hours, keeps **only** the roles that international students can "
             "actually get — **companies that sponsor visas, US-based, no security clearance, "
             "early-career** — and posts them here, fresh, every single day. **Free, for all of us.**")
    L.append("")
    L.append("If this saves you even one wasted application, **drop a ⭐ on the repo** — it "
             "helps another international student find it too. That's the whole mission. 🙌")
    L.append("")
    L.append("## ✨ What makes this list different")
    L.append("")
    L.append("- 🛂 **Visa-sponsor verified** — tagged from real H1B filing history, not guesses")
    L.append("- 🇺🇸 **US-only & OPT-friendly** — no overseas roles wasting your time")
    L.append("- 🔒 **Zero security-clearance jobs** — auto-removed (most of us can't get them)")
    L.append("- 🎓 **Early-career focused** — 0–3 years, no senior/staff noise")
    L.append("- 🆕 **Updated every 6 hours** — newest jobs always on top, with the date added")
    L.append("- 💸 **100% free & open-source** — no signups, no paywalls, no catch")
    L.append("")
    L.append("## 🚀 How to use it")
    L.append("")
    L.append("1. ⭐ **Star this repo** so you can find it again (and help others find it).")
    L.append("2. 👀 **Click \"Watch\"** to get notified when new jobs drop.")
    L.append("3. 📋 Scroll the table below — newest jobs are at the top.")
    L.append("4. 🛂 Look for the **✅ Sponsors** tag, then hit **Apply**.")
    L.append("")
    L.append(f"<sub>🔄 Last updated: **{now}** • Total roles tracked: **{total}** • "
             f"Open now: **{open_now}** • 🆕 Added today: **{new_today}**</sub>")
    L.append("")
    L.append("**Legend:** 🔥 NEW = added in the latest update (older jobs lose this automatically) • "
             "✅ Sponsors = recent H1B filing history • 🔒 = no longer listed • "
             "Posted = how long ago the company posted it • Match % = how strong a fit the role is.")
    L.append("")
    L.append("---")
    L.append("")

    for rank, label in buckets:
        group = sorted(by_age[(rank, label)], key=_within_day_sort, reverse=True)
        L.append(f"## {label} — {len(group)} jobs")
        L.append("")
        L.append("| | Company | Role | Location | Visa | Match | Posted | Apply |")
        L.append("|--|--|--|--|--|--|--|--|")
        for j in group:
            flags = "🔥" if rank <= 1 else ""   # fire on Today/Yesterday postings
            title = (j.get("title", "")).replace("|", "/")
            loc = (j.get("location") or "—").replace("|", "/")[:28]
            L.append(f"| {flags} | {j.get('company','')} | {title} | {loc} | "
                     f"{_visa_cell(j)} | **{j.get('match_score', 0)}%** | {_posted_cell(j)} | "
                     f"[Apply]({j.get('url','')}) |")
        L.append("")

    L.append("<sub>Built with a free Python scraper + GitHub Actions — no paid APIs. "
             "Sponsorship tiers are indicative; verify on the posting. "
             "Closed roles are kept for history. Data from public ATS feeds "
             "(Greenhouse, Lever, Ashby, Workday).</sub>")
    L.append("")
    return "\n".join(L)


def _posted_cell(j):
    # the company's own posting age (plain text — no fire, to avoid confusion
    # with the 🔥 NEW marker which means "added to this board in the latest update")
    age = j.get("age_days")
    if age is None:
        return "date unknown"
    if age <= 0:
        return "today"
    if age <= 30:
        return f"{age}d ago"
    return f"{age // 30}mo ago"


def _pretty_date(d):
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%B %d, %Y")
    except Exception:
        return d
