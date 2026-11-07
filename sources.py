"""
Job source fetchers.

IMPORTANT / LEGAL NOTE:
  Indeed, JobsDB and LinkedIn prohibit automated scraping in their Terms of Service.
  This module does NOT scrape them. Instead it:
    - Builds ready-to-click *search URLs* for Indeed SG, JobsDB SG, MyCareersFuture and
      a LinkedIn Jobs search, pre-filtered to your roles/location and sorted by newest.
    - Fetches NEW postings legitimately from public company ATS APIs
      (Greenhouse, Lever, Ashby), which are designed for programmatic access.

  So "alerts" work two ways:
    1. Company-board polling (fully automated, ToS-safe) -> genuine new-job alerts.
    2. Curated board search links (you click, see freshest first) -> for Indeed/JobsDB/LinkedIn.
"""
import json
import urllib.parse
import urllib.request

ROLES = [
    "Data Analyst", "Data Scientist", "Business Analyst",
    "Business Intelligence Analyst", "Analytics", "Data Science",
]
LOCATION = "Singapore"


# ---------- Curated board search links (ToS-safe, you click through) ----------

def board_search_links(keyword="Data Analyst"):
    kw = urllib.parse.quote(keyword)
    loc = urllib.parse.quote(LOCATION)
    return {
        "Indeed SG (newest first)":
            f"https://sg.indeed.com/jobs?q={kw}&l={loc}&sort=date&fromage=1",
        "JobsDB SG (newest first)":
            f"https://sg.jobsdb.com/{kw.lower().replace('%20','-')}-jobs?sortmode=ListedDate",
        "MyCareersFuture SG (newest first)":
            f"https://www.mycareersfuture.gov.sg/search?search={kw}&sortBy=new_posting_date&page=0",
        "LinkedIn Jobs (past 24h)":
            f"https://www.linkedin.com/jobs/search/?keywords={kw}&location={loc}&f_TPR=r86400&sortBy=DD",
        "Glassdoor SG":
            f"https://www.glassdoor.sg/Job/singapore-{kw.lower().replace('%20','-')}-jobs-SRCH_IL.0,9_IN217_KO10.htm",
    }


# ---------- Company ATS pollers (fully automated, ToS-safe) ----------

