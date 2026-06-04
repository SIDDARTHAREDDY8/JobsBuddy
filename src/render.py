"""
Station 5: WRITE PAGE  (accumulating archive)
Lists EVERY job ever found, grouped by the date it was added.
Newest day on top, older days below. Within a day: sponsors + best match first.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

BADGE = {"high": "✅ Sponsors (High)", "medium": "✅ Sponsors (Med)", "low": "✅ Sponsors (Low)"}


def _visa_cell(job):
    if job.get("sponsors_visa"):
        return BADGE.get(job.get("sponsor_tier"), "✅ Sponsors")
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

    # group by the date a job was first added
    by_day = {}
    for j in jobs:
        by_day.setdefault(j.get("first_seen", "unknown"), []).append(j)
    days = sorted(by_day.keys(), reverse=True)   # newest day first

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
    L.append("</p>")
    L.append("")
    L.append("> ### 🛂 Every job here is at a company with a **real H1B visa-sponsorship history.**")
    L.append("> No more applying to 500 jobs only to hear *“sorry, we don’t sponsor.”*")
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
    L.append("**Legend:** ✅ Sponsors = recent H1B filing history • 🆕 = added today • "
             "🔒 = no longer listed (kept for history) • Match % = how strong a fit the role is.")
    L.append("")
    L.append("---")
    L.append("")

    for day in days:
        group = sorted(by_day[day], key=_within_day_sort, reverse=True)
        nice = _pretty_date(day)
        L.append(f"## 🗓️ {nice} — {len(group)} jobs")
        L.append("")
        L.append("| | Company | Role | Location | Visa | Match | Added | Status | Apply |")
        L.append("|--|--|--|--|--|--|--|--|--|")
        for j in group:
            flag = "🆕" if j.get("first_seen") == today else ""
            title = (j.get("title", "")).replace("|", "/")
            loc = (j.get("location") or "—").replace("|", "/")[:28]
            status = "Open" if j.get("open", True) else "🔒 Closed"
            added = _pretty_date(j.get("first_seen", "")) if j.get("first_seen") else "—"
            L.append(f"| {flag} | {j.get('company','')} | {title} | {loc} | "
                     f"{_visa_cell(j)} | **{j.get('match_score', 0)}%** | {added} | {status} | "
                     f"[Apply]({j.get('url','')}) |")
        L.append("")

    L.append("<sub>Built with a free Python scraper + GitHub Actions — no paid APIs. "
             "Sponsorship tiers are indicative; verify on the posting. "
             "Closed roles are kept for history. Data from public ATS feeds "
             "(Greenhouse, Lever, Ashby, Workday).</sub>")
    L.append("")
    return "\n".join(L)


def _pretty_date(d):
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%B %d, %Y")
    except Exception:
        return d
