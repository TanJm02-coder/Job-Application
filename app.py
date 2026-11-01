"""
JobHunt local dashboard — runs entirely on your Mac, no external services.

Run:   python3 app.py
Open:  http://localhost:8765

Features:
  - Paste a job description + screening questions -> get tailored, ready-to-paste answers
  - Save the draft to your tracker and fire a desktop ALERT ("ready to submit")
  - Poll company ATS boards for brand-new roles (ToS-safe) and alert on new ones
  - Quick links to Indeed SG / JobsDB SG / MyCareersFuture / LinkedIn (newest first)

No passwords are ever stored. The final submit is done by you in your own browser.
"""
import json
import os
import subprocess
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import engine
import sources
import tracker

BASE = os.path.dirname(os.path.abspath(__file__))
PORT = 8765


def desktop_alert(title, message):
    """macOS native notification via osascript (no install needed)."""
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{message}" with title "{title}" sound name "Glass"'],
            check=False,
        )
    except Exception:
        pass  # non-Mac or no osascript — dashboard still works


PAGE = """<!doctype html><html><head><meta charset="utf-8">
<title>JobHunt — Tan Jie Ming</title>
<style>
 body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:900px;margin:24px auto;padding:0 16px;color:#1b1b1b}
 h1{font-size:22px} h2{font-size:17px;margin-top:28px;border-bottom:1px solid #eee;padding-bottom:6px}
 textarea,input{width:100%;box-sizing:border-box;font-size:14px;padding:8px;border:1px solid #ccc;border-radius:6px}
 textarea{height:120px;font-family:ui-monospace,monospace}
 button{background:#1363DF;color:#fff;border:0;padding:10px 16px;border-radius:6px;font-size:14px;cursor:pointer;margin-top:8px}
 button.secondary{background:#444}
 .qa{background:#f6f8fb;border:1px solid #e3e8ef;border-radius:8px;padding:12px;margin:10px 0}
 .qa b{display:block;margin-bottom:6px}
 .links a{display:inline-block;margin:4px 8px 4px 0;padding:6px 10px;background:#eef3fb;border-radius:6px;text-decoration:none;color:#1363DF;font-size:13px}
 .row{display:flex;gap:10px}.row>div{flex:1}
 .badge{font-size:12px;background:#e8f5e9;color:#2e7d32;padding:2px 8px;border-radius:10px}
 .job{border:1px solid #e3e8ef;border-radius:8px;padding:10px;margin:8px 0}
 .copy{background:#666;font-size:12px;padding:5px 10px;margin:4px 0 0}
 .muted{color:#777;font-size:13px}
</style></head><body>
<h1>JobHunt Dashboard <span class="muted">— Tan Jie Ming</span></h1>
<p class="muted">Paste a job + its questions below. You review the answers and submit in your own browser.
No passwords stored; final submit is always yours.</p>

<h2>1. Fresh jobs — search links (newest first)</h2>
<div class="links" id="links"></div>

<h2>2. Auto-polled company boards (ToS-safe)</h2>
<button class="secondary" onclick="pollJobs()">Check company boards for new roles</button>
<div id="pollresult"></div>

<h2>3. Generate answers for an application</h2>
<div class="row">
 <div><label>Company</label><input id="company" placeholder="e.g. Grab"></div>
 <div><label>Role</label><input id="role" placeholder="e.g. Data Analyst"></div>
</div>
<label style="margin-top:8px;display:block">Job URL</label><input id="url" placeholder="https://...">
<label style="margin-top:8px;display:block">Job description (paste full text)</label>
<textarea id="jobtext"></textarea>
<label style="margin-top:8px;display:block">Application questions (one per line)</label>
<textarea id="questions" placeholder="Why do you want to work here?
How many years of experience, excluding internships?
Are you authorized to work in Singapore?
When can you start?
Expected salary?"></textarea>
<button onclick="gen()">Generate tailored answers</button>
<button class="secondary" onclick="genLetter()">Generate cover letter</button>
<div id="answers"></div>
<div id="letter"></div>

<h2>4. Your applications</h2>
<button class="secondary" onclick="loadApps()">Refresh tracker</button>
<div id="apps"></div>

<script>
async function loadLinks(){
 const r = await fetch('/links?kw='+encodeURIComponent(document.getElementById('role')?.value||'Data Analyst'));
 const d = await r.json(); const el=document.getElementById('links'); el.innerHTML='';
 for(const [k,v] of Object.entries(d)){const a=document.createElement('a');a.href=v;a.target='_blank';a.textContent=k;el.appendChild(a);} }
async function pollJobs(){
 document.getElementById('pollresult').innerHTML='<p class="muted">Checking…</p>';
 const r=await fetch('/poll'); const d=await r.json(); const el=document.getElementById('pollresult');
 if(!d.jobs.length){el.innerHTML='<p class="muted">No new matching roles right now.</p>';return;}
 el.innerHTML='<p><span class="badge">'+d.jobs.length+' new</span></p>'+d.jobs.map(j=>
  '<div class="job"><b>'+j.title+'</b><div class="muted">'+(j.location||'')+' · '+j.source+'</div><a href="'+j.url+'" target="_blank">Open posting ↗</a></div>').join(''); }
let lastAnswers=null, lastMeta=null;
async function gen(){
 const body={company:company.value,role:role.value,url:url.value,jobtext:jobtext.value,
   questions:document.getElementById('questions').value.split('\\n')};
 const r=await fetch('/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 const d=await r.json(); lastAnswers=d.answers; lastMeta={company:company.value,role:role.value,url:url.value};
 const el=document.getElementById('answers');
 el.innerHTML='<p class="muted">Matched skills: '+(d.matched_skills.length)+'</p>'+
  d.answers.map((a,i)=>'<div class="qa"><b>'+a.question+'</b><div id="a'+i+'">'+a.answer+'</div>'+
   '<button class="copy" onclick="copyA('+i+')">Copy answer</button></div>').join('')+
  '<button onclick="saveReady()">Save draft & alert me it\\'s ready to submit</button>'; }
function copyA(i){navigator.clipboard.writeText(document.getElementById('a'+i).innerText);}
async function genLetter(){
 const body={company:company.value,role:role.value,jobtext:jobtext.value};
 const r=await fetch('/coverletter',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 const d=await r.json();
 document.getElementById('letter').innerHTML='<div class="qa"><b>Cover letter</b>'+
  '<textarea style="height:300px">'+d.letter+'</textarea>'+
  '<button class="copy" onclick="copyLetter(this)">Copy cover letter</button></div>'; }
function copyLetter(btn){navigator.clipboard.writeText(btn.previousElementSibling.value);}
async function saveReady(){
 const r=await fetch('/save',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({...lastMeta,answers:lastAnswers})});
 const d=await r.json(); alert('Saved & alert sent — ready to submit in your browser. App #'+d.id); loadApps(); }
async function loadApps(){
 const r=await fetch('/apps'); const d=await r.json(); const el=document.getElementById('apps');
 if(!d.length){el.innerHTML='<p class="muted">No applications yet.</p>';return;}
 el.innerHTML=d.map(a=>'<div class="job"><b>'+a.role+' @ '+a.company+'</b> <span class="badge">'+a.status+'</span>'+
  '<div class="muted">'+a.created+'</div>'+(a.url?'<a href="'+a.url+'" target="_blank">Open ↗</a>':'')+'</div>').join(''); }
loadLinks(); loadApps();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        if isinstance(body, (dict, list)):
            body = json.dumps(body)
        self.wfile.write(body.encode("utf-8"))

    def do_GET(self):
        p = urllib.parse.urlparse(self.path)
        if p.path == "/":
            return self._send(200, PAGE, "text/html")
        if p.path == "/links":
            kw = urllib.parse.parse_qs(p.query).get("kw", ["Data Analyst"])[0]
            return self._send(200, sources.board_search_links(kw))
        if p.path == "/poll":
            try:
                with open(os.path.join(BASE, "companies.json")) as f:
                    companies = json.load(f)["companies"]
            except Exception:
                companies = []
            jobs = [j for j in sources.poll_companies(companies) if "error" not in j]
            new_ids = tracker.mark_seen([j["id"] for j in jobs])
            new_jobs = [j for j in jobs if j["id"] in new_ids]
            if new_jobs:
                desktop_alert("JobHunt: new roles!",
                              f"{len(new_jobs)} new matching role(s) found.")
            return self._send(200, {"jobs": new_jobs})
        if p.path == "/apps":
            return self._send(200, tracker.list_applications())
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(length) or "{}")
        p = urllib.parse.urlparse(self.path)
        if p.path == "/generate":
            res = engine.generate_answers(
                data.get("jobtext", ""), data.get("company", ""),
                data.get("role", ""), data.get("questions", []))
            return self._send(200, res)
        if p.path == "/coverletter":
            letter = engine.generate_cover_letter(
                data.get("jobtext", ""), data.get("company", ""), data.get("role", ""))
            return self._send(200, {"letter": letter})
        if p.path == "/save":
            app = tracker.add_application(
                data.get("company", ""), data.get("role", ""), data.get("url", ""),
                status="ready_to_submit", answers=data.get("answers", []))
            desktop_alert("JobHunt: ready to submit!",
                          f"{app['role']} @ {app['company']} — answers prefilled. Open your browser to submit.")
            return self._send(200, {"id": app["id"]})
        return self._send(404, {"error": "not found"})


if __name__ == "__main__":
    print(f"JobHunt dashboard running at http://localhost:{PORT}")
    print("Press Ctrl+C to stop.")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
