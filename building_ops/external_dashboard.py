"""Curated static external view; never counted in synthetic hotel metrics."""
from dataclasses import asdict
from datetime import datetime, timezone

from .detectors.irrigation_monitor import MonitoringPolicy, analyze
from .telemetry import read_observations, timestamp, utc


def payload(path=None, *, evidence=None, as_of=None, freshness_seconds=180):
    from .gardena_assessment import load, assess
    if evidence:
        result=load(evidence,observations_path=path)
        if as_of is not None and as_of!=result['as_of_utc']:
            from .telemetry import TelemetryError
            raise TelemetryError('dashboard cutoff contradicts canonical assessment')
    else:
        rows=read_observations(path)
        result=assess(rows,policy=MonitoringPolicy(freshness_seconds=freshness_seconds),as_of=as_of)
    rows=result['observations']
    cutoff=timestamp(result['as_of_utc']) if result['as_of_utc'] else datetime.min.replace(tzinfo=timezone.utc)
    policy=MonitoringPolicy(**result['monitoring_policy'])
    findings=result['decisions']
    freshness_seconds=policy.freshness_seconds
    devices = {}
    for row in rows:
        if timestamp(row['observed_at_utc']) > cutoff:
            continue
        key = row['device_alias'], row['source_mode']
        d = devices.setdefault(key, {'last_usable_valve_state': None, 'last_usable_valve_timestamp': None})
        # Copy only the validated public observation schema, never transport/device IDs.
        d.update(row)
        if row['quality'] in ('VALID', 'PARTIAL') and row['connection_state'] == 'connected' and row['valve_state'] != 'unknown':
            d['last_usable_valve_state'] = row['valve_state']
            d['last_usable_valve_timestamp'] = row['observed_at_utc']
    for d in devices.values():
        if (cutoff - timestamp(d['observed_at_utc'])).total_seconds() > freshness_seconds:
            d['quality'] = 'STALE'
        d['current_valve_state'] = d['valve_state'] if d['quality'] in ('VALID','PARTIAL') and d['connection_state']=='connected' else 'unknown'
    view = {'as_of_utc': result['as_of_utc'], 'static_report': True, 'devices': list(devices.values()),
            'findings': findings, 'policy': asdict(policy), 'operational_outcome': 'not_measured',
            'flow_measurement': result['actual_flow_measurement'], 'assessment': result, 'qualification_warnings': result['qualification_warnings'] + ([] if evidence else ['Observation-only view is a separate default-policy assessment, not a replay export.'])}

    from .gardena_interaction import answers
    view["readonly_answers"] = answers(view)
    return view
