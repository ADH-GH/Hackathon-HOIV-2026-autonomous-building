"""The dashboard page: HTML, CSS and JavaScript in one string. No external requests."""

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
/* Dark control-room look: deep background, layered panels, monospace figures, small caps labels.
   Dark is the default; a light theme is available through the toggle. No external fonts or requests. */
:root{--bg:#0b0f17;--panel:#121823;--raise:#182033;--ink:#e6edf3;--ink2:#a9b4c2;--mute:#77839a;--line:#263042;--grid:#1c2535;
--series:#4c9aff;--ref:#8b97ab;--accent:#2dd4a7;--glow:rgba(45,212,167,.14);--mark:#ffb020;--band:rgba(45,212,167,.10);
--crit:#ff6b6b;--high:#ffb020;--med:#d7c14a;--low:#7f8ea3;--auto:#3fb950;--appr:#ffb020;--cons:#ff6b6b;--ours:#4c9aff;
--mono:ui-monospace,"JetBrains Mono","SF Mono",Menlo,Consolas,monospace;--sans:Inter,system-ui,-apple-system,"Segoe UI",sans-serif}
:root[data-theme="light"]{--bg:#f4f5f7;--panel:#ffffff;--raise:#f0f2f5;--ink:#0d1117;--ink2:#47525f;--mute:#6b7785;--line:#d5dae1;--grid:#e6e9ee;
--series:#1f6fd0;--ref:#7b8794;--accent:#0f8f6f;--glow:rgba(15,143,111,.12);--mark:#b86a00;--band:rgba(15,143,111,.10);
--crit:#c62828;--high:#b86a00;--med:#7a6a00;--low:#5f6b7a;--auto:#1a7f37;--appr:#b86a00;--cons:#c62828;--ours:#1f6fd0}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14.5px/1.55 var(--sans);-webkit-font-smoothing:antialiased}
header{padding:20px 16px 0;max-width:1440px;margin:0 auto}
.top{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap}
.kicker{font:600 11px/1 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--accent)}
.kicker::before{content:"";display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 4px var(--glow);margin-right:9px;vertical-align:1px}
h1{margin:8px 0 0;font-size:27px;font-weight:650;letter-spacing:-.02em}
.sub{color:var(--mute);font-size:12.5px;margin-top:5px;overflow-wrap:anywhere}
#theme{font:600 11px/1 var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--ink2);background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:8px 10px;cursor:pointer}
nav{display:flex;gap:6px;flex-wrap:wrap;margin-top:16px;padding-bottom:12px;border-bottom:1px solid var(--line)}
nav button{font:500 13.5px/1 var(--sans);color:var(--ink2);background:transparent;border:1px solid transparent;border-radius:7px;padding:9px 12px;cursor:pointer}
nav button:hover{background:var(--panel)}
nav button.on{color:var(--ink);background:var(--panel);border-color:var(--line);box-shadow:inset 0 -2px 0 var(--accent)}
nav button span{font:500 11.5px/1 var(--mono);color:var(--mute);margin-left:7px}
.wrap{max-width:1440px;margin:0 auto;padding:16px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(158px,1fr));gap:10px}
.tile{background:linear-gradient(180deg,var(--raise),var(--panel));border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.tile b{display:block;font:600 28px/1.1 var(--mono);letter-spacing:-.02em}
.tile span{display:block;font:600 10.5px/1.35 var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--ink2);margin-top:7px}
.tile small{display:block;font-size:11.5px;color:var(--mute);margin-top:4px}
.tile.key{border-color:var(--accent);box-shadow:0 0 0 3px var(--glow)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin-top:12px;min-width:0}
.card h2{margin:0 0 4px;font:600 11.5px/1.3 var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--ink2)}
.card p.note{margin:0 0 10px;color:var(--mute);font-size:12.5px}
.split{display:grid;grid-template-columns:minmax(270px,370px) 1fr;gap:12px;align-items:start}
@media (max-width:820px){.split{grid-template-columns:1fr}}
.list{background:var(--panel);border:1px solid var(--line);border-radius:10px;max-height:80vh;overflow:auto}
@media (max-width:820px){.list{max-height:38vh}}
.list .tools{padding:10px 12px;border-bottom:1px solid var(--line);font-size:12.5px;color:var(--ink2);position:sticky;top:0;background:var(--panel);z-index:1}
.row{padding:10px 12px;border-bottom:1px solid var(--grid);cursor:pointer}
.row:hover{background:var(--raise)}
.row.on{background:var(--raise);box-shadow:inset 3px 0 0 var(--accent)}
.row .t{font:400 11.5px/1.3 var(--mono);color:var(--mute)}
.row .a{font-weight:600;margin-top:2px;overflow-wrap:anywhere}
.tag{display:inline-block;font:600 10.5px/1.7 var(--mono);letter-spacing:.04em;border:1px solid currentColor;border-radius:999px;padding:0 8px;margin:3px 4px 0 0;white-space:nowrap}
.tag.p-critical::before,.tag.p-high::before,.tag.p-medium::before,.tag.p-low::before{content:"";display:inline-block;width:6px;height:6px;border-radius:50%;background:currentColor;margin-right:5px;vertical-align:1px}
.p-critical{color:var(--crit)}.p-high{color:var(--high)}.p-medium{color:var(--med)}.p-low{color:var(--low)}
.l-autonomous{color:var(--auto)}.l-human_approval{color:var(--appr)}.l-approval_and_consent{color:var(--cons)}
.tag.plain{color:var(--ink2)}
.detail .hero{margin-top:0;background:linear-gradient(180deg,var(--raise),var(--panel))}
.detail .hero h3{margin:0;font-size:21px;font-weight:650;letter-spacing:-.01em;overflow-wrap:anywhere}
.chain{display:grid;gap:8px;margin-top:8px}
.step{border:1px solid var(--line);border-left:3px solid var(--ours);border-radius:8px;padding:10px 12px;background:var(--raise);min-width:0}
.step .h{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.step .h b{font-size:15px;text-transform:capitalize}
.step .h time{font:400 11.5px/1 var(--mono);color:var(--mute)}
.step p{margin:7px 0 0;overflow-wrap:anywhere}
.step .k{font:600 10px/1 var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--mute);margin-top:10px}
.step pre{margin:4px 0 0;white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.5 var(--mono);color:var(--ink2)}
.step .v{margin-top:4px;color:var(--ink2)}
.msg{margin-top:8px;padding:9px 11px;border-radius:8px;background:var(--panel);border:1px dashed var(--line)}
.check{border:1px dashed var(--mute);border-radius:8px;padding:9px 12px;margin-top:12px;font-size:13.5px;color:var(--ink2)}
.check b{color:var(--ink)}
.legend{display:flex;flex-wrap:wrap;gap:16px;font-size:12px;color:var(--ink2);margin:2px 0 6px}
.legend i{display:inline-block;width:18px;height:0;border-top:2px solid var(--series);vertical-align:middle;margin-right:6px}
.legend i.ref{border-top:2px dashed var(--ref)}
.legend i.mark{border-top:0;border-left:2px solid var(--mark);height:12px;width:0}
svg{display:block;width:100%;height:auto;overflow:visible}
svg text{font:10.5px var(--mono);fill:var(--mute)}
svg .lbl{fill:var(--ink2)}
#tip{position:fixed;pointer-events:none;background:var(--ink);color:var(--bg);font-size:12px;line-height:1.4;padding:7px 9px;border-radius:6px;max-width:300px;z-index:9;display:none}
.log{margin:6px 0 0;padding:0;list-style:none;font-size:13.5px}
.log li{display:grid;grid-template-columns:104px 1fr;gap:8px;padding:5px 0;border-bottom:1px solid var(--grid)}
.log time{font:400 11.5px/1.7 var(--mono);color:var(--mute)}
.log .ours{color:var(--ours);font-weight:600}
.bars{display:grid;gap:7px;margin-top:6px}
.bar{display:grid;grid-template-columns:56px 1fr 64px;gap:10px;align-items:center;font:400 12.5px/1 var(--mono);color:var(--ink2)}
.bar div{height:10px;border-radius:0 4px 4px 0;background:var(--series)}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{text-align:left;padding:8px 8px;border-bottom:1px solid var(--grid);vertical-align:top}
th{font:600 10.5px/1.3 var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--mute)}
td.n{text-align:right;font-family:var(--mono);white-space:nowrap}
td.m{font:400 12px/1.6 var(--mono);color:var(--ink2);white-space:nowrap}
tr.go{cursor:pointer}tr.go:hover{background:var(--raise)}
.scroll{overflow-x:auto}
.empty{padding:28px 14px;color:var(--mute)}
input[type=search]{font:inherit;color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:7px;padding:6px 9px;width:100%;margin-top:8px}
.act{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:10px;padding-top:10px;border-top:1px dashed var(--line)}
.act button{font:600 12px/1 var(--mono);letter-spacing:.04em;border-radius:6px;padding:8px 12px;cursor:pointer;border:1px solid var(--line);background:var(--panel);color:var(--ink)}
.act button.ok{border-color:var(--auto);color:var(--auto)}
.act button.no{border-color:var(--crit);color:var(--crit)}
.act button:disabled{opacity:.4;cursor:not-allowed}
.act label{font-size:12.5px;color:var(--ink2)}
.act .state{font:600 12px/1.4 var(--mono)}
.act .state.approved{color:var(--auto)}.act .state.rejected{color:var(--crit)}
.act small{flex-basis:100%;color:var(--mute);font-size:11.5px}
@media (max-width:700px){
  header{padding:16px 12px 0}.wrap{padding:12px}h1{font-size:22px}
  nav{flex-wrap:nowrap;overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:none}nav::-webkit-scrollbar{display:none}nav button{white-space:nowrap;flex:0 0 auto}
  .tiles{grid-template-columns:repeat(2,minmax(0,1fr))}.tile b{font-size:23px}
  .card{padding:12px}.scroll table{min-width:680px}
  .step .h b{flex-basis:100%}.act button{padding:11px 14px}
  .log li{grid-template-columns:1fr;gap:0}
  svg text{font-size:11px}
}
footer{max-width:1440px;margin:0 auto;padding:4px 16px 28px;color:var(--mute);font-size:12px}
</style>
</head>
<body>
<header>
  <div class="top">
    <div>
      <div class="kicker">Autonomous building operations · fictional reference property</div>
      <h1 id="title"></h1>
      <div class="sub" id="source"></div>
    </div>
    <button id="theme" type="button">Light</button>
  </div>
  <nav id="nav"></nav>
