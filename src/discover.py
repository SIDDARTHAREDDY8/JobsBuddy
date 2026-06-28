"""
One-time / maintenance tool: GROW the company list safely.

Give it candidate slugs per ATS; it hits each ATS's real public API, keeps ONLY
the slugs that actually return open jobs, drops anything already in companies.json,
and (with --write) merges the verified new companies in.

Why a validator instead of just pasting names: a dead/wrong slug isn't free — it
makes the scraper waste a request and log a failure every 3 hours, forever. We
only ever want slugs proven to resolve. Run:  python3 src/discover.py [--write]

stdlib only — no pip, same as the scraper.
"""
import json
import os
import sys
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "opt-friendly-jobs/1.0 (+https://github.com/SIDDARTHAREDDY8)"
TIMEOUT = 15


def _get(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode("utf-8", "replace")


# ---- per-ATS validators: return job count (>0 means real, scrapable board) ----
def v_greenhouse(slug):
    d = json.loads(_get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"))
    return len(d.get("jobs", []))


def v_lever(slug):
    d = json.loads(_get(f"https://api.lever.co/v0/postings/{slug}?mode=json"))
    return len(d) if isinstance(d, list) else 0


def v_ashby(slug):
    d = json.loads(_get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}"))
    return len(d.get("jobs", []))


def v_smartrecruiters(slug):
    d = json.loads(_get(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"))
    return d.get("totalFound", 0)


def v_avature(host):
    html = _get(f"https://{host}/en_US/careers/SearchJobs?search=software%20engineer",
                headers={"Accept": "text/html"})
    return html.count('class="article--result')


VALIDATORS = {
    "greenhouse": v_greenhouse, "lever": v_lever, "ashby": v_ashby,
    "smartrecruiters": v_smartrecruiters, "avature": v_avature,
}

# ----------------------------------------------------------------------------
# CANDIDATES — generous on purpose; validation + dedup make wrong guesses safe.
# Focus: sponsor-heavy, early-career-friendly tech/data/AI employers.
# (company display name, ats, slug)
# ----------------------------------------------------------------------------
CANDIDATES = [
    # --- Greenhouse ---
    ("Airbnb", "greenhouse", "airbnb"), ("DoorDash", "greenhouse", "doordash"),
    ("Instacart", "greenhouse", "instacart"), ("Robinhood", "greenhouse", "robinhood"),
    ("Brex", "greenhouse", "brex"), ("Ramp", "greenhouse", "ramp"),
    ("Plaid", "greenhouse", "plaid"), ("Affirm", "greenhouse", "affirm"),
    ("Chime", "greenhouse", "chime"), ("SoFi", "greenhouse", "sofi"),
    ("Dropbox", "greenhouse", "dropbox"), ("Roblox", "greenhouse", "roblox"),
    ("Samsara", "greenhouse", "samsara"), ("HashiCorp", "greenhouse", "hashicorp"),
    ("Confluent", "greenhouse", "confluent"), ("Cockroach Labs", "greenhouse", "cockroachlabs"),
    ("Datadog", "greenhouse", "datadog"), ("Elastic", "greenhouse", "elastic"),
    ("GitLab", "greenhouse", "gitlab"), ("Cloudflare", "greenhouse", "cloudflare"),
    ("Asana", "greenhouse", "asana"), ("Notion", "greenhouse", "notion"),
    ("Calendly", "greenhouse", "calendly"), ("Retool", "greenhouse", "retool"),
    ("Discord", "greenhouse", "discord"), ("Pinterest", "greenhouse", "pinterest"),
    ("Reddit", "greenhouse", "reddit"), ("Lyft", "greenhouse", "lyft"),
    ("Nextdoor", "greenhouse", "nextdoor"), ("Benchling", "greenhouse", "benchling"),
    ("Flexport", "greenhouse", "flexport"), ("Faire", "greenhouse", "faire"),
    ("Gopuff", "greenhouse", "gopuff"), ("Twilio", "greenhouse", "twilio"),
    ("Block", "greenhouse", "block"), ("Marqeta", "greenhouse", "marqeta"),
    ("Wealthfront", "greenhouse", "wealthfront"), ("Betterment", "greenhouse", "betterment"),
    ("Nerdwallet", "greenhouse", "nerdwallet"), ("Carta", "greenhouse", "carta"),
    ("Gemini", "greenhouse", "gemini"), ("Kraken", "greenhouse", "kraken"),
    ("Circle", "greenhouse", "circle"), ("Anchorage Digital", "greenhouse", "anchorage"),
    ("Verkada", "greenhouse", "verkada"), ("Rubrik", "greenhouse", "rubrik"),
    ("Cohesity", "greenhouse", "cohesity"), ("Snyk", "greenhouse", "snyk"),
    ("1Password", "greenhouse", "1password"), ("Okta", "greenhouse", "okta"),
    ("CrowdStrike", "greenhouse", "crowdstrike"), ("SentinelOne", "greenhouse", "sentinelone"),
    ("Abnormal Security", "greenhouse", "abnormalsecurity"), ("Wiz", "greenhouse", "wiz"),
    ("Grammarly", "greenhouse", "grammarly"), ("Duolingo", "greenhouse", "duolingo"),
    ("Coursera", "greenhouse", "coursera"), ("Udemy", "greenhouse", "udemy"),
    ("DoubleVerify", "greenhouse", "doubleverify"), ("Yelp", "greenhouse", "yelp"),
    ("Eventbrite", "greenhouse", "eventbrite"), ("ZipRecruiter", "greenhouse", "ziprecruiter"),
    ("Wayfair", "greenhouse", "wayfair"), ("Chewy", "greenhouse", "chewy"),
    ("Peloton", "greenhouse", "peloton"), ("Warby Parker", "greenhouse", "warbyparker"),
    ("Sweetgreen", "greenhouse", "sweetgreen"), ("ButcherBox", "greenhouse", "butcherbox"),
    ("Tatari", "greenhouse", "tatari"), ("AngelList", "greenhouse", "angellist"),
    ("Mux", "greenhouse", "mux"), ("Sentry", "greenhouse", "sentry"),
    ("PagerDuty", "greenhouse", "pagerduty"), ("LaunchDarkly", "greenhouse", "launchdarkly"),
    ("Cribl", "greenhouse", "cribl"), ("Grafana Labs", "greenhouse", "grafanalabs"),
    ("Weights & Biases", "greenhouse", "weightsandbiases"), ("Hugging Face", "greenhouse", "huggingface"),
    ("Cohere", "greenhouse", "cohere"), ("Runway", "greenhouse", "runwayml"),
    ("Adept", "greenhouse", "adept"), ("Character AI", "greenhouse", "characterai"),
    ("Glean", "greenhouse", "glean"), ("Sierra", "greenhouse", "sierra"),
    ("Harvey", "greenhouse", "harvey"), ("Abridge", "greenhouse", "abridge"),
    ("Tempus", "greenhouse", "tempus"), ("Komodo Health", "greenhouse", "komodohealth"),
    ("Cedar", "greenhouse", "cedar"), ("Devoted Health", "greenhouse", "devotedhealth"),
    ("Oscar Health", "greenhouse", "oscar"), ("Ro", "greenhouse", "ro"),
    ("Hims & Hers", "greenhouse", "himsandhers"), ("Cityblock Health", "greenhouse", "cityblockhealth"),
    # big names whose real Greenhouse token differs from their name (verified):
    ("DoorDash", "greenhouse", "doordashusa"), ("Wiz", "greenhouse", "wizinc"),
    ("Glean", "greenhouse", "gleanwork"), ("Gusto", "greenhouse", "gusto"),
    # --- Lever ---
    ("Netflix", "lever", "netflix"), ("KAYAK", "lever", "kayak"),
    ("Brex (Lever)", "lever", "brex"), ("Plaid (Lever)", "lever", "plaid"),
    ("Attentive", "lever", "attentive"), ("Ramp (Lever)", "lever", "ramp"),
    ("Spotify", "lever", "spotify"), ("Palo Alto Networks", "lever", "paloaltonetworks"),
    ("Veeva", "lever", "veeva"), ("KnowBe4", "lever", "knowbe4"),
    ("Allbirds", "lever", "allbirds"), ("Mapbox", "lever", "mapbox"),
    ("Twitch (Lever)", "lever", "twitch"), ("Lyra Health", "lever", "lyrahealth"),
    ("Upgrade", "lever", "upgrade"), ("Clari", "lever", "clari"),
    ("Gusto (Lever)", "lever", "gusto"), ("Coinbase (Lever)", "lever", "coinbase"),
    # --- Ashby ---
    ("Linear", "ashby", "linear"), ("Vanta", "ashby", "Vanta"),
    ("Mercury", "ashby", "mercury"), ("Replit", "ashby", "replit"),
    ("Hex", "ashby", "hex"), ("Modal", "ashby", "modal"),
    ("Baseten", "ashby", "baseten"), ("Together AI", "ashby", "togetherai"),
    ("Perplexity", "ashby", "perplexity"), ("Clay", "ashby", "clay"),
    ("Ramp (Ashby)", "ashby", "ramp"), ("Notion (Ashby)", "ashby", "notion"),
    ("Cursor / Anysphere", "ashby", "anysphere"), ("Decagon", "ashby", "decagon"),
    ("Browserbase", "ashby", "browserbase"), ("Sardine", "ashby", "sardine"),
    ("Watershed", "ashby", "watershed"), ("Pinecone", "ashby", "pinecone"),
    ("Mistral AI", "ashby", "mistral"), ("ElevenLabs", "ashby", "elevenlabs"),
    ("LangChain", "ashby", "langchain"), ("Zip", "ashby", "zip"),
    # --- SmartRecruiters ---
    ("Visa", "smartrecruiters", "Visa"), ("Square (SR)", "smartrecruiters", "Square"),
    ("Bosch", "smartrecruiters", "BoschGroup"), ("Ubisoft", "smartrecruiters", "Ubisoft"),
]


def parse_target(arg):
    """Turn a job/careers URL (or 'ats:slug', or bare slug) into (name, ats, slug).
    Lets you add any job you spot on LinkedIn in one command:
        python3 src/discover.py --add https://job-boards.greenhouse.io/ooma/jobs/123
    """
    a = arg.strip()
    host = a.split("//")[-1].split("/")[0].lower()
    parts = [p for p in a.split("//")[-1].split("/")[1:] if p]
    if "greenhouse.io" in host:
        # boards-api.greenhouse.io/v1/boards/{slug}/... | job-boards/boards.greenhouse.io/{slug}/...
        if "v1/boards" in a:
            slug = a.split("v1/boards/")[1].split("/")[0]
        else:
            slug = parts[0] if parts else ""
        return (slug.title(), "greenhouse", slug) if slug else None
    if "lever.co" in host:
        return (parts[0].title(), "lever", parts[0]) if parts else None
    if "ashbyhq.com" in host:
        return (parts[0].title(), "ashby", parts[0]) if parts else None
    if "smartrecruiters.com" in host:
        return (parts[0].title(), "smartrecruiters", parts[0]) if parts else None
    if "avature.net" in host:                       # {co}.avature.net
        return (host.split(".")[0].title(), "avature", host)
    if host.startswith("apply.") and host.endswith((".com", ".net")):  # apply.{co}.com (Avature)
        return (host.split(".")[1].title(), "avature", host)
    if ":" in a and "//" not in a:                  # "ats:slug"
        ats, slug = a.split(":", 1)
        return (slug.title(), ats.strip(), slug.strip())
    if "." not in a and "/" not in a:               # bare slug -> assume greenhouse
        return (a.title(), "greenhouse", a)
    return None


def _gh_name(slug):
    """Fetch the real company display name from the Greenhouse board (nicer than
    a title-cased slug)."""
    try:
        d = json.loads(_get(f"https://boards-api.greenhouse.io/v1/boards/{slug}"))
        return d.get("name") or slug.title()
    except Exception:
        return slug.title()


def add_targets(args):
    """--add mode: parse each URL/slug, validate it returns jobs, merge if new."""
    path = os.path.join(HERE, "companies.json")
    existing = json.load(open(path))
    have = {(x["ats"], x["slug"].lower()) for x in existing}
    added = 0
    for arg in args:
        t = parse_target(arg)
        if not t:
            print(f"  ?  couldn't parse: {arg}")
            continue
        name, ats, slug = t
        if ats not in VALIDATORS:
            print(f"  ⚠️  {ats} not auto-validatable here: {slug}")
            continue
        if (ats, slug.lower()) in have:
            print(f"  =  already have {ats}:{slug}")
            continue
        try:
            n = VALIDATORS[ats](slug)
        except Exception as e:
            print(f"  ❌ {ats}:{slug} did not resolve ({type(e).__name__})")
            continue
        if not n:
            print(f"  ❌ {ats}:{slug} resolved but has 0 open jobs")
            continue
        if ats == "greenhouse":
            name = _gh_name(slug)
        existing.append({"company": name, "ats": ats, "slug": slug})
        have.add((ats, slug.lower()))
        added += 1
        print(f"  ✅ added {name} ({ats}:{slug}) — {n} open jobs")
    if added:
        json.dump(existing, open(path, "w"), indent=2)
        print(f"\n💾 merged {added} new → companies.json (now {len(existing)} total)")
    else:
        print("\nnothing new to add.")


def check(c):
    name, ats, slug = c
    try:
        n = VALIDATORS[ats](slug)
        return (c, n, None)
    except Exception as e:
        return (c, 0, type(e).__name__)


def main():
    if "--add" in sys.argv:
        targets = [a for a in sys.argv[sys.argv.index("--add") + 1:]
                   if not a.startswith("--")]
        add_targets(targets)
        return
    write = "--write" in sys.argv
    existing = json.load(open(os.path.join(HERE, "companies.json")))
    have = {(x["ats"], x["slug"].lower()) for x in existing}

    todo = [c for c in CANDIDATES if (c[1], c[2].lower()) not in have]
    print(f"{len(CANDIDATES)} candidates · {len(CANDIDATES)-len(todo)} already in list · "
          f"validating {len(todo)} new...\n")

    good, dead = [], []
    with ThreadPoolExecutor(max_workers=16) as ex:
        for c, n, err in [f.result() for f in as_completed([ex.submit(check, c) for c in todo])]:
            if n and n > 0:
                good.append((c, n))
            else:
                dead.append((c, err))

    good.sort(key=lambda x: -x[1])
    print(f"✅ VERIFIED {len(good)} new companies with live jobs:")
    for (name, ats, slug), n in good:
        print(f"   {n:>4} jobs  {ats:15} {slug:24} {name}")
    print(f"\n❌ {len(dead)} did not resolve (wrong slug / not on that ATS):")
    for (name, ats, slug), err in dead:
        print(f"        {ats:15} {slug:24} {name}  ({err})")

    if write and good:
        for (name, ats, slug), n in good:
            existing.append({"company": name, "ats": ats, "slug": slug})
        json.dump(existing, open(os.path.join(HERE, "companies.json"), "w"), indent=2)
        print(f"\n💾 merged {len(good)} new companies → companies.json "
              f"(now {len(existing)} total)")
    elif good:
        print("\n(dry run — re-run with --write to merge these in)")


if __name__ == "__main__":
    main()
