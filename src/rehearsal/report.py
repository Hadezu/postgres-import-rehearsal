"""Offline, escaped, read-only review. No CDN, analytics, or database credentials."""

from jinja2 import Environment

TEMPLATE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Import Rehearsal · Evidence review</title>
<style>
:root{color-scheme:dark;--bg:#0c1422;--panel:#131f31;--line:#2c3c52;--muted:#a9b7c9;--ink:#eef4ff;--teal:#72e0c5;--gold:#ffd38b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,sans-serif}
main{max-width:1200px;margin:auto;padding:48px 28px}header{border-bottom:1px solid var(--line);padding-bottom:30px}
.eyebrow{color:var(--teal);font-size:12px;font-weight:700;letter-spacing:.18em;text-transform:uppercase}
h1{font-size:clamp(32px,5vw,54px);letter-spacing:-.045em;line-height:1.08;margin:18px 0}h2{font-size:23px;margin:0 0 12px}
p{max-width:760px}small,.muted{color:var(--muted)}nav{display:flex;gap:9px;flex-wrap:wrap;margin:26px 0}
button{cursor:pointer;background:transparent;color:var(--ink);border:1px solid var(--line);padding:11px 16px;border-radius:8px;font:inherit}
button[aria-selected=true]{background:var(--teal);color:#0c1422;border-color:var(--teal)}button:focus-visible{outline:3px solid var(--gold);outline-offset:3px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:22px 0}.card,.meta,.notice{border:1px solid var(--line);background:var(--panel);border-radius:12px;padding:20px}
.card strong{display:block;font-size:32px;color:var(--teal)}.status{display:inline-block;background:#1c3541;color:var(--teal);padding:4px 12px;border-radius:30px;font-size:13px;font-weight:700}
.notice{border-left:4px solid var(--gold);margin:18px 0;color:var(--gold)}code{overflow-wrap:anywhere;font-size:13px}.meta{margin:18px 0;font-size:14px}.meta div{margin:6px 0}
.table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:12px}table{border-collapse:collapse;width:100%;min-width:690px;text-align:left}td,th{padding:14px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.06em}
.diff{display:block}.old{color:var(--muted)}.new{color:var(--teal)}footer{margin-top:28px;color:var(--muted);font-size:13px}details{margin:18px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}
@media(max-width:650px){main{padding:24px 16px}.grid{grid-template-columns:1fr}.card{padding:12px 18px}.card strong{font-size:25px}}
</style></head><body><main><header><div class="eyebrow">PostgreSQL · Chinook adapter · Independent demonstration</div>
<h1>Review first.<br>Apply exactly. Undo carefully.</h1><p class="muted">A real database import with an inspectable plan. This read-only evidence file cannot apply changes. Synthetic customers; existing invoice relationships.</p></header>
<nav aria-label="Evidence steps">{% for p in plans %}<button id="tab-{{loop.index0}}" aria-selected="{{'true' if loop.first else 'false'}}" aria-controls="step-{{loop.index0}}" onclick="selectStep({{loop.index0}})">{{p.get('label',p.status)}}</button>{% endfor %}</nav>
{% for p in plans %}<section id="step-{{loop.index0}}" aria-labelledby="tab-{{loop.index0}}" {% if not loop.first %}hidden{% endif %}>
<h2>{{p.get('label','Import plan')}} <span class="status">{{p.status}}</span></h2>
{% if p.get('note') %}<div class="notice">{{p.note}}</div>{% endif %}
<div class="grid">{% for k in ['INSERT','UPDATE','UNCHANGED'] %}<div class="card"><span>{{k|title}}</span><strong>{{p.payload.counts.get(k,0)}}</strong><small>Planned customer rows</small></div>{% endfor %}</div>
<div class="meta"><div>Plan <code>{{p.id}}</code></div><div>Review digest <code>{{p.digest}}</code></div><div>Source SHA-256 <code>{{p.payload.source_sha256}}</code></div><div>Adapter <code>{{p.payload.adapter}}</code> · Target <code>{{p.payload.target_id}}</code></div></div>
<div class="table-wrap"><table><thead><tr><th>ID / action</th><th>Customer</th><th>Before → proposed</th><th>Version at preview</th></tr></thead><tbody>
{% for e in p.payload.entries %}<tr><td>{{e.after.customer_id}}<br><small>{{e.action}}</small></td><td>{{e.after.first_name}} {{e.after.last_name}}<br><small>{{e.after.email}}</small></td><td>
{% for key in ['first_name','last_name','email','company','country','support_rep_id'] %}{% if not e.before.row or e.before.row[key] != e.after[key] %}<span class="diff"><small>{{key}}</small> <span class="old">{{e.before.row[key] if e.before.row else '∅'}}</span> → <span class="new">{{e.after[key]}}</span></span>{% endif %}{% endfor %}{% if e.action=='UNCHANGED' %}No field changes{% endif %}</td><td>{{e.before.revision}}</td></tr>{% endfor %}
</tbody></table></div>
{% if p.get('database') %}<div class="meta"><strong>Database readback at this step</strong><pre>{{p.database|tojson(indent=2)}}</pre></div>{% endif %}
<details><summary>Committed transaction events</summary><pre>{{p.get('events',[])|tojson(indent=2)}}</pre></details>
</section>{% endfor %}
<footer>Snapshot, not a live status monitor. Re-read the plan before acting. Reviews contain row data: use synthetic fixtures for public sharing. An undo refusal preserves later work; it is not a claim that every migration is reversible.</footer></main>
<script>function selectStep(i){document.querySelectorAll('section').forEach((s,j)=>s.hidden=j!==i);document.querySelectorAll('nav button').forEach((b,j)=>b.setAttribute('aria-selected',String(j===i)));}</script></body></html>"""


def render(plans):
    return Environment(autoescape=True).from_string(TEMPLATE).render(plans=plans)
