"""
Station 3: TAG SPONSORS
Marks each job with the company's H1B sponsorship history.

v1 uses data/sponsors.json (a curated seed list, tier = high/medium/low).
To upgrade to EXACT petition counts, download the official US DOL LCA
disclosure data and rebuild sponsors.json:
  https://www.dol.gov/agencies/eta/foreign-labor/performance
(That file is a large spreadsheet; group by EMPLOYER_NAME, count rows for
the last ~3 fiscal years, and write { normalized_name: count }.)
"""
import json
import os
import re

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_sponsors():
    with open(os.path.join(_HERE, "data", "sponsors.json")) as f:
        return json.load(f)["sponsors"]


def load_stats():
    p = os.path.join(_HERE, "data", "sponsor_stats.json")
    if os.path.exists(p):
        with open(p) as f:
            return {_norm(k): v for k, v in json.load(f).items()}
    return {}


def _norm(name):
    name = name.lower()
    name = re.sub(r"\b(inc|llc|corp|corporation|co|ltd|technologies|technology|labs|the)\b", "", name)
    return re.sub(r"[^a-z0-9 ]", "", name).strip()


def tag_sponsors(jobs, sponsors):
    norm_map = {_norm(k): v for k, v in sponsors.items()}
    stats = load_stats()
    for j in jobs:
        cn = _norm(j["company"])
        tier = norm_map.get(cn)
        if tier is None:  # loose contains-match (e.g. "Block, Inc" vs "block")
            for k, v in norm_map.items():
                if k and (k in cn or cn in k):
                    tier = v
                    break
        j["sponsor_tier"] = tier            # "high" | "medium" | "low" | None
        j["sponsors_visa"] = tier is not None
        st = stats.get(cn)                   # REAL DOL filing data, if we have it
        j["sponsor_cases"] = st["cases"] if st else None
        j["sponsor_cert"] = st["cert"] if st else None
    return jobs
