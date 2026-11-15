"""Versioned external observations, isolated from fictional hotel meters."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

QUALITIES = {'VALID', 'PARTIAL', 'STALE', 'DISCONNECTED', 'UNAVAILABLE', 'INVALID'}
MODES = {'physical_device_read', 'simulated_fixture', 'imported_observation'}
FIELDS = ('schema_version', 'source', 'device_alias', 'device_model', 'model_verification',
          'observed_at_utc', 'connection_state', 'quality', 'valve_state', 'active_watering',
          'remaining_open_seconds', 'manual_watering_seconds', 'battery_percent',
          'activation_reason', 'flow_liters_per_minute', 'source_mode', 'unavailable_fields')


class TelemetryError(ValueError):
    """Invalid or unqualified external input; no hardware identifiers in diagnostics."""


def timestamp(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|\+00:00)', value):
        raise TelemetryError('timestamp must be an explicit UTC ISO date-time')
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise TelemetryError('invalid UTC date-time') from exc


def utc(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise TelemetryError('aware host timestamp required')
    return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def alias(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', value):
        raise TelemetryError('use a short non-identifying device alias')
    return value


def validate_observation(row):
    if not isinstance(row, dict) or set(row) != set(FIELDS):
        raise TelemetryError('observation fields do not match schema version 1')
    if row['schema_version'] != 1 or type(row['schema_version']) is not int:
        raise TelemetryError('unsupported observation schema')
    alias(row['device_alias'])
    timestamp(row['observed_at_utc'])
    if not all(isinstance(row[k], str) for k in ('source', 'source_mode', 'quality', 'model_verification', 'connection_state', 'valve_state')):
        raise TelemetryError('enumerated observation fields must be strings')
    if row['source'] != 'gardena_ble' or row['source_mode'] not in MODES or row['quality'] not in QUALITIES:
        raise TelemetryError('unsupported source, mode or quality')
    if row['device_model'] is not None and row['device_model'] != '1889-20':
        raise TelemetryError('unexpected device model')
    if row['model_verification'] not in ('reported', 'owner_declared', 'unknown'):
        raise TelemetryError('invalid model provenance')
    if row['connection_state'] not in ('connected', 'disconnected', 'unavailable') or row['valve_state'] not in ('open', 'closed', 'unknown'):
        raise TelemetryError('invalid connection or valve state')
    if row['active_watering'] is not None and type(row['active_watering']) is not bool:
        raise TelemetryError('active watering must be Boolean or null')
    for field in ('remaining_open_seconds', 'manual_watering_seconds', 'battery_percent'):
        value = row[field]
        if value is not None and (type(value) is not int or value < 0 or (field == 'battery_percent' and value > 100)):
            raise TelemetryError(f'invalid {field}')
    if row['activation_reason'] is not None and (not isinstance(row['activation_reason'], str) or len(row['activation_reason']) > 80):
        raise TelemetryError('invalid activation reason')
    # This source has no independently measured flow. Separate flow evidence only.
    if row['flow_liters_per_minute'] is not None:
        raise TelemetryError('BLE valve observations cannot assert measured flow')
    missing = row['unavailable_fields']
    names = {'valve_state', 'active_watering', 'remaining_open_seconds', 'manual_watering_seconds', 'battery_percent', 'activation_reason'}
    if not isinstance(missing, list) or any(not isinstance(k, str) or k not in names for k in missing):
        raise TelemetryError('invalid missing-field list')
    if row['quality'] == 'VALID' and (missing or row['valve_state'] == 'unknown' or row['connection_state'] != 'connected'):
        raise TelemetryError('VALID requires a connected complete status')
    if row['connection_state'] != 'connected' and (row['valve_state'] != 'unknown' or row['active_watering'] is not None):
        raise TelemetryError('disconnected observations cannot assert current valve state')
    actual_missing = {k for k in names if row[k] is None or (k == 'valve_state' and row[k] == 'unknown')}
    if set(missing) != actual_missing or len(set(missing)) != len(missing):
        raise TelemetryError('missing-field qualification disagrees with values')
    if row['connection_state'] != 'connected' and actual_missing != names:
        raise TelemetryError('disconnected status measurements must be unavailable')
    return row


def observation(*, device_alias, observed_at, source_mode, values=None, connection='connected',
                model=None, model_verification='unknown', quality=None):
    values = values or {}
    state = values.get('valve_state')
    row = dict(schema_version=1, source='gardena_ble', device_alias=alias(device_alias),
               device_model=model, model_verification=model_verification, observed_at_utc=utc(observed_at),
               connection_state=connection, quality=quality, valve_state='unknown', active_watering=None,
               remaining_open_seconds=None, manual_watering_seconds=None, battery_percent=None,
               activation_reason=None, flow_liters_per_minute=None, source_mode=source_mode, unavailable_fields=[])
    names = ('valve_state', 'active_watering', 'remaining_open_seconds', 'manual_watering_seconds', 'battery_percent', 'activation_reason')
    if connection == 'connected':
        for name in names:
            value = values.get(name)
            if name == 'valve_state':
                value = 'open' if value is True else 'closed' if value is False else 'unknown'
            row[name] = value
            if value is None or (name == 'valve_state' and value == 'unknown'):
                row['unavailable_fields'].append(name)
    else:
        row['unavailable_fields'] = list(names)
    row['quality'] = quality or ('DISCONNECTED' if connection == 'disconnected' else
                                'UNAVAILABLE' if connection == 'unavailable' else
                                'PARTIAL' if row['unavailable_fields'] else 'VALID')
    return validate_observation(row)


def canonical(row):
    return json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def fingerprint(row):
    return hashlib.sha256(canonical(row).encode()).hexdigest()


def read_observations(path, *, max_bytes=8*1024*1024):
    p = Path(path)
    if p.stat().st_size > max_bytes:
        raise TelemetryError('observation file exceeds size limit')
    rows, identities = [], {}
    for n, line in enumerate(p.read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = validate_observation(json.loads(line))
        except (ValueError, TypeError, KeyError) as exc:
            raise TelemetryError(f'invalid observation at line {n}') from exc
        key = (row['device_alias'], row['source_mode'], timestamp(row['observed_at_utc']))
        if key in identities:
            if identities[key] != fingerprint(row):
                raise TelemetryError('conflicting observations at the same timestamp')
            continue
        identities[key] = fingerprint(row)
        rows.append(row)
    return sorted(rows, key=lambda r: (timestamp(r['observed_at_utc']), r['device_alias']))


def append_observation(path, row, *, max_records=10000, max_bytes=8*1024*1024):
    """Append only; retention limits refuse further intake, never delete history."""
    validate_observation(row)
    if type(max_records) is not int or max_records < 1:
        raise TelemetryError('positive retention count required')
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lock = p.with_name(p.name + '.lock')
    try:
        handle = lock.open('x')
    except FileExistsError as exc:
        raise TelemetryError('another collector holds the output lock') from exc
    try:
        handle.close()
        existing = read_observations(p, max_bytes=max_bytes) if p.exists() else []
        if existing and timestamp(row['observed_at_utc']) < timestamp(existing[-1]['observed_at_utc']):
            raise TelemetryError('append timestamp precedes existing history')
        for old in existing:
            if (old['device_alias'], timestamp(old['observed_at_utc']), old['source_mode']) == (row['device_alias'], timestamp(row['observed_at_utc']), row['source_mode']):
                if canonical(old) == canonical(row):
                    return False
                raise TelemetryError('conflicting repeated observation')
        line = canonical(row) + '\n'
        if len(existing) >= max_records or (p.stat().st_size if p.exists() else 0) + len(line.encode()) > max_bytes:
            raise TelemetryError('retention limit reached; archive explicitly before resuming')
        with p.open('a', encoding='utf-8') as stream:
            stream.write(line)
        return True
    finally:
        lock.unlink()
