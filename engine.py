"""
JobHunt engine: profile loading, experience computation, and answer generation.
Pure Python, no external dependencies — runs on your Mac with the built-in python3.
"""
import json
import os
import re
from datetime import date, datetime

BASE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    with open(os.path.join(BASE, name), "r") as f:
        return json.load(f)


def load_profile():
    return _load("profile.json")


def load_library():
    return _load("answer_library.json")


# ---------- Experience computation ----------

def _months_between(start, end):
    s = datetime.strptime(start, "%Y-%m-%d").date()
    e = datetime.strptime(end, "%Y-%m-%d").date()
    return max(0, (e.year - s.year) * 12 + (e.month - s.month))


def years_of_experience(include_internships=False, profile=None):
    """Return (years_float, human_readable). Projects never count as professional experience."""
    profile = profile or load_profile()
    total_months = 0
    for exp in profile["experience"]:
        if exp["type"] == "internship" and include_internships:
            total_months += _months_between(exp["start"], exp["end"])
    years = round(total_months / 12.0, 1)
    if not include_internships:
        return 0.0, "0 (no full-time professional experience yet; penultimate-year student)"
    return years, f"{years} years ({total_months} months of internship experience)"


def answer_experience_question(question):
    """Decide include/exclude internships from the question wording."""
    q = question.lower()
    excludes = any(p in q for p in [
        "exclud", "not includ", "excluding internship", "full-time", "full time",
        "post-graduation", "professional experience only", "paid employment",
    ])
    includes_internship = any(p in q for p in ["includ", "internship count", "including internship"])
    if excludes and not includes_internship:
        val, text = years_of_experience(include_internships=False)
    else:
        # Default for a student: present internship honestly
        val, text = years_of_experience(include_internships=True)
    return text


# ---------- Answer generation ----------

KEYWORDS = {
    "python": "I use Python daily (Pandas, NumPy, scikit-learn) across my internship and analytics projects.",
    "sql": "I write SQL for data extraction and analysis and have applied it throughout my coursework and club projects.",
    " r ": "I use R (with RMarkdown and ggplot2) for statistical analysis and reporting.",
    "tableau": "I build Tableau dashboards — including an automated live audit dashboard streaming from FormSG during my PA internship.",
    "machine learning": "I have applied machine learning (logistic regression, model building in Python/R) and hold AWS ML/GenAI certifications.",
    "nlp": "I supported an NLP-powered AI proof of concept (the mPADNA 'Dialogue Box') on AWS during my internship.",
    "aws": "I am AWS GenAI certified and worked hands-on with AWS deploying an NLP AI PoC during my internship.",
    "dashboard": "I have built automated, real-time dashboards in Tableau for leadership decision-making.",
    "governance": "I worked directly on data governance, auditing self-assessments and testing CLS/RLS security controls.",
    "security": "I tested Column-Level and Row-Level Security and user access controls to keep sensitive data safe.",
    "statistics": "I apply statistical methods (ANOVA, Chi-squared, MLR, discriminant/conjoint analysis) to real problems.",
}


def match_skills(job_text):
    jt = " " + job_text.lower() + " "
    hits = [v for k, v in KEYWORDS.items() if k in jt]
    return hits[:5]


