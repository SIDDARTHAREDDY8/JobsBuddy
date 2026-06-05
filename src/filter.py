"""
Station 2: FILTER
Keeps only jobs that match Siddartha's resume profile:
  - role is SWE / AI / Data / Full-stack (roles_include) and not senior (roles_exclude)
  - experience 0-3 years (drops postings that require 4+ years)
  - flags jobs that look citizen-only / no-sponsorship
"""
import re

MAX_YEARS = 3   # keep roles requiring up to this many years; drop 4+

# Patterns that capture the REQUIRED years number, in any common phrasing:
#   "4+ years", "4 - 6 years", "minimum of 4 years", "at least 4 years",
#   "4 years of experience", "4 yrs experience"
_YEARS_PATTERNS = [
    re.compile(r"(\d{1,2})\s*\+\s*years?"),                                  # 4+ years
    re.compile(r"(\d{1,2})\s*(?:-|–|to)\s*\d{1,2}\s*years?"),                # 4-6 years (take min)
    re.compile(r"(?:minimum|min\.?|at least|at min)[^\d]{0,12}(\d{1,2})\s*years?"),
    re.compile(r"(\d{1,2})\s*(?:\+)?\s*years?\s+of\s+(?:industry\s+|professional\s+|relevant\s+|software\s+)?experience"),
    re.compile(r"(\d{1,2})\s*yrs?\b"),                                       # 4 yrs
]


def _has_any(text, needles):
    return any(n in text for n in needles)


def role_ok(title, profile):
    t = title.lower()
    if _has_any(t, profile["roles_exclude"]):
        return False
    return _has_any(t, profile["roles_include"])


def experience_ok(text, profile):
    t = text.lower()
    # 1) keep the old explicit-phrase safety net
    if _has_any(t, profile.get("exp_exclude_patterns", [])):
        return False
    # 2) robust: read the actual required-years number from any phrasing
    max_allowed = profile.get("experience_years_max", MAX_YEARS)
    for pat in _YEARS_PATTERNS:
        for m in pat.finditer(t):
            try:
                yrs = int(m.group(1))
            except (ValueError, IndexError):
                continue
            if yrs > max_allowed:      # e.g. requires 4+ when max is 3 -> drop
                return False
    return True


def sponsorship_friendly(text, profile):
    # True if nothing screams "citizen only / no sponsorship"
    return not _has_any(text.lower(), profile["no_sponsor_flags"])


def needs_clearance(text, profile):
    # True if the posting requires a US security clearance -> we DROP these
    return _has_any(text.lower(), profile.get("clearance_exclude", []))


STRONG_US = ["united states", "usa", "u.s.", ", us", "- us", "remote us",
             "remote - us", "us-remote", "remote, us"]


def location_ok(location, profile):
    if not profile.get("us_only"):
        return True
    loc = (location or "").lower()
    if not loc:
        return True  # unknown location -> keep, don't over-filter
    # block-list wins decisively, UNLESS the posting explicitly says US too
    if _has_any(loc, profile.get("us_location_block", [])):
        return _has_any(loc, STRONG_US)
    # not a known foreign location -> keep (US hint, remote, or unclear)
    return True


def filter_jobs(jobs, profile):
    kept = []
    for j in jobs:
        blob = f"{j['title']} {j['description']}"
        if not role_ok(j["title"], profile):
            continue
        if not experience_ok(blob, profile):
            continue
        if needs_clearance(blob, profile):
            continue   # drop security-clearance roles entirely
        if not location_ok(f"{j.get('location','')} {j.get('url','')}", profile):
            continue
        j["opt_friendly"] = sponsorship_friendly(blob, profile)
        kept.append(j)
    return kept
