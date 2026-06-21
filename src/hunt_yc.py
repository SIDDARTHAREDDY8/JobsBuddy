"""
The 'god view' hunter: tap the public YC company directory (~6,000 funded
startups), keep the ACTIVE + currently-HIRING + US ones, and intersect them with
the open ATSes we can scrape. These are the hidden gems — funded, hiring, often
visa-sponsoring, but unknown, so almost nobody applies. Low applicants = best odds.

  python3 src/hunt_yc.py            # dry run — show what resolves
  python3 src/hunt_yc.py --write    # merge verified new companies
  python3 src/hunt_yc.py --limit 400 --write

stdlib only.
"""
import json
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "opt-friendly-jobs/1.0 (+https://github.com/SIDDARTHAREDDY8)"
TIMEOUT = 10
YC_URL = "https://raw.githubusercontent.com/yc-oss/api/main/companies/all.json"


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode("utf-8", "replace")


def v_greenhouse(s):
    return len(json.loads(_get(f"https://boards-api.greenhouse.io/v1/boards/{s}/jobs")).get("jobs", []))


def v_lever(s):
    d = json.loads(_get(f"https://api.lever.co/v0/postings/{s}?mode=json"))
    return len(d) if isinstance(d, list) else 0


def v_ashby(s):
    return len(json.loads(_get(f"https://api.ashbyhq.com/posting-api/job-board/{s}")).get("jobs", []))


# Ashby first: YC/early-stage startups skew heavily Ashby, then Greenhouse, Lever.
ORDER = [("ashby", v_ashby), ("greenhouse", v_greenhouse), ("lever", v_lever)]

# known slug collisions — the slug resolves to a DIFFERENT (usually large staffing)
# company than the YC startup of that name. Verified by board name + job count.
SKIP = {("greenhouse", "agency")}   # -> "Meridial", an 800-job staffing board


def _gh_real_name(slug, fallback):
    try:
        n = json.loads(_get(f"https://boards-api.greenhouse.io/v1/boards/{slug}")).get("name")
        return n.strip() if n else fallback
    except Exception:
        return fallback


def slugs_for(c):
    """Candidate slugs: the YC slug (usually the ATS slug too) + flattened name."""
    out = []
    for s in [c.get("slug", ""), re.sub(r"[^a-z0-9]", "", c.get("name", "").lower())]:
        if s and s not in out:
            out.append(s)
    return out


def is_us(c):
    loc = c.get("all_locations") or ""
    regions = c.get("regions") or []
    return ("USA" in loc or "United States" in loc
            or any("United States" in r for r in regions))


def hunt(c, have):
    for slug in slugs_for(c):
        for ats, vfn in ORDER:
            if (ats, slug.lower()) in have or (ats, slug.lower()) in SKIP:
                continue
            try:
                n = vfn(slug)
            except Exception:
                continue
            if n and n > 0:
                # Greenhouse exposes the authoritative board name — prefer it so
                # collision/rebrand slugs are labeled right (burnt -> XION etc.)
                name = _gh_real_name(slug, c["name"]) if ats == "greenhouse" else c["name"]
                return (name, ats, slug, n, c.get("batch", ""), c.get("industry", ""))
    return None


def main():
    write = "--write" in sys.argv
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    print("fetching YC directory...")
    data = json.loads(_get(YC_URL))
    pool = [c for c in data if c.get("status") == "Active"
            and c.get("isHiring") and is_us(c)]
    if limit:
        pool = pool[:limit]
    print(f"{len(pool)} active + hiring + US YC startups to check\n")

    existing = json.load(open(os.path.join(HERE, "companies.json")))
    have = {(x["ats"], x["slug"].lower()) for x in existing}

    found = []
    with ThreadPoolExecutor(max_workers=24) as ex:
        futs = [ex.submit(hunt, c, have) for c in pool]
        for i, f in enumerate(as_completed(futs), 1):
            r = f.result()
            if r:
                found.append(r)
            if i % 200 == 0:
                print(f"  ...checked {i}/{len(pool)}, {len(found)} hidden gems so far")

    found.sort(key=lambda x: -x[3])
    print(f"\n✅ {len(found)} hidden YC employers on open ATSes with live jobs:\n")
    for name, ats, slug, n, batch, ind in found:
        print(f"   {n:>4} jobs  {ats:11} {slug:22} {name:26} [{batch}] {ind[:24]}")

    if write and found:
        for name, ats, slug, n, batch, ind in found:
            existing.append({"company": name, "ats": ats, "slug": slug})
        json.dump(existing, open(os.path.join(HERE, "companies.json"), "w"), indent=2)
        print(f"\n💾 merged {len(found)} → companies.json (now {len(existing)} total)")
    elif found:
        print("\n(dry run — re-run with --write to merge)")


if __name__ == "__main__":
    main()
