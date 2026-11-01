# JobHunt — Jie Ming's application assistant

A local toolkit (runs entirely on your Mac, no installs beyond built-in Python 3) that:

1. **Finds fresh jobs** — one-click search links for **Indeed SG, JobsDB SG, MyCareersFuture, LinkedIn, Glassdoor**, all pre-filtered to your roles + Singapore + sorted newest-first.
2. **Auto-polls company boards** — checks public ATS APIs (Greenhouse / Lever / Ashby) for brand-new data/analytics roles and fires a **desktop alert** when new ones appear. This part is fully automated and ToS-safe.
3. **Generates tailored answers** — paste a job description + its screening questions, get ready-to-paste answers drawn from *your* resume (experience logic included: "0" when a question excludes internships, PA internship counted otherwise).
4. **Tracks applications** — logs every draft, status, and date.
5. **Alerts you when a draft is ready** — a macOS notification says "ready to submit"; you open your browser and submit.

## First-time setup

Your real contact details are **not** stored in this public repo. After cloning, create your
local profile from the template and fill in your email/phone:

```bash
cp profile.example.json profile.json
# then open profile.json and replace YOUR_EMAIL@example.com and +65 XXXX XXXX
```

`profile.json` is git-ignored, so your personal details never get pushed.

## Run it

```bash
cd jobhunt
python3 app.py
```

Then open **http://localhost:8765** in your browser.

## Daily flow

1. Click a search link → scan newest roles → open one you like.
2. Copy the job description + its questions into the dashboard → **Generate tailored answers**.
3. Review/tweak the answers (they're *drafts in your voice* — always give them a quick read).
4. **Save draft & alert** → you get a notification → paste the answers into the real application and hit submit yourself.

## What this does NOT do (on purpose)

- It does **not** log into LinkedIn/Workday or auto-click submit. Those platforms ban automated applications — that risks a permanent ban on your account, and auto-filled answers get filtered out by recruiters anyway. The final submit is always yours (~10 seconds).
- It does **not** store any passwords. Your own details live in `profile.json`; use your browser or a password manager (1Password/Bitwarden) for logins.

## Files

- `profile.json` — your details & experience (edit anytime).
- `answer_library.json` — reusable base answers (edit into your own words).
- `companies.json` — companies to auto-poll (add ATS tokens from careers-page URLs).
- `engine.py` — answer generation + experience logic.
- `sources.py` — job search links + company-board polling.
- `tracker.py` — application tracker.
- `app.py` — the dashboard.

## Tips

- **Add companies to auto-poll:** open a company's careers page. If the URL contains `boards.greenhouse.io/XXX`, `jobs.lever.co/XXX`, or `jobs.ashbyhq.com/XXX`, add `{"ats":"greenhouse","token":"XXX","label":"Name"}` to `companies.json`.
- **Edit your answers:** every generated answer is a starting point. Personalising one or two lines per application is what gets interviews.
