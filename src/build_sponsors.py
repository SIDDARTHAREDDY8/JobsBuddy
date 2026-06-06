"""
Build data/sponsors.json + data/sponsor_stats.json from REAL H1B data.

Source: DOL OFLC LCA disclosure data (aggregated, public) — gives each employer's
H1B filing count and certification rate. We match it to our company list so the
✅ Sponsors tiers and counts are REAL, not guessed.

Run occasionally (not every scrape):  python3 src/build_sponsors.py

Honest note: the fetchable public aggregate covers ~1,500 top sponsoring employers
(the big, high-volume ones people most apply to). Smaller startups not in it keep
their curated tier, or show as "unknown". To cover the full long tail you'd load the
raw ~500k-row DOL file (too large to host in this repo).
"""
import urllib.request, csv, io, re, json, os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOL_CSV = ("https://raw.githubusercontent.com/Chidvy/h1b-opportunity-scorer/"
           "decd32535c2ef2ea39d2f7e033d40ce0de9fbcee/employer_scores.csv")

# curated fallback tiers for well-known sponsors not in the fetched aggregate
CURATED = {
    "google": "high", "amazon": "high", "microsoft": "high", "meta": "high",
    "apple": "high", "nvidia": "high", "salesforce": "high", "adobe": "high",
    "oracle": "high", "intuit": "high", "paypal": "high", "linkedin": "high",
    "uber": "high", "netflix": "high", "atlassian": "high", "snap": "high",
    "openai": "medium", "anthropic": "medium", "spotify": "high", "visa": "high",
    "palantir": "high", "roblox": "high", "coupang": "high", "veeva": "high",
}


def norm(n):
    n = (n or "").lower()
    n = re.sub(r"\b(inc|llc|corp|corporation|co|ltd|technologies|technology|labs|"
               r"holdings|the|group|usa|america|us)\b", "", n)
    return re.sub(r"[^a-z0-9 ]", "", n).strip()


def tier_from_cases(cases):
    if cases >= 50:
        return "high"
    if cases >= 10:
        return "medium"
    return "low"


def main():
    print("Downloading real H1B (DOL) employer data...")
    raw = urllib.request.urlopen(
        urllib.request.Request(DOL_CSV, headers={"User-Agent": "jobsbuddy"}), timeout=30
    ).read().decode("utf-8", "replace")
    emp = {}
    for row in csv.DictReader(io.StringIO(raw)):
        emp[norm(row["EMPLOYER_NAME"])] = {
            "cases": int(float(row["TOTAL_CASES"])), "cert": round(float(row["CERT_RATE"]), 1)}
    print(f"  loaded {len(emp)} employers with real filing data")

    companies = json.load(open(os.path.join(HERE, "companies.json")))
    tiers, stats = {}, {}
    real = 0
    for c in companies:
        nm = c["company"]
        n = norm(nm)
        if not n:
            continue
        match = emp.get(n)
        if not match:  # fuzzy contains match, pick the biggest filer
            best = None
            for k, v in emp.items():
                if len(n) >= 4 and (n + " " in k + " " or k + " " in n + " "):
                    if best is None or v["cases"] > best["cases"]:
                        best = v
            match = best
        if match:
            tiers[nm.lower()] = tier_from_cases(match["cases"])
            stats[nm.lower()] = match
            real += 1
        elif n in CURATED or nm.lower() in CURATED:
            tiers[nm.lower()] = CURATED.get(n) or CURATED.get(nm.lower())

    # keep any previously-curated entries we still have
    prev = json.load(open(os.path.join(HERE, "data", "sponsors.json"))).get("sponsors", {})
    for k, v in prev.items():
        tiers.setdefault(k, v)

    json.dump({"_note": "tiers from REAL DOL H1B filing counts where available; "
               "see src/build_sponsors.py", "sponsors": tiers},
              open(os.path.join(HERE, "data", "sponsors.json"), "w"), indent=1)
    json.dump(stats, open(os.path.join(HERE, "data", "sponsor_stats.json"), "w"), indent=1)
    print(f"  {real} companies tagged with REAL filing counts; "
          f"{len(tiers)} total sponsors tagged")
    print("  wrote data/sponsors.json + data/sponsor_stats.json")


if __name__ == "__main__":
    main()
