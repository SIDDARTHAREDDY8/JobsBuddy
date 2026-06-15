"""
Runs the whole pipeline:
  scrape -> filter -> tag sponsors -> score -> ARCHIVE(append new) -> write README

The board is an ACCUMULATING archive: every run, brand-new jobs are added with
today's date. Old jobs stay. The README lists everything, newest day on top.
"""
import json
import os
import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

from scrape import scrape_all
from filter import (filter_jobs, role_ok, experience_ok, needs_clearance,
                    location_ok, blocks_visa, company_blocked)
from sponsors import load_sponsors, tag_sponsors
from match import score_all
from freshness import tag_freshness, age_in_days
from render import render_readme
from render_html import render_html

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, default):
    p = os.path.join(HERE, name)
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return default


def job_key(j):
    # location-independent: one role = one stable archive entry
    raw = f"{j['company']}|{j['title']}".lower().strip()
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _fresh_enough(age, max_age, strict):
    if age is None:
        return not strict          # strict mode drops jobs we can't date
    return age <= max_age


def dedupe(jobs):
    """Collapse the same role posted across many cities into one row."""
    groups = {}
    for j in jobs:
        key = (j["company"].lower(), j["title"].strip().lower())
        if key not in groups:
            groups[key] = j
            j["_locs"] = set()
        if j.get("location"):
            groups[key]["_locs"].add(j["location"].split(";")[0].strip())
    out = []
    for j in groups.values():
        locs = sorted(l for l in j.get("_locs", set()) if l)
        if locs:
            first = locs[0][:24]
            j["location"] = first + (f"  +{len(locs)-1} more" if len(locs) > 1 else "")
        j.pop("_locs", None)        # drop the helper set (not JSON-serializable)
        out.append(j)
    return out


