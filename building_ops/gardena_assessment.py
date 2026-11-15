"""Canonical, self-contained shadow assessment. Integrity checks are not signatures."""
from dataclasses import asdict, fields
import hashlib
import json
from pathlib import Path
import subprocess

from .telemetry import TelemetryError, canonical, fingerprint, read_observations, timestamp, utc, validate_observation
from .detectors.irrigation_monitor import MonitoringPolicy, analyze, validate_flow
from .decisions import validate_decision


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def decision_bytes(decisions):
    return ''.join(json.dumps(d, sort_keys=True, allow_nan=False)+'\n' for d in decisions).encode()


def revision():
    try:
        return subprocess.check_output(['git','rev-parse','HEAD'],cwd=Path(__file__).resolve().parent.parent,
                                       stderr=subprocess.DEVNULL,text=True).strip()
    except (OSError,subprocess.SubprocessError):return None


def assess(rows, *, policy=None, as_of=None, flows=(), input_sha256=None, flow_input_sha256=None, code_revision=None):
    policy=policy or MonitoringPolicy()
    # Identity validation and order normalization also applies to in-memory callers.
    unique={}
    for row in rows:
        validate_observation(row)
        key=(row['device_alias'],row['source_mode'],timestamp(row['observed_at_utc']))
        if key in unique and fingerprint(unique[key])!=fingerprint(row):raise TelemetryError('conflicting observation identity')
        unique[key]=row
    rows=sorted(unique.values(),key=lambda r:(timestamp(r['observed_at_utc']),r['device_alias'],r['source_mode']))
    flows=sorted((validate_flow(f) for f in flows),key=lambda f:(timestamp(f['timestamp_utc']),f['device_alias'],f['source']))
    cutoff=utc(timestamp(as_of)) if as_of else (rows[-1]['observed_at_utc'] if rows else None)
    decisions=analyze(rows,policy=policy,as_of=cutoff,flow_observations=flows)
    for decision in decisions:validate_decision(decision,require_risk_context=True)
    warnings=[]
    if not rows:warnings.append('No observations supplied.')
    if any(r['quality']!='VALID' for r in rows):warnings.append('Some observations are incomplete or unusable; unknown is not zero.')
    if cutoff and any(timestamp(r['observed_at_utc'])>timestamp(cutoff) for r in rows):warnings.append('Future observations excluded from assessment.')
    warnings.append('Provenance declarations are not authenticated physical verification; no operational outcome measured.')
    modes=sorted({r['source_mode'] for r in rows})
    return dict(schema_version=2,source='gardena_ble',environment='synthetic_fixture' if modes==['simulated_fixture'] else 'external_shadow',
                code_revision=code_revision if code_revision is not None else revision(),
                input_sha256=input_sha256,flow_input_sha256=flow_input_sha256,
                observations_sha256=fingerprint(rows),flow_observations_sha256=fingerprint(flows),
                decisions_sha256=digest(decision_bytes(decisions)),observation_count=len(rows),decision_count=len(decisions),
                source_modes=modes,as_of_utc=cutoff,monitoring_policy=asdict(policy),observations=rows,flow_observations=flows,
                decisions=decisions,observation_evidence=[{'sha256':fingerprint(r),'record':r} for r in rows],
                qualification_warnings=warnings,evidence_classification='synthetic_replay' if modes==['simulated_fixture'] else 'unverified_source_declarations',
                verification_status='NOT_TESTED',hardware_connection_verified=False,flow_measurement_verified=False,
                actuator_control_enabled=False,hotel_data_combined=False,physical_hardware_test='not_performed_by_replay',
                actual_flow_measurement='separately_supplied_assertions' if flows else 'not_measured',
                real_valve_actuation='excluded',operational_outcome='not_measured')


def load(path, *, observations_path=None):
    p=Path(path)
    if p.stat().st_size>32*1024*1024:raise TelemetryError('assessment exceeds size bound')
    try:
        report=json.loads(p.read_text())
        if not isinstance(report,dict) or report.get('schema_version')!=2:raise TelemetryError('canonical schema version 2 required; replay legacy evidence again')
        policy=report['monitoring_policy']
        if not isinstance(policy,dict) or set(policy)!={f.name for f in fields(MonitoringPolicy)}:raise TelemetryError('complete canonical monitoring policy required')
        expected=assess(report['observations'],policy=MonitoringPolicy(**policy),as_of=report['as_of_utc'],flows=report['flow_observations'],
                        input_sha256=report['input_sha256'],flow_input_sha256=report['flow_input_sha256'],code_revision=report['code_revision'])
        if canonical(expected)!=canonical(report):raise TelemetryError('assessment policy, inputs, hashes or findings disagree; replay original inputs')
        if observations_path is not None and digest(Path(observations_path).read_bytes())!=report['input_sha256']:
            raise TelemetryError('observation file does not match assessment input hash')
        return report
    except (KeyError,TypeError,ValueError,RecursionError) as exc:
        raise TelemetryError('invalid or inconsistent canonical assessment: '+str(exc)) from exc


def replay(input_path, output_path, *, policy, as_of=None, flow_input=None):
    output=Path(output_path);manifest=output.with_suffix('.evidence.json')
    if output.exists() or manifest.exists():raise TelemetryError('output exists; choose a new evidence destination')
    if output.resolve()==manifest.resolve():raise TelemetryError('decisions and manifest need distinct paths')
    raw=Path(input_path).read_bytes()
    flows=[];flow_hash=None
    if flow_input:
        p=Path(flow_input)
        if p.stat().st_size>8*1024*1024:raise TelemetryError('flow evidence exceeds size bound')
        try:flows=[json.loads(s) for s in p.read_text().splitlines() if s.strip()]
        except ValueError as exc:raise TelemetryError('invalid flow JSONL') from exc
        flow_hash=digest(p.read_bytes())
    if output.resolve() in {Path(input_path).resolve(),Path(flow_input).resolve() if flow_input else None} or manifest.resolve() in {Path(input_path).resolve(),Path(flow_input).resolve() if flow_input else None}:
        raise TelemetryError('outputs must not overwrite source evidence')
    report=assess(read_observations(input_path),policy=policy,as_of=as_of,flows=flows,input_sha256=digest(raw),flow_input_sha256=flow_hash)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('xb') as stream:stream.write(decision_bytes(report['decisions']))
    with manifest.open('x',encoding='utf-8') as stream:stream.write(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+'\n')
    return report