def generate_answers(job_text, company, role, questions):
    profile = load_profile()
    lib = load_library()
    sf = lib["standing_facts"]
    nb = lib["base_narratives"]
    matched = match_skills(job_text)

    out = []
    for q in questions:
        q_clean = q.strip()
        if not q_clean:
            continue
        ql = q_clean.lower()
        ans = None

        if any(w in ql for w in ["year", "how many years", "experience with", "years of"]):
            ans = answer_experience_question(q_clean)
        elif "authori" in ql or "work permit" in ql or "eligible to work" in ql or "citizen" in ql:
            ans = sf["work_authorization"]
        elif "sponsor" in ql or "visa" in ql:
            ans = sf["require_sponsorship"]
        elif "start" in ql or "available" in ql or "notice" in ql or "join" in ql:
            ans = sf["earliest_start_date"]
        elif "relocat" in ql:
            ans = sf["willing_to_relocate"]
        elif "salary" in ql or "compensation" in ql or "expected pay" in ql:
            ans = sf["salary_expectation"]
        elif "gpa" in ql or "classification" in ql or "grade" in ql or "honours" in ql or "honors" in ql:
            ans = sf["gpa_classification"]
        elif "hear about" in ql or "how did you" in ql:
            ans = sf["how_did_you_hear"]
        elif "why" in ql and ("you" in ql or "us" in ql or "company" in ql or "role" in ql or "interest" in ql):
            reason = f"your work and this {role or 'role'}" if not company else f"{company} and this {role or 'role'}"
            skill_line = (" " + matched[0]) if matched else ""
            ans = (f"I'm drawn to {reason} because it directly matches my data science and analytics background. "
                   f"{nb['pitch']}" + (f" In particular,{skill_line}" if skill_line else ""))
        elif "strength" in ql or "why should we" in ql or "good fit" in ql or "suitable" in ql:
            ans = nb["strengths"] + (f" Relevant to this role: {' '.join(matched)}" if matched else "")
        elif "tell us about yourself" in ql or "introduce" in ql or "about you" in ql:
            ans = nb["pitch"]
        elif "team" in ql or "collaborat" in ql:
            ans = nb["teamwork"]
        elif "challeng" in ql or "difficult" in ql or "problem you solved" in ql or "describe a time" in ql:
            ans = ("During my PA internship I migrated and tested data for an NLP AI proof of concept on AWS while "
                   "ensuring strict data security (CLS/RLS). Balancing a working demo against zero tolerance for data "
                   "leakage was challenging; I solved it by methodically testing access controls layer by layer, "
                   "which let the 'Dialogue Box' go live securely.")
        else:
            # Fallback: a tailored general answer
            ans = (f"{nb['pitch']}"
                   + (f" This is directly relevant here because {matched[0].lower()}" if matched else ""))

        out.append({"question": q_clean, "answer": ans})
    return {
        "company": company,
        "role": role,
        "matched_skills": matched,
        "answers": out,
    }


def generate_cover_letter(job_text, company, role):
    """Produce a tailored one-page cover letter drawn from the profile + matched skills."""
    profile = load_profile()
    p = profile["personal"]
    matched = match_skills(job_text)
    company = company or "your team"
    role = role or "this role"

    # Pick the two most relevant skill lines to weave in
    skill_sentences = " ".join(matched[:2]) if matched else (
        "I work fluently in Python, R, SQL, and Tableau across end-to-end analysis.")

    body = f"""Dear Hiring Manager,

I am writing to apply for the {role} position at {company}. As a penultimate-year BSc Data Science and Business Analytics student at the University of London (LSE), on track for an Upper Second Class Honours, I bring hands-on experience in end-to-end data analysis, machine learning, and business intelligence that maps closely to what this role requires.

During my Data Management internship at the People's Association, I built an automated Tableau audit dashboard that streamed live data from FormSG so leadership could monitor compliance in real time, and I supported an NLP-powered AI proof of concept on AWS while rigorously testing Column- and Row-Level Security to keep sensitive data safe. Across my analytics projects — from behavioural and monetization analysis of in-app currency to a global sales dataset and a large-scale flight-delay study — I have turned messy data into clear, actionable recommendations. {skill_sentences}

What draws me to {company} is the chance to apply these skills where they create real impact. I am AWS Generative AI certified, comfortable moving from raw data to a decision-ready dashboard or model, and used to collaborating under pressure through my Data Analytics Club and leadership roles. I am a Singapore Citizen available from June 2027 and open to relocation.

I would welcome the opportunity to discuss how I can contribute to {company}. Thank you for your consideration.

Sincerely,
{p['full_name']}
{p['email']} | {p['phone']}
{p['linkedin']}"""
    return body


if __name__ == "__main__":
    # quick self-test
    print("=== COVER LETTER ===")
    print(generate_cover_letter(
        "Data Analyst role using Python, SQL, Tableau and machine learning.",
        "Grab", "Data Analyst"))
    print("\n=== ANSWERS ===")
    r = generate_answers(
        "Looking for a Data Analyst with Python, SQL and Tableau. Machine learning a plus.",
        "Acme Analytics", "Data Analyst",
        ["Why do you want to work here?",
         "How many years of professional experience do you have, excluding internships?",
         "Are you authorized to work in Singapore?",
         "When can you start?",
         "Expected salary?"],
    )
    print(json.dumps(r, indent=2))
