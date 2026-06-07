"""
Station 2: FILTER
Keeps only jobs that match Siddartha's resume profile:
  - role is SWE / AI / Data / Full-stack (roles_include) and not senior (roles_exclude)
  - experience 0-3 years (drops postings that require 4+ years)
  - flags jobs that look citizen-only / no-sponsorship
"""
import re

MAX_YEARS = 3   # keep roles requiring up to this many years; drop 4+

# Patterns that capture the REQUIRED years number, in many real-world phrasings:
#   "4+ years", "4+ working", "4+ yoe", "4 - 6 years", "minimum of 4 years",
#   "at least 4 years", "4 years of experience", "4 yrs", "6+ of experience"
_EXP_WORDS = r"(?:years?|yrs?|yoe|year['’]?s?|working|of\s+experience|of\s+professional|of\s+industry)"
_YEARS_PATTERNS = [
    re.compile(r"(\d{1,2})\s*\+\s*" + _EXP_WORDS),                           # 6+ years / 6+ working / 6+ yoe
    re.compile(r"(\d{1,2})\s*(?:-|–|to)\s*\d{1,2}\s*" + _EXP_WORDS),         # 4-6 years (take min)
    re.compile(r"(?:minimum|min\.?|at least|at min)[^\d]{0,14}(\d{1,2})\s*" + _EXP_WORDS),
    re.compile(r"(\d{1,2})\s*\+?\s*years?\s+of\s+(?:industry\s+|professional\s+|relevant\s+|software\s+|hands[- ]on\s+)?experience"),
    re.compile(r"(\d{1,2})\s*\+?\s*yrs?\b"),                                 # 4 yrs / 4+ yrs
]


def _has_any(text, needles):
    return any(n in text for n in needles)


# core software/AI/data role indicators (the FAMILY, not one specific name).
# NOTE: use "developer" not "development" — "development" matches sales roles like
# "Business Development" / "Sales Development Representative".
_ROLE_CORE = re.compile(r"\b(engineer|engineering|developer|programmer|"
                        r"sde|swe|sre|sdet|coder|dba)\b")
_ROLE_CORE_PHRASES = ["data scientist", "applied scientist", "machine learning",
                      "data science", "site reliability", "data analyst",
                      "database administrator", "analytics engineer"]
# seniority — drop these
_SENIOR = re.compile(r"\b(senior|sr|staff|principal|lead|leads|manager|director|"
                     r"head|vp|vice president|president|distinguished|architect|"
                     r"intern|internship|apprentice|trainee|co op|fellow|phd)\b")


def role_ok(title, profile):
    t = re.sub(r"[^a-z0-9 ]", " ", title.lower())
    t = re.sub(r"\s+", " ", t).strip()

    # IC exception: "(member of) technical staff" is an entry/IC title, not senior —
    # strip it before the seniority check so bare 'staff' doesn't wrongly drop it
    is_ic_staff = "technical staff" in t
    senior_check = t.replace("technical staff", "").replace("member of", "") if is_ic_staff else t

    # 1) drop senior / intern titles
    if _SENIOR.search(senior_check):
        return False
    # 2) drop clearly non-software engineering domains (mechanical, sales, etc.)
    if _has_any(t, profile.get("roles_domain_exclude", [])):
        return False
    # 3) keep if it's any software / AI / data role in the family
    return bool(is_ic_staff or _ROLE_CORE.search(t) or _has_any(t, _ROLE_CORE_PHRASES))


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


# Catch "[negation] ... sponsor" in ANY phrasing (not a fixed phrase list):
#   "does not provide immigration-related sponsorship", "will not sponsor",
#   "unable to provide sponsorship", "not eligible for sponsorship",
#   "do not apply ... if you need ... sponsorship"
_VISA_BLOCK_RE = [
    re.compile(r"\b(?:do|does|did|will|would|can|could|are|is|to|we)\s+not\b[^.!?]{0,55}\bsponsor"),
    re.compile(r"\b(?:cannot|can ?not|unable to|won'?t|not able to|not eligible for|"
               r"not be able to|ineligible for|no longer)\b[^.!?]{0,40}\bsponsor"),
    re.compile(r"\bdo not apply\b[^.!?]{0,110}\bsponsor"),
    re.compile(r"\bwithout\b[^.!?]{0,20}\bsponsor"),
    re.compile(r"\bno\b[^.!?]{0,18}\b(?:visa|immigration|employment|work|h-?1b)\b[^.!?]{0,18}\bsponsor"),
    re.compile(r"\bsponsor\w*\b[^.!?]{0,20}\b(?:is|are|will)\s+not\b"),  # "sponsorship is not available"
]


