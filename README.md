# JobHunt — Jie Ming's application assistant

A local toolkit (runs entirely on your Mac, no installs beyond built-in Python 3) that:

1. **Finds fresh jobs** — one-click search links for **Indeed SG, JobsDB SG, MyCareersFuture, LinkedIn, Glassdoor**, all pre-filtered to your roles + Singapore + sorted newest-first.
2. **Auto-polls company boards** — checks public ATS APIs (Greenhouse / Lever / Ashby) for brand-new data/analytics roles and fires a **desktop alert** when new ones appear. This part is fully automated and ToS-safe. **Filtered to Singapore only** (plus APAC/Asia-remote roles that are SG-eligible); postings with no stated location are kept but flagged "verify it's Singapore". To allow worldwide roles, set `SG_ONLY = False` in `sources.py`.
3. **Generates tailored answers** — paste a job description + its screening questions, get ready-to-paste answers drawn from *your* resume (experience logic included: "0" when a question excludes internships, PA internship counted otherwise).
4. **Generates a tailored cover letter** per posting — one click, drawn from your resume.
5. **Tracks applications** — logs every draft, status, and date.
6. **Alerts you when a draft is ready** — a macOS notification says "ready to submit"; you open your browser and submit.
7. **Background auto-poller** — `poller.py` checks your company boards on a schedule and alerts you on new roles with zero clicks.

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

## Run the background auto-poller (optional, hands-free alerts)

```bash
python3 poller.py        # checks company boards every 30 min, alerts on new roles
python3 poller.py 15     # every 15 min
```

To have it start automatically and run quietly in the background, you can add it to `cron`
(`crontab -e`) — but note cron can't show desktop notifications on macOS. The simplest
reliable approach on a Mac is to just leave `python3 poller.py` running in a Terminal tab,
or set it up as a `launchd` agent. Running it manually in a tab is perfectly fine to start.

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
- `poller.py` — background auto-poller with desktop alerts.

## Tips

- **Add companies to auto-poll:** open a company's careers page. If the URL contains `boards.greenhouse.io/XXX`, `jobs.lever.co/XXX`, or `jobs.ashbyhq.com/XXX`, add `{"ats":"greenhouse","token":"XXX","label":"Name"}` to `companies.json`.
- **Edit your answers:** every generated answer is a starting point. Personalising one or two lines per application is what gets interviews.