def _get_json(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 JobHunt/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_greenhouse(board_token):
    """Public Greenhouse board API."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
    try:
        data = _get_json(url)
        return [{
            "id": f"gh-{j['id']}",
            "source": f"Greenhouse/{board_token}",
            "title": j.get("title", ""),
            "location": (j.get("location") or {}).get("name", ""),
            "url": j.get("absolute_url", ""),
            "updated_at": j.get("updated_at", ""),
        } for j in data.get("jobs", [])]
    except Exception as e:
        return [{"error": f"greenhouse/{board_token}: {e}"}]


def fetch_lever(company):
    """Public Lever postings API."""
    url = f"https://api.lever.co/v0/postings/{company}?mode=json"
    try:
        data = _get_json(url)
        return [{
            "id": f"lever-{j.get('id')}",
            "source": f"Lever/{company}",
            "title": j.get("text", ""),
            "location": (j.get("categories") or {}).get("location", ""),
            "url": j.get("hostedUrl", ""),
            "updated_at": str(j.get("createdAt", "")),
        } for j in data]
    except Exception as e:
        return [{"error": f"lever/{company}: {e}"}]


def fetch_ashby(org):
    """Public Ashby job board API."""
    url = f"https://api.ashbyhq.com/posting-api/job-board/{org}"
    try:
        data = _get_json(url)
        return [{
            "id": f"ashby-{j.get('id')}",
            "source": f"Ashby/{org}",
            "title": j.get("title", ""),
            "location": j.get("locationName", ""),
            "url": j.get("jobUrl", ""),
            "updated_at": j.get("publishedAt", ""),
        } for j in data.get("jobs", [])]
    except Exception as e:
        return [{"error": f"ashby/{org}: {e}"}]


def relevant(title):
    t = title.lower()
    terms = ["data analyst", "data scien", "business analyst", "business intelligence",
             "analytics", "bi analyst", "data engineer", "quantitative"]
    return any(x in t for x in terms)


# Location filtering. Default: Singapore only. Set SG_ONLY = False to allow worldwide.
SG_ONLY = True
_SG_TERMS = ["singapore", "sg", "sgp", "remote - apac", "apac"]
# Strings that indicate a clearly non-SG location (used to reject "Remote - US" etc.)
_NON_SG_HINTS = [
    "united states", "usa", "u.s.", "london", "uk", "india", "bangalore",
    "bengaluru", "manila", "philippines", "vietnam", "ho chi minh", "jakarta",
    "indonesia", "malaysia", "kuala lumpur", "bangkok", "thailand", "tokyo", "japan",
    "korea", "seoul", "sydney", "australia", "china", "beijing", "shanghai",
    "hong kong", "taiwan", "germany", "berlin", "amsterdam", "netherlands", "canada",
    "dublin", "ireland", "france", "paris", "emea", "latam", "brazil",
]


def is_singapore(location):
    import re
    loc = (location or "").lower().strip()
    if not loc:
        # No location given: keep it, but it will be flagged for you to verify.
        return True
    # explicit Singapore (word-boundary, so "sg"/"us" don't match inside other words)
    if re.search(r"\b(singapore|sg|sgp)\b", loc):
        return True
    # bare non-SG country codes/terms that need word boundaries
    if re.search(r"\b(us|usa|uk|eu|emea|latam|apac na|us remote|remote us)\b", loc) \
            and not re.search(r"\b(apac|asia)\b", loc):
        return False
    # named non-SG countries/cities
    if any(h in loc for h in _NON_SG_HINTS):
        return False
    # APAC / Asia remote is plausibly SG-eligible
    if re.search(r"\b(apac|asia)\b", loc):
        return True
    # a generic "remote" with no disqualifying country -> keep (verify later)
    if "remote" in loc:
        return True
    return False


def search_mycareersfuture(keyword="data analyst", limit=20, entry_level_only=True):
    """
    LIVE search of MyCareersFuture (official SG government job board) via its public API.
    Returns real Singapore jobs, newest first. This is the main in-app job feed.
    """
    url = f"https://api.mycareersfuture.gov.sg/v2/search?limit={limit}&page=0"
    payload = {"search": keyword, "sortBy": ["new_posting_date"]}
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data_bytes, method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return [{"error": f"mycareersfuture: {e}"}]

    out = []
    for item in data.get("results", []):
        meta = item.get("metadata", {})
        company = (item.get("postedCompany") or {}).get("name", "Company not disclosed")
        levels = [p.get("position", "") for p in item.get("positionLevels", [])]
        # entry/junior filter for a penultimate student
        if entry_level_only:
            lv = " ".join(levels).lower()
            senior = any(s in lv for s in ["manager", "senior", "lead", "director",
                                           "head", "principal", "executive"])
            if senior and not any(s in lv for s in ["fresh", "entry", "junior",
                                                    "professional", "non-executive"]):
                continue
        sal = item.get("salary") or {}
        salary = ""
        if sal.get("minimum") and not item.get("isHideSalary"):
            salary = f"${sal.get('minimum')}-{sal.get('maximum')}/mo"
        out.append({
            "id": f"mcf-{meta.get('jobPostId', '')}",
            "source": "MyCareersFuture (SG govt)",
            "title": item.get("title", ""),
            "company": company,
            "location": "Singapore",
            "level": ", ".join(levels),
            "salary": salary,
            "posted": meta.get("newPostingDate", ""),
            "url": meta.get("jobDetailsUrl", ""),
        })
    return out


def poll_companies(companies):
    """companies: list of dicts {'ats': 'greenhouse'|'lever'|'ashby', 'token': '...'}"""
    results = []
    for c in companies:
        ats = c.get("ats")
        token = c.get("token")
        if ats == "greenhouse":
            jobs = fetch_greenhouse(token)
        elif ats == "lever":
            jobs = fetch_lever(token)
        elif ats == "ashby":
            jobs = fetch_ashby(token)
        else:
            continue
        for j in jobs:
            if "error" in j:
                results.append(j)
                continue
            if not relevant(j.get("title", "")):
                continue
            if SG_ONLY and not is_singapore(j.get("location", "")):
                continue
            # flag postings with no stated location so you can double-check
            if not (j.get("location") or "").strip():
                j["location_note"] = "location not stated — verify it's Singapore"
            results.append(j)
    return results


if __name__ == "__main__":
    print("Board search links for 'Data Analyst':")
    for k, v in board_search_links("Data Analyst").items():
        print(f"  {k}\n    {v}")
