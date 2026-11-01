"""Application tracker backed by a local JSON file."""
import json
import os
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "applications.json")


def _load():
    if not os.path.exists(DB):
        return {"applications": [], "seen_job_ids": []}
    with open(DB) as f:
        return json.load(f)


def _save(d):
    with open(DB, "w") as f:
        json.dump(d, f, indent=2)


def add_application(company, role, url, status="drafted", answers=None, notes=""):
    d = _load()
    d["applications"].append({
        "id": len(d["applications"]) + 1,
        "company": company,
        "role": role,
        "url": url,
        "status": status,  # drafted | ready_to_submit | submitted | interview | rejected | offer
        "answers": answers or [],
        "notes": notes,
        "created": datetime.now().isoformat(timespec="seconds"),
        "updated": datetime.now().isoformat(timespec="seconds"),
    })
    _save(d)
    return d["applications"][-1]


def update_status(app_id, status):
    d = _load()
    for a in d["applications"]:
        if a["id"] == app_id:
            a["status"] = status
            a["updated"] = datetime.now().isoformat(timespec="seconds")
    _save(d)


def list_applications():
    return _load()["applications"]


def mark_seen(job_ids):
    d = _load()
    seen = set(d.get("seen_job_ids", []))
    new = [j for j in job_ids if j not in seen]
    seen.update(job_ids)
    d["seen_job_ids"] = list(seen)
    _save(d)
    return new  # returns only the genuinely new ids


def already_seen(job_id):
    return job_id in set(_load().get("seen_job_ids", []))
