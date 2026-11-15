"""Offline onboarding and static reports from the canonical assessment only."""
import html
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import platform
from datetime import datetime,timezone

from .external_dashboard import payload
from .gardena_assessment import load,replay
from .detectors.irrigation_monitor import MonitoringPolicy
from .telemetry import TelemetryError,utc


def doctor():
    packages={}
    for name in ('bleak','gardena-bluetooth'):
        try:packages[name]=version(name)
        except PackageNotFoundError:packages[name]=None
    return dict(platform=platform.system(),python=platform.python_version(),ordinary_python_compatible=tuple(map(int,platform.python_version_tuple()[:2]))>=(3,11),
                native_corebluetooth_candidate=platform.system()=='Darwin',optional_dependencies=packages,
                required_native_profile='Python 3.12+; requirements/gardena-macos-py312.txt on supported macOS',
                bluetooth_permission='not_verified',hardware_authorization='not_granted_by_this_command',device_connection='not_attempted',
                physical_device_test='NOT_TESTED',actuator_control_enabled=False,offline_capable=True,
                next_step='Run gardena demo; scanning requires explicit owner authorization. On macOS allow your Terminal/Python Bluetooth permission. Never reset pairing to bypass a conflict.')


def escape(value):return html.escape('unavailable' if value is None else str(value),quote=True)


