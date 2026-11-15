"""Curated static external view; never counted in synthetic hotel metrics."""
from dataclasses import asdict
from datetime import datetime, timezone

from .detectors.irrigation_monitor import MonitoringPolicy, analyze
from .telemetry import read_observations, timestamp, utc


def payload(path, *, as_of=None, freshness_seconds=180):
    rows = read_observations(path)
    cutoff = timestamp(as_of) if as_of else datetime.now(timezone.utc)
    policy = MonitoringPolicy(freshness_seconds=freshness_seconds)
    findings = analyze(rows, policy=policy, as_of=utc(cutoff))
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
    return {'as_of_utc': utc(cutoff), 'static_report': True, 'devices': list(devices.values()),
            'findings': findings, 'policy': asdict(policy), 'operational_outcome': 'not_measured',
            'flow_measurement': 'unavailable_without_independent_sensor'}
