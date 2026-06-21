"""
Variant hunter: given a list of COMPANY NAMES, generate plausible ATS slugs,
test every variant against Greenhouse/Lever/Ashby/SmartRecruiters, and keep the
one that actually returns live jobs. Far higher hit-rate than guessing one slug.

  python3 src/hunt.py            # dry run — show what resolves
  python3 src/hunt.py --write    # merge verified new companies into companies.json
"""
import json
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "opt-friendly-jobs/1.0 (+https://github.com/SIDDARTHAREDDY8)"
TIMEOUT = 12


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


def v_smartrecruiters(s):
    return json.loads(_get(f"https://api.smartrecruiters.com/v1/companies/{s}/postings")).get("totalFound", 0)


VALIDATORS = {"greenhouse": v_greenhouse, "lever": v_lever,
              "ashby": v_ashby, "smartrecruiters": v_smartrecruiters}


def slug_variants(name):
    """Generate plausible slugs from a company name."""
    base = re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()
    base = re.sub(r"\b(inc|llc|labs|technologies|technology|software|the|ai|io)\b", "", base).strip()
    flat = base.replace(" ", "")
    first = base.split()[0] if base.split() else flat
    hyphen = base.replace(" ", "-")
    raw = re.sub(r"[^a-z0-9]", "", name.lower())
    cands = [flat, raw, first, hyphen, flat + "careers", flat + "inc",
             flat + "hq", flat + "jobs", first + "ai", flat + "ai"]
    seen, out = set(), []
    for c in cands:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


# Well-known visa-sponsoring, early-career-friendly employers on open ATSes.
NAMES = [
    # AI / ML
    "Scale AI", "Anyscale", "Perplexity", "Together AI", "Fireworks AI", "Baseten",
    "Modal", "Replicate", "Contextual AI", "Writer", "Cresta", "Moveworks",
    "Hippocratic AI", "Cartesia", "Sierra", "Decagon", "Glean", "Harvey", "Scourcegraph",
    "ElevenLabs", "Runway", "Pika", "Luma AI", "Suno", "Mistral", "Cohere", "Adept",
    "Weaviate", "Qdrant", "Chroma", "LanceDB", "Pinecone", "Vespa",
    # Fintech
    "Mercury", "Modern Treasury", "Lithic", "Increase", "Column", "Unit", "Highnote",
    "Public", "Step", "Current", "Varo", "Dave", "MoneyLion", "Klarna", "Marqeta",
    "Pomelo", "Ramp", "Brex", "Plaid", "Wealthfront", "Bond", "Alloy", "Sardine",
    # Data / infra / dev tools
    "Fivetran", "dbt Labs", "Airbyte", "Census", "Hightouch", "Monte Carlo", "Hex",
    "Sigma Computing", "Starburst", "Dremio", "ClickHouse", "Timescale", "Neon",
    "Supabase", "PlanetScale", "Materialize", "Temporal", "Estuary", "Prefect",
    "Dagster", "Astronomer", "Tecton", "Chronosphere", "Grafana Labs", "Cribl",
    "Vercel", "Netlify", "Render", "Railway", "Sourcegraph", "Postman", "Linear",
    "Warp", "Raycast", "Codeium", "Tabnine", "Replit", "Sentry", "LaunchDarkly",
    # Security
    "Tailscale", "Lacework", "Orca Security", "Aqua Security", "Sysdig", "Vanta",
    "Drata", "Material Security", "Chainguard", "Semgrep", "Socket", "Snyk", "Wiz",
    "Auth0", "1Password", "Island", "Cyera", "Persona",
    # Health
    "Tempus", "Komodo Health", "Cedar", "Maven Clinic", "Carbon Health",
    "Spring Health", "Headway", "Included Health", "Color", "Flatiron Health",
    "Recursion", "Devoted Health", "Oscar Health", "Ro", "Hims and Hers",
    # Consumer / marketplace / SaaS
    "Whatnot", "StockX", "Faire", "Patreon", "Substack", "Webflow", "Framer",
    "Loom", "Miro", "Canva", "Notion", "Airtable", "Calendly", "Gusto", "Rippling",
    "Deel", "Remote", "Ironclad", "Vanta", "Ramp", "Front", "Pylon", "Clari",
    # Robotics / hardware (non-defense)
    "Zipline", "Skydio", "Figure", "Nuro", "Applied Intuition", "Waymo", "Zoox",
    "Cruise", "Aurora Innovation", "Rivian", "Wing",
]


def hunt_one(name, have):
    for ats, vfn in VALIDATORS.items():
        for slug in slug_variants(name):
            if (ats, slug.lower()) in have:
                return (name, ats, slug, -1)   # already have it
            try:
                n = vfn(slug)
            except Exception:
                continue
            if n and n > 0:
                return (name, ats, slug, n)
    return (name, None, None, 0)


def main():
    write = "--write" in sys.argv
    existing = json.load(open(os.path.join(HERE, "companies.json")))
    have = {(x["ats"], x["slug"].lower()) for x in existing}

    print(f"hunting {len(NAMES)} company names across 4 ATSes (variant search)...\n")
    results = []
    with ThreadPoolExecutor(max_workers=12) as ex:
        for r in [f.result() for f in as_completed([ex.submit(hunt_one, n, have) for n in NAMES])]:
            results.append(r)

    new = [r for r in results if r[3] > 0]
    dup = [r for r in results if r[3] == -1]
    miss = [r for r in results if r[3] == 0]
    new.sort(key=lambda x: -x[3])

    print(f"✅ NEW & verified ({len(new)}):")
    for name, ats, slug, n in new:
        print(f"   {n:>4} jobs  {ats:15} {slug:24} {name}")
    print(f"\n=  already had ({len(dup)}): " + ", ".join(r[0] for r in dup))
    print(f"\n❌ not on an open ATS / unknown slug ({len(miss)}): " + ", ".join(r[0] for r in miss))

    if write and new:
        for name, ats, slug, n in new:
            # Greenhouse exposes the authoritative board name — use it so we never
            # mislabel a name-collision slug (e.g. 'carbon' -> Carbon Inc, not
            # Carbon Health; 'remote' -> General Assembly, not Remote.com).
            if ats == "greenhouse":
                try:
                    real = json.loads(_get(f"https://boards-api.greenhouse.io/v1/boards/{slug}")).get("name")
                    if real:
                        name = real
                except Exception:
                    pass
            existing.append({"company": name, "ats": ats, "slug": slug})
        json.dump(existing, open(os.path.join(HERE, "companies.json"), "w"), indent=2)
        print(f"\n💾 merged {len(new)} → companies.json (now {len(existing)} total)")
    elif new:
        print("\n(dry run — re-run with --write to merge)")


if __name__ == "__main__":
    main()
