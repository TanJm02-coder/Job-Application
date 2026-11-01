"""
Background auto-poller: checks your company boards on a schedule and fires a
macOS desktop alert whenever a NEW matching role appears — no clicking needed.

Run in the background:
    python3 poller.py            # polls every 30 min (default)
    python3 poller.py 15         # polls every 15 min

Stop it: Ctrl+C, or `pkill -f poller.py`.

This only hits public company ATS APIs (Greenhouse/Lever/Ashby) — ToS-safe.
"""
import json
import os
import subprocess
import sys
import time

import sources
import tracker

BASE = os.path.dirname(os.path.abspath(__file__))


def desktop_alert(title, message):
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{message}" with title "{title}" sound name "Glass"'],
            check=False,
        )
    except Exception:
        pass


def load_companies():
    try:
        with open(os.path.join(BASE, "companies.json")) as f:
            return json.load(f)["companies"]
    except Exception:
        return []


def poll_once():
    companies = load_companies()
    jobs = [j for j in sources.poll_companies(companies) if "error" not in j]
    new_ids = tracker.mark_seen([j["id"] for j in jobs])
    new_jobs = [j for j in jobs if j["id"] in new_ids]
    ts = time.strftime("%Y-%m-%d %H:%M")
    if new_jobs:
        titles = ", ".join(j["title"] for j in new_jobs[:3])
        more = f" +{len(new_jobs) - 3} more" if len(new_jobs) > 3 else ""
        desktop_alert("JobHunt: new role(s)!", f"{len(new_jobs)} new: {titles}{more}")
        print(f"[{ts}] {len(new_jobs)} NEW role(s):")
        for j in new_jobs:
            print(f"    - {j['title']} ({j.get('location','')}) — {j['url']}")
    else:
        print(f"[{ts}] checked {len(jobs)} roles, nothing new.")
    return new_jobs


def main():
    interval_min = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    print(f"JobHunt poller started — every {interval_min} min. Ctrl+C to stop.")
    while True:
        try:
            poll_once()
        except Exception as e:
            print(f"[poll error] {e}")
        time.sleep(interval_min * 60)


if __name__ == "__main__":
    main()