</header>
<div class="wrap" id="view"></div>
<footer>PLATO-40 synthetic dataset, proximata Hackathon '26 · Rhomberg track (CC BY 4.0). Every finding concerns the fictional PLATO-40 only. Simulated effects are labelled; nothing here was measured on a real building.</footer>
<div id="tip"></div>
<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const $ = id => document.getElementById(id);
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
const NS = 'http://www.w3.org/2000/svg';
const svg = (tag, attrs, text) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (text != null) e.textContent = text; return e; };
const fmt = (opts) => new Intl.DateTimeFormat('sv-SE', Object.assign({timeZone: 'Europe/Vienna'}, opts));
const F_FULL = fmt({year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', timeZoneName: 'short'});
const F_DAY = new Intl.DateTimeFormat('de-AT', {timeZone: 'Europe/Vienna', day: '2-digit', month: '2-digit'});
const F_HM = fmt({hour: '2-digit', minute: '2-digit'});
const F_DHM = new Intl.DateTimeFormat('de-AT', {timeZone: 'Europe/Vienna', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'});
const lt = ms => F_FULL.format(new Date(ms));
const dhm = ms => F_DHM.format(new Date(ms));
const level = d => d.autonomy || (d.requires_guest_consent ? 'approval_and_consent' : d.requires_human_approval ? 'human_approval' : 'autonomous');
const LEVEL = {autonomous: 'autonomous', human_approval: 'human approval', approval_and_consent: 'approval + guest consent'};
const SC = {S01: 'S01 Turnaround', S02: 'S02 Water', S03: 'S03 Heating', S04: 'S04 Maintenance'};
const KIND = {room_flow: 'Water leak in a room', main_gap: 'Water loss outside the rooms', room_meter: 'Unreliable water meter',
  cop: 'Heat pump degradation', forecast: 'Cold snap ahead', room_temp: 'Guest reports a cold room',
  room_day: 'Room turnaround', day_plan: 'Day capacity shortfall', ahu: 'Ventilation filter'};
const tsOf = d => Date.parse(d.timestamp_utc);
const E = D.episodes;
const all = E.flatMap(e => e.decisions);
let tab = 'overview', selected = {}, showRoutine = {}, query = '';
/* ---------- approvals: a person decides, the effect is simulated, the log stays in this browser ---------- */
const KEY = 'approvals:' + D.profile + ':' + D.source;
let approvals = {}; try { approvals = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (err) {}
const saveApprovals = () => { try { localStorage.setItem(KEY, JSON.stringify(approvals)); } catch (err) {} };
const needs = d => level(d) !== 'autonomous';
const pending = () => all.filter(d => needs(d) && !(approvals[d.event_id] && approvals[d.event_id].state));
function decide(d, state) { const a = approvals[d.event_id] || {}; approvals[d.event_id] = Object.assign(a, {state, at: new Date().toISOString(), action: d.action, assets: d.affected_assets, episode_id: d.episode_id, simulated: true}); saveApprovals(); render(); }
function controls(d) {
  const box = el('div', 'act'), a = approvals[d.event_id] || {}, consent = level(d) === 'approval_and_consent';
  if (a.state) { box.append(el('span', 'state ' + a.state, (a.state === 'approved' ? 'Approved' : 'Rejected') + ' ' + lt(Date.parse(a.at)) + (a.state === 'approved' ? ' · executed in simulation' : ' · not executed')));
    const undo = el('button', null, 'Undo'); undo.type = 'button'; undo.onclick = () => { delete approvals[d.event_id]; saveApprovals(); render(); }; box.append(undo); }
  else { const ok = el('button', 'ok', 'Approve'), no = el('button', 'no', 'Reject'); ok.type = no.type = 'button';
    if (consent) { const lb = el('label'), cb = el('input'); cb.type = 'checkbox'; cb.checked = !!a.consent; ok.disabled = !a.consent;
      cb.onchange = () => { approvals[d.event_id] = Object.assign(approvals[d.event_id] || {}, {consent: cb.checked}); saveApprovals(); ok.disabled = !cb.checked; };
      lb.append(cb, document.createTextNode(' Guest consent is on record')); box.append(lb); }
    ok.onclick = () => decide(d, 'approved'); no.onclick = () => decide(d, 'rejected'); box.append(ok, no); }
  box.append(el('small', null, 'Operator action in this demo. The replay does not change; the effect is simulated and the choice is kept in this browser only.'));
  return box;
}

$('title').textContent = D.title;
$('source').textContent = 'Dataset: ' + D.profile + ' · ' + all.length + ' decisions in ' + E.length + ' episodes · all times Vienna local time (CET/CEST) · PLATO-40 is fictional, the data is synthetic, effects of actions are simulated';

/* ---------- tooltip ---------- */
const tip = $('tip');
function showTip(ev, html) { tip.innerHTML = html; tip.style.display = 'block'; const w = tip.offsetWidth, h = tip.offsetHeight;
  tip.style.left = Math.max(4, Math.min(window.innerWidth - w - 4, ev.clientX + 12)) + 'px';
  tip.style.top = Math.max(4, ev.clientY - h - 10) + 'px'; }
function hideTip() { tip.style.display = 'none'; }
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));

/* ---------- line chart: one axis, hover crosshair ---------- */
function niceTicks(lo, hi, n) { const span = hi - lo || 1, step0 = Math.pow(10, Math.floor(Math.log10(span / n)));
  const step = [1, 2, 5, 10].map(m => m * step0).find(s => span / s <= n) || step0 * 10; const out = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(+v.toFixed(6)); return out; }
function lineChart(host, o) {
  const narrow = window.innerWidth < 700, W = narrow ? Math.max(300, window.innerWidth - 66) : 820, H = narrow ? 230 : 250, m = {l: narrow ? 34 : 46, r: narrow ? 8 : 14, t: 14, b: 26};
  const t = o.t, lines = o.lines.filter(l => l.v && l.v.some(v => v != null)).map(l => o.cap ? Object.assign({}, l, {raw: l.v, v: l.v.map(v => v == null ? null : Math.min(v, o.cap))}) : l);
  if (!t || !t.length || !lines.length) { host.append(el('div', 'empty', 'No readings in this window.')); return; }
  const vals = lines.flatMap(l => l.v.filter(v => v != null)).concat(o.band || []).concat(o.zero ? [0] : []);
  let lo = Math.min(...vals), hi = Math.max(...vals); const pad = (hi - lo || 1) * 0.08; lo -= o.zero && lo >= 0 ? 0 : pad; hi += pad;
  const t0 = t[0], t1 = t[t.length - 1] === t0 ? t0 + 1 : t[t.length - 1];
  const x = v => m.l + (v - t0) / (t1 - t0) * (W - m.l - m.r), y = v => H - m.b - (v - lo) / (hi - lo) * (H - m.t - m.b);
  const s = svg('svg', {viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': o.label});
  for (const v of niceTicks(lo, hi, 5)) { s.append(svg('line', {x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), stroke: 'var(--grid)'}));
    s.append(svg('text', {x: m.l - 6, y: y(v) + 4, 'text-anchor': 'end'}, v)); }
  if (o.band) s.append(svg('rect', {x: m.l, width: W - m.l - m.r, y: y(o.band[1]), height: y(o.band[0]) - y(o.band[1]), fill: 'var(--band)'}));
  const spanH = (t1 - t0) / 36e5, nt = narrow ? 2 : 5;
  for (let i = 0; i <= nt; i++) { const tv = t0 + (t1 - t0) * i / nt;
    s.append(svg('text', {x: x(tv), y: H - 8, 'text-anchor': i === 0 ? 'start' : i === nt ? 'end' : 'middle'}, spanH > 96 ? F_DAY.format(new Date(tv)) : dhm(tv))); }
  s.append(svg('text', {x: m.l, y: 10, class: 'lbl'}, o.unit));
  for (const l of lines) { let dpath = '', pen = false;
    l.v.forEach((v, i) => { if (v == null) { pen = false; return; } dpath += (pen ? 'L' : 'M') + x(t[i]).toFixed(1) + ' ' + y(v).toFixed(1); pen = true; });
    s.append(svg('path', {d: dpath, fill: 'none', stroke: l.ref ? 'var(--ref)' : 'var(--series)', 'stroke-width': 2, 'stroke-dasharray': l.ref ? '5 4' : '', 'stroke-linejoin': 'round'})); }
  (o.marks || []).forEach((mk, i) => { if (mk.t < t0 || mk.t > t1) return; const X = x(mk.t);
    s.append(svg('line', {x1: X, x2: X, y1: m.t, y2: H - m.b, stroke: mk.check ? 'var(--mute)' : 'var(--mark)', 'stroke-width': 2, 'stroke-dasharray': mk.check ? '2 3' : ''}));
    const flip = X > W - (narrow ? 150 : 190); s.append(svg('text', {x: X + (flip ? -5 : 5), y: m.t + 10 + i * 13, 'text-anchor': flip ? 'end' : 'start', class: 'lbl'}, mk.label)); });
  const cross = svg('line', {y1: m.t, y2: H - m.b, stroke: 'var(--ink2)', 'stroke-width': 1, visibility: 'hidden'}); s.append(cross);
  const hit = svg('rect', {x: m.l, y: m.t, width: W - m.l - m.r, height: H - m.t - m.b, fill: 'transparent'});
  hit.addEventListener('mousemove', ev => { const r = s.getBoundingClientRect(), px = (ev.clientX - r.left) / r.width * W, tv = t0 + (px - m.l) / (W - m.l - m.r) * (t1 - t0);
    let i = 0, best = Infinity; t.forEach((q, k) => { const dd = Math.abs(q - tv); if (dd < best) { best = dd; i = k; } });
    cross.setAttribute('x1', x(t[i])); cross.setAttribute('x2', x(t[i])); cross.setAttribute('visibility', 'visible');
    showTip(ev, '<b>' + esc(lt(t[i])) + '</b><br>' + lines.map(l => esc(l.name) + ': ' + ((l.raw || l.v)[i] == null ? 'missing' : (l.raw || l.v)[i] + ' ' + (o.short || ''))).join('<br>')); });
  hit.addEventListener('mouseleave', () => { cross.setAttribute('visibility', 'hidden'); hideTip(); });
  s.append(hit);
  const lg = el('div', 'legend');
  for (const l of lines) { const sp = el('span'); sp.append(el('i', l.ref ? 'ref' : ''), document.createTextNode(l.name)); lg.append(sp); }
  if ((o.marks || []).some(mk => !mk.check)) { const sp = el('span'); sp.append(el('i', 'mark'), document.createTextNode('our decision')); lg.append(sp); }
  host.append(lg, s);
}

/* ---------- parts ---------- */
function tags(d) { const w = el('span'); w.append(el('span', 'tag p-' + d.priority, d.priority), el('span', 'tag l-' + level(d), LEVEL[level(d)])); return w; }
function step(d) {
  const s = el('div', 'step'), h = el('div', 'h');
  h.append(el('b', null, d.action.replace(/_/g, ' ')), el('time', null, lt(tsOf(d))), tags(d));
  if (d.resource_id) h.append(el('span', 'tag plain', d.resource_id));
  if (d.confidence != null) h.append(el('span', 'tag plain', 'confidence ' + d.confidence));
  s.append(h, el('p', null, d.reason));
  if (d.proposed_message) { const mm = el('div', 'msg'); mm.append(el('div', 'k', 'Proposed message (' + (d.message_language || '') + '), not sent'), el('div', null, d.proposed_message)); s.append(mm); }
  const add = (k, v) => { if (v) { s.append(el('div', 'k', k)); s.append(el(Array.isArray(v) ? 'pre' : 'div', Array.isArray(v) ? '' : 'v', Array.isArray(v) ? v.join('\n') : v)); } };
  add('Evidence', d.evidence && d.evidence.length ? d.evidence : null);
  add('Expected outcome', d.expected_outcome); add('Verification', d.verification_plan);
  const a = D.actions[d.event_id];
  if (a && !needs(d)) add('Mock executor', a.status.replace(/_/g, ' ') + ' · simulated, no effect was measured');
  if (needs(d)) s.append(controls(d));
  return s;
}
function evidenceCard(e) {
  const c = el('div', 'card'), first = e.start, marks = [{t: first, label: 'decision ' + dhm(first)}];
  if (e.check) marks.push({t: e.check.t, label: 'work order ' + dhm(e.check.t), check: true});
  const S = e.series;
  if (e.kind === 'room_flow') { c.append(el('h2', null, 'Water flow in ' + e.subject), el('p', 'note', 'Litres per 15 minutes from the room meter. A healthy room has long stretches at zero.'));
    const after = S ? S.v.filter((v, i) => v != null && v > 0 && S.t[i] >= first - 5 * 36e5 && S.t[i] <= first) : [];
    const quiet = after.length && after.slice().sort((a, b) => a - b)[Math.floor(after.length / 2)] < 3;
    if (quiet) c.append(el('p', 'note', 'The leak is small (about 1 L per 15 min), so the axis is cut at 6 L: showers go off the top. What matters is that the line never returns to zero.'));
    lineChart(c, {t: S && S.t, lines: [{name: 'flow', v: S && S.v}], unit: 'L per 15 min', short: 'L', zero: true, cap: quiet ? 6 : null, marks, label: 'Water flow'}); }
  else if (e.kind === 'room_meter') { c.append(el('h2', null, 'Meter reading of WM_' + e.subject), el('p', 'note', 'Cumulative litres. A meter can only count up; this one steps backwards, so its consumption is not used.'));
    lineChart(c, {t: S && S.t, lines: [{name: 'meter total', v: S && S.v}], unit: 'litres', short: 'L', marks, label: 'Meter reading'}); }
  else if (e.kind === 'main_gap') { c.append(el('h2', null, 'Night gap: main meter minus all room meters'), el('p', 'note', 'Median of the 15-minute intervals between 01:00 and 05:00, one point per night. Normal is about zero.'));
    lineChart(c, {t: S && S.t, lines: [{name: 'night gap', v: S && S.v}], unit: 'L per 15 min', short: 'L', zero: true, marks, label: 'Night gap'}); }
  else if (e.kind === 'cop') { c.append(el('h2', null, 'Heat pump COP against the outdoor-temperature model'), el('p', 'note', 'Hourly median of heat output divided by electric input. The dashed line is what the outdoor temperature explains.'));
    lineChart(c, {t: S && S.t, lines: [{name: 'measured COP', v: S && S.v}, {name: 'expected from outdoor temperature', v: S && S.ref, ref: true}], unit: 'COP', marks, label: 'COP'}); }
  else if (e.kind === 'ahu') { const dm = e.decisions.map(d => ({t: tsOf(d), label: (d.stage || 'decision') + ' ' + dhm(tsOf(d))})).filter((x, i, a) => a.findIndex(y => y.label === x.label) === i).concat(e.check ? [{t: e.check.t, label: 'work order ' + dhm(e.check.t), check: true}] : []);
    c.append(el('h2', null, 'Filter differential pressure'), el('p', 'note', 'Hourly median. Where the line stops, the sensor sent nothing; a gap is not a recovery. The saw-tooth is the planned reduced operation at night.'));
    lineChart(c, {t: S && S.t, lines: [{name: 'filter pressure', v: S && S.v}], unit: 'Pa', short: 'Pa', marks: dm, label: 'Filter pressure'});
    c.append(el('h2', null, 'Fan power'), el('p', 'note', 'A different sensor, still reporting through the gap. The fan works harder against a loaded filter until it reaches its limit of 5.4 kW.'));
    c.lastChild.previousSibling.style.marginTop = '14px';
    lineChart(c, {t: S && S.t, lines: [{name: 'fan power', v: S && S.fan}], unit: 'kW', short: 'kW', marks: dm, label: 'Fan power'});
    c.append(el('h2', null, 'Airflow'), el('p', 'note', 'Nominal is 4,200 m³/h. Once the fan is at its limit, airflow falls.'));
    c.lastChild.previousSibling.style.marginTop = '14px';
    lineChart(c, {t: S && S.t, lines: [{name: 'airflow', v: S && S.air}], unit: 'm³/h', short: 'm³/h', marks: dm, label: 'Airflow'}); }
  else if (e.kind === 'forecast') { c.append(el('h2', null, 'Outdoor temperature forecast used for the decision'), el('p', 'note', 'Solid: the forecast issued at the decision time. Dashed: what was measured afterwards, shown for checking only.'));
    lineChart(c, {t: S && S.t, lines: [{name: 'forecast', v: S && S.v}, {name: 'measured later', v: S && S.ref, ref: true}], unit: '°C outdoor', short: '°C', marks, label: 'Forecast'}); }
  else if (e.kind === 'room_temp') { c.append(el('h2', null, 'Room ' + e.subject + ': temperature and setpoint'), el('p', 'note', 'Shaded band: comfort range for occupied rooms, 20 to 23 °C. The replay does not react to our action.'));
    lineChart(c, {t: S && S.t, lines: [{name: 'room temperature', v: S && S.v}, {name: 'setpoint', v: S && S.ref, ref: true}], unit: '°C', short: '°C', band: [20, 23], marks, label: 'Room temperature'}); }
  else if (e.kind === 'room_day') { c.append(el('h2', null, 'What happened in ' + e.subject + ' that day'), el('p', 'note', 'Grey: events and guest requests from the dataset. Blue: our decisions.'));
    const items = (e.timeline || []).map(x => ({t: x.t, text: x.type.replace(/_/g, ' ') + (x.who ? ' · ' + x.who : '') + (x.text ? ' · “' + x.text + '”' : '')}))
      .concat(e.decisions.map(d => ({t: tsOf(d), ours: true, text: '→ ' + d.action.replace(/_/g, ' ') + ' (' + LEVEL[level(d)] + ')'}))).sort((a, b) => a.t - b.t || (a.ours ? 1 : -1));
    const ul = el('ul', 'log'); for (const it of items) { const li = el('li'); li.append(el('time', null, dhm(it.t)), el('span', it.ours ? 'ours' : '', it.text)); ul.append(li); }
    c.append(ul); }
  else if (e.kind === 'day_plan') { const dd = e.day || {waits: []}; c.append(el('h2', null, 'The day as it went in the replay'), el('p', 'note', 'From the dataset, for checking only. The replay did not follow our plan.'));
    const tl = el('div', 'tiles'); [[dd.checkouts, 'check-outs'], [dd.checkins, 'check-ins'], [dd.cleanings, 'cleanings finished'], [dd.oncall, 'on-call call-outs'], [dd.waits.length, 'guests who waited']].forEach(([v, k]) => { const t = el('div', 'tile'); t.append(el('b', null, v), el('span', null, k)); tl.append(t); });
    c.append(tl);
    if (dd.waits.length) { const mx = Math.max(...dd.waits.map(w => w.min)), bs = el('div', 'bars'); c.append(el('p', 'note', 'Waiting time per guest, arrival at the door to check-in:'));
      for (const w of dd.waits.sort((a, b) => b.min - a.min)) { const b = el('div', 'bar'), bar = el('div'); bar.style.width = Math.max(2, w.min / mx * 100) + '%'; const holder = el('span'); holder.append(bar);
        b.append(el('span', null, w.room), holder, el('span', null, w.min + ' min')); bs.append(b); } c.append(bs); } }
  return c;
}
function episodeTitle(e) { if (e.kind === 'ahu') return e.issue_type === 'data_quality' ? 'Filter sensor gap, plant healthy' : 'Ventilation filter cascade'; return (KIND[e.kind] || e.issue_type) + (e.subject && e.subject !== 'BUILDING' && e.kind !== 'cop' && e.kind !== 'main_gap' ? ' · ' + e.subject : ''); }
function detail(e) {
  const box = el('div', 'detail');
  if (!e) { box.append(el('div', 'empty', 'Select a case.')); return box; }
  const head = el('div', 'card hero');
  head.append(el('h3', null, episodeTitle(e)), el('div', 'sub', lt(e.start) + (e.end > e.start ? ' to ' + lt(e.end) : '') + ' · ' + e.decisions.length + ' decision(s) · episode ' + e.id));
  const tg = el('div'); tg.append(el('span', 'tag p-' + e.priority, 'risk: ' + e.priority));
  for (const lv of [...new Set(e.decisions.map(level))]) tg.append(el('span', 'tag l-' + lv, LEVEL[lv]));
  head.append(tg);
  if (e.check) { const ck = el('div', 'check'); ck.append(el('b', null, 'Checked against the dataset: '), document.createTextNode('work order ' + e.check.id + ' was written ' + lt(e.check.t) + ', ' + e.check.lead_h + ' h after our decision: “' + e.check.text + '”. The detector does not read work orders.')); head.append(ck); }
  box.append(head, evidenceCard(e));
  const ch = el('div', 'card'); ch.append(el('h2', null, 'Decisions and actions'), el('p', 'note', 'In order. Autonomous actions run in the mock executor; the others wait for a person, or for a person and the guest.'));
  const chain = el('div', 'chain'); const ORDER = ['flag_anomaly', 'schedule_cleaning', 'dispatch_robot', 'adjust_room_setpoint', 'optimize_energy', 'request_inspection', 'dispatch_technician', 'order_service', 'block_room', 'request_human_approval', 'release_room', 'notify_guest'];
  const rank = d => { const i = ORDER.indexOf(d.action); return i < 0 ? 99 : i; };
  for (const d of e.decisions.slice().sort((a, b) => tsOf(a) - tsOf(b) || rank(a) - rank(b))) chain.append(step(d)); ch.append(chain); box.append(ch);
  return box;
}

/* ---------- views ---------- */
function tile(v, k, small, key) { const t = el('div', 'tile' + (key ? ' key' : '')); t.append(el('b', null, v), el('span', null, k)); if (small) t.append(el('small', null, small)); return t; }
function overview(root) {
  const inc = E.filter(e => !e.routine), by = s => inc.filter(e => e.scenario === s).length;
  const checked = E.filter(e => e.check), leads = checked.map(e => e.check.lead_h).sort((a, b) => a - b);
  const tl = el('div', 'tiles');
  tl.append(tile(inc.length, 'cases that needed a decision', E.length - inc.length + ' routine guest answers besides'),
    tile(by('S01'), 'S01 turnaround cases'), tile(by('S02'), 'S02 water cases'), tile(by('S03'), 'S03 heating cases'), tile(by('S04'), 'S04 maintenance cases'),
    tile(all.filter(d => level(d) === 'autonomous').length, 'autonomous decisions'), tile(all.filter(d => level(d) === 'human_approval').length, 'need human approval', pending().length + ' still open'),
    tile(all.filter(d => level(d) === 'approval_and_consent').length, 'need guest consent too'),
    tile(leads.length ? Math.round(leads[Math.floor(leads.length / 2)]) + ' h' : 'n/a', 'median lead over the repair', leads.length ? checked.length + ' cases with a later work order' : 'no work order to compare', true));
  root.append(tl);
  // time strip
  const c = el('div', 'card'); c.append(el('h2', null, 'When the cases happened'), el('p', 'note', 'One dot per case, one lane per scenario. Hover for details, click to open.'));
  const narrow = window.innerWidth < 700, W = narrow ? Math.max(300, window.innerWidth - 66) : 1000, gap = narrow ? 46 : 38, H = narrow ? 236 : 188, m = {l: narrow ? 4 : 110, r: narrow ? 8 : 14, t: 10, b: 24}, lanes = ['S01', 'S02', 'S03', 'S04'];
  const t0 = Math.min(...E.map(e => e.start)), t1 = Math.max(...E.map(e => e.start), t0 + 1);
  const x = v => m.l + (v - t0) / (t1 - t0) * (W - m.l - m.r), s = svg('svg', {viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Cases over time'});
  lanes.forEach((ln, i) => { const y = m.t + (narrow ? 30 : 20) + i * gap; s.append(svg('line', {x1: m.l, x2: W - m.r, y1: y, y2: y, stroke: 'var(--grid)'})); s.append(svg('text', {x: narrow ? m.l : 0, y: narrow ? y - 12 : y + 4, class: 'lbl'}, SC[ln]));
    for (const e of inc.filter(q => q.scenario === ln)) { const cc = svg('circle', {cx: x(e.start), cy: y, r: (e.priority === 'critical' ? 6 : 4.5) + (narrow ? 1 : 0), fill: 'var(--series)', stroke: 'var(--panel)', 'stroke-width': 2, style: 'cursor:pointer'});
      cc.addEventListener('mousemove', ev => showTip(ev, '<b>' + esc(episodeTitle(e)) + '</b><br>' + esc(lt(e.start)) + '<br>risk: ' + e.priority)); cc.addEventListener('mouseleave', hideTip);
      cc.addEventListener('click', () => open(e)); s.append(cc); } });
  const ticks = narrow ? 3 : 6; for (let i = 0; i <= ticks; i++) { const tv = t0 + (t1 - t0) * i / ticks; s.append(svg('text', {x: x(tv), y: H - 6, 'text-anchor': i === 0 ? 'start' : i === ticks ? 'end' : 'middle'}, F_DAY.format(new Date(tv)))); }
  c.append(s); root.append(c);
  // table
  const tb = el('div', 'card'); tb.append(el('h2', null, 'Technical incidents and how early they were seen'), el('p', 'note', 'Lead is the time from our first decision to the corrective work order in the dataset. Work orders are used for this comparison only.'));
  const sc = el('div', 'scroll'), table = el('table'), hr = el('tr'); ['Case', 'First decision (Vienna)', 'Risk', 'Work order written later', 'Lead'].forEach(h => hr.append(el('th', null, h))); table.append(hr);
  for (const e of E.filter(q => ['room_flow', 'main_gap', 'cop'].includes(q.kind) || (q.kind === 'ahu' && q.issue_type !== 'data_quality'))) { const tr = el('tr', 'go'); tr.onclick = () => open(e);
    tr.append(el('td', null, episodeTitle(e)), el('td', 'm', lt(e.start))); const td = el('td'); td.append(el('span', 'tag p-' + e.priority, e.priority)); tr.append(td);
    tr.append(el('td', null, e.check ? e.check.text : 'none within 14 days'), el('td', 'n', e.check ? e.check.lead_h + ' h' : '')); table.append(tr); }
  sc.append(table); tb.append(sc); root.append(tb);
}
function scenario(root, sc) {
  const list = E.filter(e => e.scenario === sc), routine = list.filter(e => e.routine).length;
  const shown = list.filter(e => (showRoutine[sc] || !e.routine) && (!query || JSON.stringify(e.decisions).toLowerCase().includes(query)));
  if (!shown.includes(selected[sc])) selected[sc] = shown.find(e => e.priority === 'critical') || shown[0] || null;
  const split = el('div', 'split'), L = el('div', 'list'), tools = el('div', 'tools');
  tools.append(document.createTextNode(shown.length + ' case(s)'));
  if (routine) { const lb = el('label'); lb.style.marginLeft = '10px'; const cb = el('input'); cb.type = 'checkbox'; cb.checked = !!showRoutine[sc]; cb.onchange = () => { showRoutine[sc] = cb.checked; render(); };
    lb.append(cb, document.createTextNode(' show ' + routine + ' routine guest answers')); tools.append(lb); }
  const q = el('input'); q.type = 'search'; q.placeholder = 'Filter by room, booking or text'; q.value = query; q.onchange = () => { query = q.value.trim().toLowerCase(); render(); }; tools.append(q);
  L.append(tools);
  if (!shown.length) L.append(el('div', 'empty', 'No case matches.'));
  for (const e of shown) { const r = el('div', 'row' + (e === selected[sc] ? ' on' : '')); r.append(el('div', 't', lt(e.start)), el('div', 'a', episodeTitle(e)));
    const tg = el('div'); tg.append(el('span', 'tag p-' + e.priority, e.priority), el('span', 'tag plain', e.decisions.length + ' decision' + (e.decisions.length > 1 ? 's' : ''))); if (e.check) tg.append(el('span', 'tag l-autonomous', e.check.lead_h + ' h early'));
    r.append(tg); r.onclick = () => { selected[sc] = e; render(); }; L.append(r); }
  split.append(L, detail(selected[sc])); root.append(split);
  const on = L.querySelector('.row.on'); if (on) L.scrollTop = Math.max(0, on.offsetTop - 90);
}
function trail(root) {
  const c = el('div', 'card'); c.style.marginTop = '0'; c.append(el('h2', null, 'Every decision, in order'), el('p', 'note', 'The complete log as written to ' + D.source + '. Click a row to open its case.'));
  const sc = el('div', 'scroll'), table = el('table'), hr = el('tr'); ['Time (Vienna)', 'Action', 'Assets', 'Risk', 'Autonomy', 'Reason'].forEach(h => hr.append(el('th', null, h))); table.append(hr);
  const rows = E.flatMap(e => e.decisions.map(d => [d, e])).sort((a, b) => tsOf(a[0]) - tsOf(b[0])), cap = 1500;
  for (const [d, e] of rows.slice(0, cap)) { const tr = el('tr', 'go'); tr.onclick = () => open(e);
    const a = d.affected_assets || []; tr.append(el('td', 'n', dhm(tsOf(d))), el('td', null, d.action.replace(/_/g, ' ')), el('td', null, a.slice(0, 3).join(', ') + (a.length > 3 ? ' +' + (a.length - 3) : '')));
    const p = el('td'); p.append(el('span', 'tag p-' + d.priority, d.priority)); const l = el('td'); l.append(el('span', 'tag l-' + level(d), LEVEL[level(d)]));
    tr.append(p, l, el('td', null, d.reason.length > 170 ? d.reason.slice(0, 170) + '…' : d.reason)); table.append(tr); }
  sc.append(table); c.append(sc); if (rows.length > cap) c.append(el('p', 'note', 'Showing the first ' + cap + ' of ' + rows.length + '.')); root.append(c);
}
function queue(root) {
  const open_ = pending(), done = all.filter(d => approvals[d.event_id] && approvals[d.event_id].state);
  const tl = el('div', 'tiles'); tl.append(tile(open_.length, 'waiting for a person', null, true), tile(open_.filter(d => level(d) === 'approval_and_consent').length, 'of these need guest consent'),
    tile(done.filter(d => approvals[d.event_id].state === 'approved').length, 'approved'), tile(done.filter(d => approvals[d.event_id].state === 'rejected').length, 'rejected')); root.append(tl);
  const c = el('div', 'card'); c.append(el('h2', null, 'Approval queue'), el('p', 'note', 'Everything the building may not do on its own: technician and contractor call-outs, blocking a room, the on-call housekeeper, entering an occupied room. Most urgent first.'));
  const rank = {critical: 0, high: 1, medium: 2, low: 3}, chain = el('div', 'chain');
  for (const d of open_.slice().sort((a, b) => rank[a.priority] - rank[b.priority] || tsOf(a) - tsOf(b))) chain.append(step(d));
  if (!open_.length) chain.append(el('div', 'empty', 'Nothing is waiting.')); c.append(chain); root.append(c);
  const lg = el('div', 'card'); lg.append(el('h2', null, 'Approval log'), el('p', 'note', 'Who decided what in this session. Kept in this browser; export it to keep it.'));
  if (done.length) { const sc = el('div', 'scroll'), table = el('table'), hr = el('tr'); ['Decided (Vienna)', 'Result', 'Action', 'Assets', 'Case'].forEach(h => hr.append(el('th', null, h))); table.append(hr);
    for (const d of done.sort((a, b) => approvals[b.event_id].at.localeCompare(approvals[a.event_id].at))) { const a = approvals[d.event_id], tr = el('tr', 'go'); tr.onclick = () => open(E.find(e => e.id === d.episode_id));
      tr.append(el('td', 'm', lt(Date.parse(a.at)))); const td = el('td'); td.append(el('span', 'tag ' + (a.state === 'approved' ? 'l-autonomous' : 'p-critical'), a.state)); tr.append(td, el('td', null, d.action.replace(/_/g, ' ')), el('td', null, (d.affected_assets || []).slice(0, 4).join(', ')), el('td', 'm', d.episode_id)); table.append(tr); }
    sc.append(table); lg.append(sc);
    const row = el('div', 'act'), ex = el('button', null, 'Export log (JSON)'), cl = el('button', 'no', 'Clear log'); ex.type = cl.type = 'button';
    ex.onclick = () => { const blob = new Blob([JSON.stringify(Object.entries(approvals).filter(([, v]) => v.state).map(([event_id, v]) => Object.assign({event_id}, v)), null, 1)], {type: 'application/json'}), a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'approvals.json'; a.click(); URL.revokeObjectURL(a.href); };
    cl.onclick = () => { approvals = {}; saveApprovals(); render(); }; row.append(ex, cl); lg.append(row); }
  else lg.append(el('div', 'empty', 'No decision taken yet.'));
  root.append(lg);
}
function open(e) { tab = e.scenario in SC ? e.scenario : 'trail'; history.replaceState(null, '', '#' + tab + ':' + encodeURIComponent(e.id)); if (e.routine) showRoutine[e.scenario] = true; selected[e.scenario] = e; query = ''; render(); window.scrollTo(0, 0); }
function render() {
  hideTip();
  const nav = $('nav'); nav.replaceChildren();
  const tabs = [['overview', 'Overview', ''], ...Object.keys(SC).map(k => [k, SC[k], E.filter(e => e.scenario === k && !e.routine).length]), ['queue', 'Approvals', pending().length], ['trail', 'All decisions', all.length]];
  for (const [k, name, n] of tabs) { const b = el('button', k === tab ? 'on' : '', name); if (n !== '') b.append(el('span', null, n)); b.onclick = () => { tab = k; history.replaceState(null, '', '#' + k); render(); }; nav.append(b); }
  const root = $('view'); root.replaceChildren();
  if (tab === 'overview') overview(root); else if (tab === 'trail') trail(root); else if (tab === 'queue') queue(root); else scenario(root, tab);
}
// deep links: #S02 opens a tab, #S02:<episode id> opens a case
(function () { const h = decodeURIComponent(location.hash.slice(1)); if (!h) return; const i = h.indexOf(':'), k = i < 0 ? h : h.slice(0, i);
  if (k === 'overview' || k === 'trail' || k === 'queue' || k in SC) tab = k;
  if (i > 0) { const e = E.find(q => q.id === h.slice(i + 1)); if (e) { if (e.routine) showRoutine[e.scenario] = true; selected[e.scenario] = e; } } })();
const themeBtn = $('theme');
function setTheme(t) { if (t === 'light') document.documentElement.setAttribute('data-theme', 'light'); else document.documentElement.removeAttribute('data-theme');
  themeBtn.textContent = t === 'light' ? 'Dark' : 'Light'; try { localStorage.setItem('theme', t); } catch (err) {} }
themeBtn.onclick = () => setTheme(document.documentElement.getAttribute('data-theme') === 'light' ? 'dark' : 'light');
try { setTheme(localStorage.getItem('theme') || 'dark'); } catch (err) { setTheme('dark'); }
let lastW = window.innerWidth, timer = null;
window.addEventListener('resize', () => { clearTimeout(timer); timer = setTimeout(() => { if (Math.abs(window.innerWidth - lastW) > 40) { lastW = window.innerWidth; render(); } }, 150); });
render();
</script>
</body>
</html>
"""
