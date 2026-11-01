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
            elif relevant(j.get("title", "")):
                results.append(j)
    return results


if __name__ == "__main__":
    print("Board search links for 'Data Analyst':")
    for k, v in board_search_links("Data Analyst").items():
        print(f"  {k}\n    {v}")
