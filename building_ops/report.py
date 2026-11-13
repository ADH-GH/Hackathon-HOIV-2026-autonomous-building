"""Decision viewer: one self-contained HTML file from decisions.jsonl.

Shows, per decision, what the brief asks an interface to show: evidence, risk
(priority), the decision, the autonomy level and approvals, and the
verification plan, plus the simulated action trail if given. No server, no
dependencies; it opens from disk and works offline.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read(path: str | Path | None) -> list[dict[str, Any]]:
    if not path or not Path(path).is_file():
        return []
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def build(decisions_path: str | Path, out: str | Path, actions_path: str | Path | None = None,
          title: str = "PLATO-40 decision trail", sample: bool = False) -> Path:
    payload = {
        "title": title,
        "sample": sample,
        "source": str(decisions_path),
        "decisions": _read(decisions_path),
        "actions": {a["event_id"]: a for a in _read(actions_path)},
    }
    # "</" must not appear inside the script element.
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(PAGE.replace("__DATA__", data).replace("__TITLE__", title), encoding="utf-8")
    return out


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#f6f5f1;--panel:#fff;--ink:#1c1b19;--mute:#6b675f;--line:#dedad0;--accent:#b4541a;
--crit:#b3261e;--high:#b4541a;--med:#8a6d00;--low:#4d6b4f;--auto:#2f6b4a;--appr:#8a6d00;--cons:#b3261e}
@media (prefers-color-scheme:dark){:root{--bg:#171614;--panel:#211f1c;--ink:#ece8df;--mute:#a09a8d;--line:#39352f;
--accent:#e08a4c;--crit:#f2776f;--high:#e08a4c;--med:#d6b84a;--low:#8fb593;--auto:#7fc49c;--appr:#d6b84a;--cons:#f2776f}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
header{padding:20px 16px 12px;border-bottom:1px solid var(--line)}
h1{margin:0;font-size:22px}
.sub{color:var(--mute);font-size:13px;margin-top:4px;overflow-wrap:anywhere}
.banner{margin-top:10px;padding:8px 12px;border:1px solid var(--crit);color:var(--crit);border-radius:6px;font-weight:600}
.stats{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:6px 12px;min-width:92px}
.stat b{display:block;font-size:20px}
.stat span{font-size:12px;color:var(--mute)}
.filters{display:flex;flex-wrap:wrap;gap:8px;padding:12px 16px;border-bottom:1px solid var(--line)}
select,input{font:inherit;color:var(--ink);background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:6px 8px}
input{flex:1;min-width:160px}
main{display:grid;grid-template-columns:minmax(280px,420px) 1fr;gap:0;min-height:60vh}
@media (max-width:760px){main{grid-template-columns:1fr}}
#list{border-right:1px solid var(--line);max-height:78vh;overflow:auto}
@media (max-width:760px){#list{border-right:0;border-bottom:1px solid var(--line);max-height:42vh}}
.row{padding:10px 16px;border-bottom:1px solid var(--line);cursor:pointer}
.row:hover,.row.on{background:var(--panel)}
.row.on{box-shadow:inset 3px 0 0 var(--accent)}
.row .t{font-size:12px;color:var(--mute);font-variant-numeric:tabular-nums}
.row .a{font-weight:600;overflow-wrap:anywhere}
.tag{display:inline-block;font-size:11px;font-weight:600;border:1px solid currentColor;border-radius:999px;padding:0 8px;margin-right:4px}
.p-critical{color:var(--crit)}.p-high{color:var(--high)}.p-medium{color:var(--med)}.p-low{color:var(--low)}
.l-autonomous{color:var(--auto)}.l-human_approval{color:var(--appr)}.l-approval_and_consent{color:var(--cons)}
#detail{padding:16px;min-width:0}
#detail h2{margin:0 0 6px;font-size:19px;overflow-wrap:anywhere}
.sec{margin-top:16px}
.sec h3{margin:0 0 6px;font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--mute)}
.box{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:10px 12px;overflow-wrap:anywhere}
pre{margin:0;white-space:pre-wrap;overflow-wrap:anywhere;font:12.5px/1.45 ui-monospace,Menlo,Consolas,monospace}
.sim{color:var(--mute);font-size:13px}
.empty{padding:32px 16px;color:var(--mute)}
</style>
</head>
<body>
<header>
  <h1 id="title"></h1>
  <div class="sub" id="source"></div>
  <div class="banner" id="banner" hidden>Sample data. These decisions were written by hand to show the interface. They are not results.</div>
  <div class="stats" id="stats"></div>
</header>
<div class="filters">
  <select id="f-issue" aria-label="Issue type"></select>
  <select id="f-priority" aria-label="Priority"></select>
  <select id="f-level" aria-label="Autonomy"></select>
  <input id="f-text" type="search" placeholder="Filter by asset, episode or text" aria-label="Text filter">
</div>
<main>
  <div id="list"></div>
  <div id="detail"></div>
</main>
<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const $ = id => document.getElementById(id);
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
const level = d => d.autonomy || (d.requires_guest_consent ? 'approval_and_consent' : d.requires_human_approval ? 'human_approval' : 'autonomous');
const LEVEL = {autonomous: 'autonomous', human_approval: 'human approval', approval_and_consent: 'approval + guest consent'};
let selected = null;

$('title').textContent = D.title;
$('source').textContent = 'Source: ' + D.source + ' · times in Vienna local time (CET/CEST), UTC in the detail view · fictional property, synthetic data';
const vienna = new Intl.DateTimeFormat('sv-SE', {timeZone: 'Europe/Vienna', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', timeZoneName: 'short'});
const lt = iso => vienna.format(new Date(iso));
$('banner').hidden = !D.sample;

function stats() {
  const n = D.decisions.length;
  const count = f => D.decisions.filter(f).length;
  const items = [[n, 'decisions'], [new Set(D.decisions.map(d => d.episode_id)).size, 'episodes'],
    [count(d => level(d) === 'autonomous'), 'autonomous'], [count(d => level(d) === 'human_approval'), 'need approval'],
    [count(d => level(d) === 'approval_and_consent'), 'need consent'], [count(d => d.priority === 'critical'), 'critical']];
  for (const [v, label] of items) { const s = el('div', 'stat'); s.append(el('b', null, v), el('span', null, label)); $('stats').append(s); }
}

function options(id, label, values, names) {
  const s = $(id); s.append(new Option(label + ': all', ''));
  for (const v of values) s.append(new Option(names ? names[v] || v : v, v));
  s.onchange = render;
}

function visible() {
  const issue = $('f-issue').value, pr = $('f-priority').value, lv = $('f-level').value, q = $('f-text').value.trim().toLowerCase();
  return D.decisions.filter(d => (!issue || d.issue_type === issue) && (!pr || d.priority === pr) && (!lv || level(d) === lv)
    && (!q || JSON.stringify(d).toLowerCase().includes(q)));
}

function render() {
  const rows = visible(); const list = $('list'); list.replaceChildren();
  if (!rows.length) { list.append(el('div', 'empty', D.decisions.length ? 'No decision matches the filter.' : 'No decisions in this file.')); }
  if (!rows.includes(selected)) selected = rows[0] || null;
  for (const d of rows) {
    const r = el('div', 'row' + (d === selected ? ' on' : ''));
    r.append(el('div', 't', lt(d.timestamp_utc) + ' · ' + (d.affected_assets || []).slice(0, 4).join(', ') + ((d.affected_assets || []).length > 4 ? ' +' + (d.affected_assets.length - 4) : '')));
    r.append(el('div', 'a', d.action + ' · ' + d.issue_type));
    const tags = el('div'); tags.append(el('span', 'tag p-' + d.priority, d.priority), el('span', 'tag l-' + level(d), LEVEL[level(d)]));
    r.append(tags); r.onclick = () => { selected = d; render(); };
    list.append(r);
  }
  detail();
}

function section(title, node) { const s = el('div', 'sec'); s.append(el('h3', null, title)); const b = el('div', 'box'); b.append(node); s.append(b); return s; }
function text(t) { return el('div', null, t); }
function json(v) { return el('pre', null, JSON.stringify(v, null, 2)); }

function detail() {
  const box = $('detail'); box.replaceChildren();
  const d = selected; if (!d) { box.append(el('div', 'empty', 'Select a decision.')); return; }
  box.append(el('h2', null, d.action + ' · ' + (d.affected_assets || []).slice(0, 6).join(', ') + ((d.affected_assets || []).length > 6 ? ' and ' + (d.affected_assets.length - 6) + ' more' : '')));
  const tags = el('div'); tags.append(el('span', 'tag p-' + d.priority, 'risk: ' + d.priority), el('span', 'tag l-' + level(d), LEVEL[level(d)]));
  if (d.confidence != null) tags.append(el('span', 'tag', 'confidence ' + d.confidence));
  box.append(tags, el('div', 'sub', lt(d.timestamp_utc) + ' (' + d.timestamp_utc + ') · episode ' + d.episode_id + ' · ' + d.event_id));
  if (d.proposed_message) box.append(section('Proposed guest message (' + (d.message_language || '') + ')', text(d.proposed_message)));
  box.append(section('Decision and reason', text(d.reason)));
  box.append(section('Evidence', d.evidence && d.evidence.length ? (d.evidence.every(e => typeof e === 'string') ? el('pre', null, d.evidence.join('\n')) : json(d.evidence)) : text('No evidence recorded.')));
  const approvals = level(d) === 'autonomous' ? 'May run without approval. Logged and explainable.'
    : level(d) === 'human_approval' ? 'Waits for a human to approve.' : 'Waits for human approval and guest consent. Consent is needed, not granted.';
  box.append(section('Autonomy and approval', text(approvals)));
  box.append(section('Expected outcome', text(d.expected_outcome || 'Not stated.')));
  box.append(section('Verification', text(d.verification_plan || 'No verification plan recorded.')));
  if (d.dependencies && d.dependencies.length) box.append(section('Depends on', json(d.dependencies)));
  if (d.guest_request_ids && d.guest_request_ids.length) box.append(section('Guest requests', json(d.guest_request_ids)));
  const a = D.actions[d.event_id];
  if (a) { const n = el('div'); n.append(text('Status: ' + a.status), el('div', 'sim', 'Simulated. ' + a.note)); box.append(section('Action trail (mock executor)', n)); }
}

stats();
options('f-issue', 'Issue', [...new Set(D.decisions.map(d => d.issue_type))].sort());
options('f-priority', 'Priority', ['critical', 'high', 'medium', 'low']);
options('f-level', 'Autonomy', Object.keys(LEVEL), LEVEL);
$('f-text').oninput = render;
render();
</script>
</body>
</html>
"""
