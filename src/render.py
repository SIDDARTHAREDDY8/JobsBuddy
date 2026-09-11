"""
Station 5: WRITE PAGE  (accumulating archive)
The README is the project's landing page — hook, proof, and the newest jobs.
The live board (index.html) carries the full searchable list; the README shows
only the newest slice so it stays readable.
"""
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import json as _json

ET = ZoneInfo("America/New_York")

# how many of the newest open roles the README table shows
README_SHOW = 150


def _coverage():
    """How many companies + ATS systems we scrape (read from companies.json)."""
    try:
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "companies.json")
        c = _json.load(open(p))
        return len(c), len(set(x["ats"] for x in c))
    except Exception:
        return 0, 0


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
    return "—"


def _tier_rank(j):
    return {"high": 3, "medium": 2, "low": 1}.get(j.get("sponsor_tier"), 0)


def render_readme(jobs, profile, today):
    now = datetime.now(ET).strftime("%Y-%m-%d %I:%M %p ET")
    total = len(jobs)
    open_jobs = [j for j in jobs if j.get("open", True)]
    open_now = len(open_jobs)
    new_today = sum(1 for j in open_jobs if j.get("first_seen") == today)
    sponsors = sum(1 for j in open_jobs if j.get("sponsors_visa"))
    n_companies, n_ats = _coverage()

    newest = sorted(open_jobs,
                    key=lambda j: (j.get("first_seen") or "",
                                   j.get("sponsors_visa", False),
                                   _tier_rank(j)),
                    reverse=True)[:README_SHOW]

    L = []
    L.append("# 🌍 JobsBuddy — Visa-Sponsoring Tech Jobs for International Students")
    L.append("")
    L.append("<p align=\"center\">")
    L.append("<a href=\"https://github.com/SIDDARTHAREDDY8/JobsBuddy/stargazers\">"
             "<img src=\"https://img.shields.io/github/stars/SIDDARTHAREDDY8/JobsBuddy?"
             "style=for-the-badge&logo=github&color=gold\" alt=\"Stars\"></a>")
    L.append("<img src=\"https://img.shields.io/badge/updated-every%203%20hours-brightgreen?"
             "style=for-the-badge\" alt=\"Auto-updated\">")
    L.append(f"<img src=\"https://img.shields.io/badge/open%20jobs-{open_now}-blue?"
             "style=for-the-badge\" alt=\"Open jobs\">")
    L.append("<img src=\"https://img.shields.io/badge/cost-%240%20forever-success?"
             "style=for-the-badge\" alt=\"Free\">")
    L.append("<img src=\"https://img.shields.io/badge/license-MIT-lightgrey?"
             "style=for-the-badge\" alt=\"MIT license\">")
    L.append(f"<img src=\"https://img.shields.io/badge/companies-{n_companies}-blueviolet?"
             "style=for-the-badge\" alt=\"Companies\">")
    L.append(f"<img src=\"https://img.shields.io/badge/ATS%20systems-{n_ats}-orange?"
             "style=for-the-badge\" alt=\"ATS systems\">")
    L.append("</p>")
    L.append("")
    L.append(f"📡 **Scanning {n_companies:,} companies** across **{n_ats} ATS systems** "
             "(Greenhouse, Lever, Ashby, Workday, SmartRecruiters, Workable, Pinpoint, Breezy) "
             "— re-scraped **every 3 hours**, real posting dates only.")
    L.append("")
    L.append("> ### 🛂 Every job here is at a company with a **real H1B visa-sponsorship history.**")
    L.append("> No more applying to 500 jobs only to hear *“sorry, we don't sponsor.”*")
    L.append("")
    L.append("### 👉 **[Open the live job board ↗](https://siddarthareddy8.github.io/JobsBuddy/)**")
    L.append("")
    L.append("Search, filter by **experience level** (Entry / Mid / Senior / Lead), company, "
             "location, and sponsorship — with full job descriptions and one-click Apply.")
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
             "every few hours and keeps **only** the roles international students can "
             "actually get — **companies that sponsor visas, US-based, no security clearance, "
             "every experience level** — and posts them here, fresh, every single day. **Free, for all of us.**")
    L.append("")
    L.append("If this saves you even one wasted application, **drop a ⭐ on the repo** — it "
             "helps another international student find it too. That's the whole mission. 🙌")
    L.append("")
    L.append("## ✨ What makes this list different")
    L.append("")
    L.append("- 🛂 **Visa-sponsor verified** — tagged from real H1B filing history, not guesses")
    L.append("- 🇺🇸 **US-only & OPT-friendly** — no overseas roles wasting your time")
    L.append("- 🔒 **Zero security-clearance jobs** — auto-removed (most of us can't get them)")
    L.append("- 📊 **Every experience level** — years-of-experience tagged on every role; "
             "filter by experience on the [live board](https://siddarthareddy8.github.io/JobsBuddy/)")
    L.append("- 🆕 **Updated every 3 hours** — newest jobs always on top")
    L.append("- 💸 **100% free & open-source** — no signups, no paywalls, no catch")
    L.append("")
    L.append("## ⚙️ How it works")
    L.append("")
    L.append("```")
    L.append("Scrape → Filter → Tag → Publish (every 3 hours, fully automated)")
    L.append("```")
    L.append("")
    L.append(f"1. **Scrape** — {n_companies:,} companies across {n_ats} ATS platforms "
             "(Greenhouse, Lever, Ashby, Workday, …)")
    L.append("2. **Filter** — drops non-US roles, security-clearance jobs, staffing-firm "
             "spam, and non-software roles")
    L.append("3. **Tag** — years-of-experience extracted from each posting; H1B sponsorship "
             "history attached per company")
    L.append("4. **Publish** — this README plus the [live job board]"
             "(https://siddarthareddy8.github.io/JobsBuddy/) regenerate automatically")
    L.append("")
    L.append("Built with plain Python + GitHub Actions. No paid APIs, no servers, no database.")
    L.append("")
    L.append("## 🚀 How to use it")
    L.append("")
    L.append("1. ⭐ **Star this repo** so you can find it again (and help others find it).")
    L.append("2. 👀 **Click \"Watch\"** to get notified when new jobs drop.")
    L.append("3. 🔍 Use the **[live board](https://siddarthareddy8.github.io/JobsBuddy/)** "
             "to search and filter — the table below is just the newest slice.")
    L.append("4. 🛂 Look for the **✅ Sponsors** tag, then hit **Apply**.")
    L.append("")
    L.append("---")
    L.append("")
    L.append(f"## 🆕 Newest jobs — showing {len(newest)} of {open_now:,} open roles")
    L.append("")
    L.append(f"<sub>🔄 Last updated: **{now}** • Open now: **{open_now:,}** • "
             f"🆕 Added today: **{new_today:,}** • 🛂 At visa sponsors: **{sponsors:,}** • "
             f"[Browse all {open_now:,} on the live board →]"
             "(https://siddarthareddy8.github.io/JobsBuddy/)</sub>")
    L.append("")
    L.append("**Legend:** 🔥 = discovered in the latest scrape • ✅ Sponsors = recent H1B "
             "filing history • Posted = how long ago the company posted it • "
             "YOE = years of experience asked in the posting.")
    L.append("")
    L.append("| | Company | Role | Location | YOE | Visa | Posted | Apply |")
    L.append("|--|--|--|--|--|--|--|--|")
    for j in newest:
        flags = "🔥" if j.get("first_seen") == today else ""
        title = (j.get("title", "")).replace("|", "/")
        loc = (j.get("location") or "—").replace("|", "/")[:28]
        L.append(f"| {flags} | {j.get('company','')} | {title} | {loc} | {_yoe_cell(j)} | "
                 f"{_visa_cell(j)} | {_posted_cell(j)} | "
                 f"[Apply]({j.get('url','')}) |")
    L.append("")
    L.append(f"_Showing the {len(newest)} newest — [search and filter all {open_now:,} roles "
             "on the live board →](https://siddarthareddy8.github.io/JobsBuddy/)_")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 🤝 Contributing")
    L.append("")
    L.append("This board gets better when the community pitches in:")
    L.append("")
    L.append("- **Add a company** — know a sponsor-friendly employer we're missing? "
             "Add it to `companies.json` and open a PR.")
    L.append("- **Report a bad listing** — closed role, wrong location, doesn't sponsor? "
             "[Open an issue](https://github.com/SIDDARTHAREDDY8/JobsBuddy/issues) and "
             "it'll be filtered out.")
    L.append("- **Improve the filters** — the scraping pipeline is plain Python in `src/`; "
             "PRs welcome.")
    L.append("")
    L.append("## 🛠️ Tech stack")
    L.append("")
    L.append("- **Scraper:** Python (`requests` + ATS APIs — Greenhouse, Lever, Ashby, Workday, …)")
    L.append("- **Automation:** GitHub Actions (every 3 hours)")
    L.append("- **Frontend:** zero-dependency static page on GitHub Pages")
    L.append("- **Data:** `data/jobs.json` — the full archive, updated every run")
    L.append("")
    L.append("## ⚠️ Disclaimer")
    L.append("")
    L.append("Sponsorship tags are indicative, based on public H1B filing history — "
             "**always verify on the actual job posting** before applying. "
             "This is not legal or immigration advice.")
    L.append("")
    L.append("## 📄 License")
    L.append("")
    L.append("MIT — do whatever you want with it, just keep the credit. 🤝")
    L.append("")
    return "\n".join(L)


def _yoe_cell(j):
    lo, hi = j.get("yoe_min"), j.get("yoe_max")
    if lo is None:
        return "—"
    if hi is None:
        return f"{lo}+ yrs"
    if lo == hi:
        return f"{lo} yrs"
    return f"{lo}–{hi} yrs"


def _posted_cell(j):
    # the company's own posting age (plain text — no fire, to avoid confusion
    # with the 🔥 marker which means "discovered in the latest scrape")
    age = j.get("age_days")
    if age is None:
        return "date unknown"
    if age <= 0:
        return "today"
    if age <= 30:
        return f"{age}d ago"
    return f"{age // 30}mo ago"