def main():
    profile = _load("profile.json", {})
    companies = _load("companies.json", [])

    print("① Scraping ATS feeds...")
    jobs = scrape_all(companies)
    # NOTE: The Muse aggregator was removed — it re-stamps every job with the
    # current date (fake "posted today"), so it floods the fresh section with
    # actually-outdated jobs. Incompatible with a freshness-first board.
    print(f"   total raw jobs: {len(jobs)}")

    print("② Filtering to my profile (role + 0-3 yrs + sponsor-friendly)...")
    jobs = filter_jobs(jobs, profile)
    print(f"   kept: {len(jobs)}")

    print("③ Tagging visa sponsors...")
    jobs = tag_sponsors(jobs, load_sponsors())

    print("④ Scoring match + tagging freshness...")
    jobs = score_all(jobs, profile)
    jobs = tag_freshness(jobs)

    # drop jobs posted more than N days ago (too many applicants already)
    max_age = profile.get("max_posted_age_days")
    strict = profile.get("require_known_date", False)
    if max_age is not None:
        before_age = len(jobs)
        jobs = [j for j in jobs if _fresh_enough(j.get("age_days"), max_age, strict)]
        print(f"   freshness: kept {len(jobs)} posted within {max_age} days "
              f"(dropped {before_age - len(jobs)}; strict={strict})")

    before = len(jobs)
    jobs = dedupe(jobs)
    print(f"   de-duped {before} -> {len(jobs)} unique roles")

    print("⑤ Updating the accumulating archive...")
    today = datetime.now(ET).strftime("%Y-%m-%d")
    archive = _load(os.path.join("data", "jobs.json"), {})  # {key: job}

    new_count = 0
    for j in jobs:
        k = job_key(j)
        if k in archive:
            # already known -> keep its original date, refresh live fields
            archive[k]["last_seen"] = today
            archive[k]["url"] = j["url"]
            archive[k]["location"] = j["location"]
            archive[k]["description"] = j.get("description", "")[:3000]  # refresh (trimmed)
            archive[k]["posted_at"] = j.get("posted_at", archive[k].get("posted_at", ""))
            archive[k]["open"] = True
            archive[k]["age_days"] = j.get("age_days")
            archive[k]["fresh"] = j.get("fresh", False)
        else:
            j["first_seen"] = today
            j["last_seen"] = today
            j["open"] = True
            j["description"] = j.get("description", "")[:3000]  # trim to keep file small
            archive[k] = j
            new_count += 1

    # mark jobs that didn't show up this run as no longer open (kept in archive)
    live_keys = {job_key(j) for j in jobs}
    closed = 0
    for k, j in archive.items():
        if k not in live_keys:
            if j.get("open", True):
                closed += 1
            j["open"] = False

    print(f"   added {new_count} new • {len(archive)} total in archive • {closed} now closed")

    # self-heal: purge any archived job that no longer passes current filters
    # (e.g. mis-included before a filter fix — like a "4+ years" role)
    bad = []
    for k, j in archive.items():
        blob = f"{j.get('title','')} {j.get('description','')}"
        # recompute current posting age (jobs age out of the window over time)
        age = age_in_days(j.get("posted_at"))
        too_old = (max_age is not None and not _fresh_enough(age, max_age, strict))
        # drop CLOSED jobs entirely — a job no longer in the live scrape is either
        # filled or aged out; either way you can't usefully apply, so it's clutter
        is_closed = not j.get("open", True)
        if (too_old or is_closed
                or not role_ok(j.get("title", ""), profile)
                or not experience_ok(blob, profile)
                or needs_clearance(blob, profile)
                or blocks_visa(blob, profile)
                or company_blocked(j.get("company",""), profile)
                or not location_ok(f"{j.get('location','')} {j.get('url','')}", profile)):
            bad.append(k)
    for k in bad:
        del archive[k]
    if bad:
        print(f"   🧹 purged {len(bad)} jobs (stale >{max_age}d or no longer matching filters)")

    print("⑤b Verifying Apply links are live...")
    from verify import verify_links
    dead = verify_links(list(archive.values()))
    for j in dead:
        k = job_key(j)
        archive.pop(k, None)
    if dead:
        print(f"   🔗 removed {len(dead)} jobs with dead (404) Apply links")

    print("⑥ Writing README.md + index.html (website)...")
    snapshot = list(archive.values())
    tag_sponsors(snapshot, load_sponsors())   # refresh sponsor tiers + real counts on all
    with open(os.path.join(HERE, "README.md"), "w") as f:
        f.write(render_readme(snapshot, profile, today))
    with open(os.path.join(HERE, "index.html"), "w") as f:
        f.write(render_html(snapshot, profile, today))

    # SEO: sitemap + robots so search engines crawl the site
    site = "https://siddarthareddy8.github.io/JobsBuddy/"
    with open(os.path.join(HERE, "sitemap.xml"), "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                f'  <url><loc>{site}</loc><lastmod>{today}</lastmod>'
                '<changefreq>daily</changefreq><priority>1.0</priority></url>\n'
                '</urlset>\n')
    with open(os.path.join(HERE, "robots.txt"), "w") as f:
        f.write("User-agent: *\nAllow: /\n"
                f"Sitemap: {site}sitemap.xml\n")

    with open(os.path.join(HERE, "data", "jobs.json"), "w") as f:
        json.dump(archive, f, indent=2)

    # ⑦ final self-audit: confirm NOTHING on the board violates the filters
    leaks = []
    for j in archive.values():
        blob = f"{j.get('title','')} {j.get('description','')}"
        locblob = f"{j.get('location','')} {j.get('url','')}"
        age = age_in_days(j.get("posted_at"))
        if (not role_ok(j.get("title", ""), profile)
                or not experience_ok(blob, profile)
                or not location_ok(locblob, profile)
                or needs_clearance(blob, profile)
                or blocks_visa(blob, profile)
                or company_blocked(j.get("company",""), profile)
                or (max_age is not None and age is not None and age > max_age)):
            leaks.append(f"{j.get('company')} - {j.get('title')}")
    if leaks:
        print(f"⚠️  AUDIT WARNING: {len(leaks)} job(s) on the board violate filters:")
        for l in leaks[:10]:
            print(f"      - {l}")
    else:
        print("⑦ Audit: ✅ all jobs pass role + experience + location + clearance + freshness checks")

    print(f"\n✅ Done. {new_count} new today, {len(archive)} jobs total on the board.")


if __name__ == "__main__":
    main()