def render(evidence,out,*,generated_at=None,voice_agent=None):
    result=load(evidence);view=payload(evidence=evidence)
    output=Path(out)
    if output.exists() or output.resolve()==Path(evidence).resolve():raise TelemetryError('report output exists; choose a new destination')
    generated_at=generated_at or utc(datetime.now(timezone.utc))
    from .telemetry import timestamp
    timestamp(generated_at)
    cards=[]
    for d in view['devices']:
        state='DISCONNECTED' if d['connection_state']=='disconnected' else 'STALE' if d['quality']=='STALE' else d['current_valve_state'].upper()
        values=[('State at assessment',state),('Model / identity basis',f"{d['device_model'] or 'unknown'} / {d['model_verification']}"),
                ('Last observation UTC',d['observed_at_utc']),('Evidence mode',d['source_mode']),('Telemetry quality',d['quality']),
                ('Reported watering at observation',d['active_watering']),('Remaining seconds reported',d['remaining_open_seconds']),
                ('Battery % at observation',d['battery_percent']),('Last usable valve / UTC',f"{d['last_usable_valve_state']} / {d['last_usable_valve_timestamp']}"),
                ('Measured BLE flow','unavailable — independent sensor required')]
        cards.append('<article><h3>'+escape(d['device_alias'])+'</h3><dl>'+''.join('<dt>'+escape(k)+'</dt><dd>'+escape(v)+'</dd>' for k,v in values)+'</dl></article>')
    timeline=[]
    for ref in result['observation_evidence']:
        r=ref['record']
        if result['as_of_utc'] and timestamp(r['observed_at_utc'])>timestamp(result['as_of_utc']):continue
        timeline.append('<tr><td>'+escape(r['observed_at_utc'])+'</td><td>'+escape(r['device_alias'])+'</td><td>'+escape(r['connection_state'])+'</td><td>'+escape(r['valve_state'])+'</td><td>'+escape(r['quality'])+'</td><td><a href="#obs-'+ref['sha256']+'">record</a></td></tr>')
    findings=[]
    for d in result['decisions']:
        findings.append('<article><h3>'+escape(d['issue_type'].replace('_',' '))+'</h3><p>'+escape(d['reason'])+'</p><p>'+escape(d['timestamp_utc'])+' · '+escape(', '.join(d['affected_assets']))+'</p><p>Human follow-up: inspect the device, reporting coverage and relevant sensor placement. No automatic operation.</p><p>Verification: NOT_TESTED; operational outcome not measured.</p><details><summary>Evidence references</summary><pre>'+escape(json.dumps(d['evidence'],indent=2))+'</pre></details></article>')
    records=''.join('<details id="obs-'+r['sha256']+'"><summary>'+escape(r['record']['device_alias']+' · '+r['record']['observed_at_utc'])+' · '+r['sha256'][:12]+'</summary><pre>'+escape(json.dumps(r['record'],indent=2))+'</pre></details>' for r in result['observation_evidence'])
    warnings=''.join('<li>'+escape(w)+'</li>' for w in result['qualification_warnings'])
    metadata={k:v for k,v in result.items() if k not in ('observations','decisions','flow_observations','observation_evidence')}
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PLATO-40 · GARDENA evidence</title><style>
:root{color-scheme:light dark;--bg:#f1f4f2;--ink:#18251e;--card:#fff;--line:#bbc9c0;--muted:#41564a;--accent:#19563d}
@media(prefers-color-scheme:dark){:root{--bg:#101b17;--ink:#edf2ed;--card:#192820;--line:#53675b;--muted:#b7c8bc;--accent:#a4dcc0}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,sans-serif}header,main,footer{max-width:1180px;margin:auto;padding:24px}header{border-bottom:1px solid var(--line)}h1{font-size:clamp(28px,5vw,46px);margin:8px 0}h2{margin-top:32px}h3{margin-top:0}p{max-width:85ch}a{color:var(--accent)}.eyebrow,dt{color:var(--muted)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(275px,1fr));gap:16px}article,details,.panel{background:var(--card);padding:18px;border:1px solid var(--line);border-radius:12px;margin-bottom:12px}dl{margin:0}dd{margin:0 0 10px;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%}td,th{padding:10px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}button,select{font:inherit;padding:10px;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:6px;max-width:100%}button{cursor:pointer}nav{display:flex;gap:16px;flex-wrap:wrap}footer{color:var(--muted)}
</style><header><div class="eyebrow">PLATO-40 / EXTERNAL OBSERVATIONS</div><h1>GARDENA water-management evidence</h1><p>From observation to explainable decisions. Static, read-only and separate from the fictional hotel metrics.</p><nav><a href="#status">Device status</a><a href="#activity">Activity</a><a href="#findings">Findings</a><a href="#questions">Ask</a><a href="#evidence">Evidence</a></nav></header><main>'''
    page+='<p>Report generated UTC: '+escape(generated_at)+'. Assessment cutoff UTC: '+escape(result['as_of_utc'])+'.</p><p>Evidence: '+escape(result['evidence_classification'])+'. Hardware qualification: NOT_TESTED. No live updates or valve control.</p><ul>'+warnings+'</ul>'
    page+='<section id="status"><h2>Device status</h2><div class="grid">'+''.join(cards)+'</div></section>'
    page+='<section id="activity"><h2>Observed activity timeline</h2><p>Rows are observations, not interpolated physical states. A disconnected or missing interval establishes neither continued watering nor closure. Reconnection starts a new observation interval. Duration findings compare qualifying observations with the recorded policy; no manufacturer schedule is assumed.</p><div class="scroll"><table><thead><tr><th>UTC</th><th>Alias</th><th>Connection</th><th>Reported valve</th><th>Quality</th><th>Evidence</th></tr></thead><tbody>'+''.join(timeline)+'</tbody></table></div></section>'
    page+='<section id="findings"><h2>Monitoring findings · '+str(len(findings))+'</h2>'+(''.join(findings) or '<p>No finding under this policy; flow and equipment health are not thereby verified.</p>')+'</section>'
    from .gardena_interaction import section
    page+=section(view,voice_agent=voice_agent)
    page+='<section id="evidence"><h2>Evidence and policy</h2><p>Export the adjacent decisions and evidence JSON files for replay. This HTML embeds the same validated assessment, not a second monitoring policy. Record hashes are integrity references, not authenticated physical proof.</p><details><summary>Exact policy, hashes and qualification</summary><pre>'+escape(json.dumps(metadata,sort_keys=True,indent=2))+'</pre></details><details><summary>Separate flow assertions</summary><pre>'+escape(json.dumps(result['flow_observations'],indent=2))+'</pre></details>'+records+'</section></main><footer>Read-only shadow monitoring · Water consumption and real-world incident resolution not measured.</footer></html>'
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as stream:stream.write(page)
    return {'report':str(output),'generated_at_utc':generated_at,'assessment_sha256':__import__('hashlib').sha256(Path(evidence).read_bytes()).hexdigest()}


def demo(out):
    import shutil
    root=Path(out)
    if root.exists():raise TelemetryError('demo destination exists; choose a new directory')
    root.mkdir(parents=True)
    fixtures=Path(__file__).parent/'data/gardena'
    for name in ('demo.jsonl','flow.jsonl'):shutil.copyfile(fixtures/name,root/name)
    report=replay(root/'demo.jsonl',root/'decisions.jsonl',policy=MonitoringPolicy(watering_limit_seconds=60,flow_tolerance_l_min=.1,flow_relationships={'Flow_discrepancy':'fixture_zone','Flow_unqualified':'fixture_zone'}),
                  as_of='2026-11-15T12:02:00Z',flow_input=root/'flow.jsonl')
    result=render(root/'decisions.evidence.json',root/'experience.html')
    result.update(finding_count=report['decision_count'],evidence=str(root/'decisions.evidence.json'),source_mode='simulated_fixture',hardware_test='NOT_TESTED')
    return result
