"""Independent external irrigation monitoring, never hotel leak detection or control."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
import math

from ..decisions import Decision
from ..telemetry import TelemetryError, fingerprint, timestamp, utc, validate_observation


@dataclass(frozen=True)
class MonitoringPolicy:
    watering_limit_seconds: int = 3600
    battery_low_percent: int = 20
    freshness_seconds: int = 180
    max_gap_seconds: int = 180
    flow_tolerance_l_min: float | None = None
    flow_settle_seconds: int = 30
    flow_persistence_seconds: int = 60
    flow_max_skew_seconds: int = 60

    def __post_init__(self):
        for name in ('watering_limit_seconds', 'freshness_seconds', 'max_gap_seconds', 'flow_persistence_seconds', 'flow_max_skew_seconds'):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise TelemetryError(f'{name} must be a positive monitoring-policy integer')
        if type(self.battery_low_percent) is not int or not 0 <= self.battery_low_percent <= 100:
            raise TelemetryError('battery monitoring threshold must be 0..100')
        if type(self.flow_settle_seconds) is not int or self.flow_settle_seconds < 0:
            raise TelemetryError('settling period must be nonnegative')
        v = self.flow_tolerance_l_min
        if v is not None and (type(v) not in (int, float) or v < 0 or (type(v) is float and not math.isfinite(v))):
            raise TelemetryError('flow tolerance must be finite and nonnegative')


def validate_flow(row):
    """Supplied sensor provenance is a declaration, not authentication or calibration proof."""
    required = {'device_alias', 'timestamp_utc', 'flow_liters_per_minute', 'quality',
                'source', 'source_mode', 'hydraulic_scope_confirmed', 'calibration_reference'}
    if not isinstance(row, dict) or set(row) != required:
        raise TelemetryError('external flow evidence has an invalid schema')
    timestamp(row['timestamp_utc'])
    from ..telemetry import alias, MODES, QUALITIES
    alias(row['device_alias'])
    if not isinstance(row['source'], str) or not row['source'] or row['source'] == 'gardena_ble':
        raise TelemetryError('independent flow source must be identified')
    if not isinstance(row['source_mode'], str) or not isinstance(row['quality'], str):
        raise TelemetryError('flow mode and quality must be strings')
    if row['source_mode'] not in MODES or row['quality'] not in QUALITIES or type(row['hydraulic_scope_confirmed']) is not bool:
        raise TelemetryError('invalid flow qualification')
    v = row['flow_liters_per_minute']
    if v is not None and (type(v) not in (int, float) or v < 0 or (type(v) is float and not math.isfinite(v))):
        raise TelemetryError('invalid flow measurement')
    if row['quality'] == 'VALID' and (v is None or not isinstance(row['calibration_reference'], str) or not row['calibration_reference']):
        raise TelemetryError('qualified measured flow requires a value and calibration reference')
    return row


def analyze(observations, *, policy=None, as_of=None, flow_observations=()):
    policy = policy or MonitoringPolicy()
    unique = {}
    for row in observations:
        validate_observation(row)
        key = (row['device_alias'], row['source_mode'], timestamp(row['observed_at_utc']))
        if key in unique and fingerprint(unique[key]) != fingerprint(row):
            raise TelemetryError('conflicting observation identity')
        unique[key] = row
    rows = sorted(unique.values(), key=lambda r: (timestamp(r['observed_at_utc']), r['device_alias']))
    cutoff = timestamp(as_of) if as_of is not None else max((timestamp(r['observed_at_utc']) for r in rows), default=None)
    flows = sorted((validate_flow(r) for r in flow_observations), key=lambda r: timestamp(r['timestamp_utc']))
    decisions, states = [], {}

    def finding(row, at, issue, reason, episode, evidence, priority='medium'):
        decisions.append(Decision(timestamp_utc=at, affected_assets=[row['device_alias']], issue_type=issue,
            action='flag_anomaly', priority=priority, reason=reason,
            episode_id=f'irrigation:{row["device_alias"]}:{row["source_mode"]}:{issue}:{utc(episode)}',
            evidence=evidence, extra={'source': 'gardena_ble', 'source_mode': row['source_mode'],
            'environment': 'synthetic_fixture' if row['source_mode'] == 'simulated_fixture' else 'external_shadow',
            'shadow_only': True, 'operational_outcome': 'not_measured'}).finalize())

    for row in rows:
        t = timestamp(row['observed_at_utc'])
        if cutoff is not None and t > cutoff:
            continue
        key = row['device_alias'], row['source_mode']
        s = states.setdefault(key, dict(last=None, last_valid=None, opened=None, prolonged=False,
                                       lost=False, low=False, conflict=None, conflict_since=None, conflict_emitted=False))
        ref = f'observation:{row["device_alias"]}:{row["observed_at_utc"]}:sha256:{fingerprint(row)}'
        usable = row['quality'] in ('VALID', 'PARTIAL') and row['connection_state'] == 'connected' and row['valve_state'] != 'unknown'
        if s['last'] is not None and (t - s['last']).total_seconds() > policy.max_gap_seconds:
            s['opened'] = None
            s['prolonged'] = False
            s['conflict'] = None
            s['changed'] = t
            s['conflict_since'] = None
            s['conflict_emitted'] = False
        s['last'] = t
        battery = row['battery_percent']
        if row['connection_state'] == 'connected' and row['quality'] in ('VALID', 'PARTIAL') and battery is not None:
            if battery < policy.battery_low_percent and not s['low']:
                finding(row, t, 'irrigation_battery', f'Reported battery {battery}% is below monitoring-policy threshold {policy.battery_low_percent}%; maintenance review only.', t, [ref], 'low')
            s['low'] = battery < policy.battery_low_percent
        if not usable:
            s['prolonged'] = False
            s['conflict'] = None
            s['opened'] = None
            s['conflict_since'] = None
            if not s['lost']:
                last = s['last_valid']
                note = f'Last usable valve state was {last["valve_state"]} at {last["observed_at_utc"]}.' if last else 'No prior usable valve state.'
                finding(row, t, 'irrigation_telemetry', f'Telemetry is {row["quality"]}; current valve and water flow are unknown. {note}', t, [ref])
            s['lost'] = True
            continue
        previous = s['last_valid']
        s['last_valid'] = row
        if s['lost']:
            s['changed'] = t
        s['lost'] = False
        if row['valve_state'] == 'open':
            s['opened'] = s['opened'] or t
            duration = (t - s['opened']).total_seconds()
            if duration > policy.watering_limit_seconds and not s['prolonged']:
                finding(row, t, 'irrigation_duration', f'Open valve observed over {int(duration)} seconds, exceeding configured monitoring limit {policy.watering_limit_seconds} seconds. This is a monitoring policy, not a manufacturer fault threshold or evidence of water volume/leakage.', s['opened'], [ref])
                s['prolonged'] = True
        else:
            s['opened'] = None
            s['prolonged'] = False
        if previous is None or previous['valve_state'] != row['valve_state']:
            s['changed'] = t
        eligible = [f for f in flows if f['device_alias'] == row['device_alias'] and f['source_mode'] == row['source_mode']
                    and timestamp(f['timestamp_utc']) <= t]
        f = eligible[-1] if eligible else None
        qualified = f is not None and f['quality'] == 'VALID' and f['hydraulic_scope_confirmed'] is True and policy.flow_tolerance_l_min is not None and (t-timestamp(f['timestamp_utc'])).total_seconds() <= policy.flow_max_skew_seconds
        conflict = None
        if qualified and (t-s.get('changed',t)).total_seconds() >= policy.flow_settle_seconds:
            positive = f['flow_liters_per_minute'] > policy.flow_tolerance_l_min
            if row['valve_state'] == 'closed' and positive:
                conflict = 'closed_with_flow'
            elif row['valve_state'] == 'open' and not positive:
                conflict = 'open_without_flow'
        if conflict != s['conflict'] or conflict is None:
            s['conflict_since'] = t if conflict else None
            s['conflict_emitted'] = False
        s['conflict'] = conflict
        if conflict and not s['conflict_emitted'] and (t-s['conflict_since']).total_seconds() >= policy.flow_persistence_seconds:
            explanation = 'Consider drainage, sensor placement, bypass flow or stale valve state; no exact leak location is established.' if conflict == 'closed_with_flow' else 'Possible supply interruption, obstruction, valve or sensor problem; not automatically a leak.'
            finding(row, t, 'irrigation_flow_discrepancy', f'Reported valve state and separately supplied qualified flow disagree ({conflict}); tolerance {policy.flow_tolerance_l_min} L/min. {explanation}', s['conflict_since'], [ref, f'flow:{f["source"]}:{f["timestamp_utc"]}:sha256:{fingerprint(f)}'])
            s['conflict_emitted'] = True
    if cutoff is not None:
        for s in states.values():
            row = s['last_valid']
            if row and not s['lost'] and (cutoff - s['last']).total_seconds() > policy.freshness_seconds:
                finding(row, cutoff, 'irrigation_telemetry', f'No recent observation within {policy.freshness_seconds} seconds. Last usable state {row["valve_state"]} at {row["observed_at_utc"]}; current state and flow remain unknown.', cutoff, [f'observation:sha256:{fingerprint(row)}'])
    return sorted(decisions, key=lambda d: (d['timestamp_utc'], d['event_id']))
