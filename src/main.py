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
from filter import filter_jobs, role_ok, experience_ok, needs_clearance, location_ok
from sponsors import load_sponsors, tag_sponsors
from match import score_all
from freshness import tag_freshness
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
    print(f"   total raw jobs: {len(jobs)}")

    print("② Filtering to my profile (role + 0-3 yrs + sponsor-friendly)...")
    jobs = filter_jobs(jobs, profile)
    print(f"   kept: {len(jobs)}")

    print("③ Tagging visa sponsors...")
    jobs = tag_sponsors(jobs, load_sponsors())

    print("④ Scoring match + tagging freshness...")
    jobs = score_all(jobs, profile)
    jobs = tag_freshness(jobs)

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
            archive[k]["open"] = True
            archive[k]["age_days"] = j.get("age_days")
            archive[k]["fresh"] = j.get("fresh", False)
        else:
            j["first_seen"] = today
            j["last_seen"] = today
            j["open"] = True
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
        if (not role_ok(j.get("title", ""), profile)
                or not experience_ok(blob, profile)
                or needs_clearance(blob, profile)
                or not location_ok(j.get("location", ""), profile)):
            bad.append(k)
    for k in bad:
        del archive[k]
    if bad:
        print(f"   🧹 purged {len(bad)} jobs that no longer match the filters")

    print("⑥ Writing README.md + index.html (website)...")
    snapshot = list(archive.values())
    with open(os.path.join(HERE, "README.md"), "w") as f:
        f.write(render_readme(snapshot, profile, today))
    with open(os.path.join(HERE, "index.html"), "w") as f:
        f.write(render_html(snapshot, profile, today))

    with open(os.path.join(HERE, "data", "jobs.json"), "w") as f:
        json.dump(archive, f, indent=2)

    print(f"\n✅ Done. {new_count} new today, {len(archive)} jobs total on the board.")


if __name__ == "__main__":
    main()