def blocks_visa(text, profile):
    # True if the posting requires US citizenship or explicitly won't sponsor -> DROP
    t = text.lower()
    if _has_any(t, profile.get("visa_block_phrases", [])):
        return True
    return any(p.search(t) for p in _VISA_BLOCK_RE)


def company_blocked(company, profile):
    # True for IT-services / consulting / staffing body shops we don't want.
    # word-boundary match so "kforce" != "Trackforce", "atos" != "Atossa", etc.
    c = company.lower()
    return (_has_word(c, profile.get("companies_exclude", []))
            or _has_word(c, profile.get("defense_exclude", [])))


STRONG_US = ["united states", "usa", "u.s.", ", us", "- us", "remote us",
             "remote - us", "us-remote", "remote, us"]

# foreign ISO country codes safe to block as a trailing location token —
# EXCLUDES codes that collide with US state abbreviations
# (ca=California, in=Indiana, de=Delaware, co=Colorado, ar=Arkansas,
#  id=Idaho, ma=Mass., md=Maryland, or=Oregon, pa=Penn., etc.)
FOREIGN_CC = {
    "vn", "fr", "gb", "uk", "ie", "nl", "be", "lu", "es", "pt", "it", "ch",
    "at", "dk", "se", "no", "fi", "pl", "cz", "sk", "hu", "ro", "bg", "gr",
    "hr", "rs", "si", "ee", "lt", "lv", "tr", "ua", "ru", "jp", "cn", "kr",
    "tw", "hk", "sg", "my", "th", "ph", "au", "nz", "br", "mx", "cl", "pe",
    "ae", "qa", "il", "eg", "za", "ng", "ke", "lk", "bd", "pk", "np", "ph",
}


def location_ok(location, profile):
    """US-REQUIRED logic: a job is kept only if its location shows a clear US
    signal (or is remote / genuinely unknown). Anything with a location that
    has no US signal is treated as foreign and dropped — this catches foreign
    cities we've never explicitly listed (the root of repeated India leaks)."""
    if not profile.get("us_only"):
        return True
    full = (location or "").lower()          # may be "location url"
    loc_text = full.split("http")[0].strip()  # location portion only (drop URL)

    strong_us = _has_any(full, STRONG_US)

    # 1) explicit foreign signal (known country/city, anywhere incl. URL path) -> drop
    if _has_word(full, profile.get("us_location_block", [])) and not strong_us:
        return False
    # 2) trailing 2-letter country code ("Hà Nội, vn") -> drop
    seg = loc_text.replace(";", ",").split(",")[-1].strip()
    last = seg.split()[0] if seg.split() else ""
    if last in FOREIGN_CC and not strong_us:
        return False

    # 3) US-REQUIRED: must have a positive US signal to pass
    if not loc_text:
        return True            # truly no location given -> keep (rare, don't over-drop)
    if "remote" in loc_text:
        return True            # remote (US-leaning for US-based employers)
    if strong_us or _has_any(loc_text, profile.get("us_location_hints", [])):
        return True            # US state / city / "United States" / ", CA" etc.
    # has a location, but no US signal at all -> foreign or unknown -> DROP
    return False


def _has_word(text, terms):
    for t in terms:
        if re.search(r"\b" + re.escape(t.strip()) + r"\b", text):
            return True
    return False


def filter_jobs(jobs, profile):
    kept = []
    for j in jobs:
        blob = f"{j['title']} {j['description']}"
        if company_blocked(j.get("company", ""), profile):
            continue   # drop IT-services / consulting / staffing companies
        if not role_ok(j["title"], profile):
            continue
        if not experience_ok(blob, profile):
            continue
        if needs_clearance(blob, profile):
            continue   # drop security-clearance roles entirely
        if blocks_visa(blob, profile):
            continue   # drop citizenship-required / no-sponsorship roles
        if not location_ok(f"{j.get('location','')} {j.get('url','')}", profile):
            continue
        j["opt_friendly"] = sponsorship_friendly(blob, profile)
        kept.append(j)
    return kept
