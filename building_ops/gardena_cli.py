"""Standalone bounded collection and offline replay. No persistent live backend."""
import asyncio
import hashlib
import platform
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path

from .adapters.gardena_ble import GardenaBLE
from .detectors.irrigation_monitor import MonitoringPolicy, analyze
from .telemetry import TelemetryError, append_observation, read_observations, timestamp, utc


def add_parser(sub):
    p = sub.add_parser('gardena', help='optional native macOS BLE observation and offline replay')
    commands = p.add_subparsers(dest='gardena_command', required=True)
    scan = commands.add_parser('scan')
    scan.add_argument('--seconds', type=float, default=12)
    scan.add_argument('--authorize-hardware', action='store_true')
    scan.add_argument('--show-device-ids', action='store_true', help='explicitly reveal private local identifiers for selection')
    collect = commands.add_parser('observe')
    collect.add_argument('--device-id', required=True)
    collect.add_argument('--alias', default='gardena')
    collect.add_argument('--authorize-hardware', action='store_true')
    collect.add_argument('--confirm-model', choices=['1889-20'])
    collect.add_argument('--once', action='store_true')
    collect.add_argument('--samples', type=int, default=1)
    collect.add_argument('--interval-seconds', type=float, default=60)
    collect.add_argument('--timeout-seconds', type=float, default=15)
    collect.add_argument('--max-records', type=int, default=10000)
    collect.add_argument('--out', required=True)
    replay = commands.add_parser('replay')
    replay.add_argument('--input', required=True)
    replay.add_argument('--out', required=True)
    replay.add_argument('--as-of')
    replay.add_argument('--watering-limit-seconds', type=int, default=3600)
    replay.add_argument('--battery-low-percent', type=int, default=20)
    replay.add_argument('--freshness-seconds', type=int, default=180)
    replay.add_argument('--flow-input')
    replay.add_argument('--flow-tolerance-l-min', type=float)


async def _hardware(args):
    # Check authorization before imports, scanning, connecting or opening output files.
    if not args.authorize_hardware:
        raise TelemetryError('explicit owner authorization required; no hardware was accessed')
    reader = GardenaBLE(authorized=True, device_alias=getattr(args, 'alias', 'gardena'),
                       timeout_seconds=getattr(args, 'timeout_seconds', 15),
                       confirmed_model=getattr(args, 'confirm_model', None))
    if args.gardena_command == 'scan':
        return await reader.discover_devices(args.seconds, reveal_ids=args.show_device_ids)
    count = 1 if args.once else args.samples
    if not 1 <= count <= 100 or not 0 < args.interval_seconds <= 3600:
        raise TelemetryError('choose 1..100 samples and a positive interval up to one hour')
    appended = 0
    try:
        await reader.connect_readonly(args.device_id)
        for i in range(count):
            row = await reader.read_status()
            appended += append_observation(args.out, row, max_records=args.max_records)
            if row['connection_state'] != 'connected':
                break
            if i + 1 < count:
                await asyncio.sleep(args.interval_seconds)
    finally:
        await reader.disconnect()
    return {'appended': appended, 'source_mode': 'physical_device_read', 'valve_control_calls': 0,
            'outcome': 'not_measured', 'output': args.out}


def run(args):
    if args.gardena_command != 'replay':
        return asyncio.run(_hardware(args))
    rows = read_observations(args.input)
    policy = MonitoringPolicy(watering_limit_seconds=args.watering_limit_seconds,
                              battery_low_percent=args.battery_low_percent,
                              freshness_seconds=args.freshness_seconds,
                              flow_tolerance_l_min=args.flow_tolerance_l_min)
    if args.flow_input:
        if Path(args.flow_input).stat().st_size > 8*1024*1024:
            raise TelemetryError('flow evidence exceeds size limit')
        try:
            flows = [json.loads(line) for line in Path(args.flow_input).read_text().splitlines() if line.strip()]
        except ValueError as exc:
            raise TelemetryError('invalid flow JSONL') from exc
    else:
        flows = []
    decisions = analyze(rows, policy=policy, as_of=args.as_of, flow_observations=flows)
    output = Path(args.out)
    if output.resolve() == Path(args.input).resolve() or (args.flow_input and output.resolve() == Path(args.flow_input).resolve()):
        raise TelemetryError('output must not overwrite input evidence')
    report_path = output.with_suffix('.evidence.json')
    if output.exists() or report_path.exists():
        raise TelemetryError('output exists; choose a new evidence destination')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        stream.write(''.join(json.dumps(d, sort_keys=True, allow_nan=False) + '\n' for d in decisions))
    cutoff = args.as_of or (rows[-1]['observed_at_utc'] if rows else None)
    project_root = Path(__file__).resolve().parent.parent
    dirty = None
    try:
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=project_root, stderr=subprocess.DEVNULL, text=True).strip()
        dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=project_root, stderr=subprocess.DEVNULL))
    except (OSError, subprocess.SubprocessError):
        revision = None
    implementation = {str(p.relative_to(project_root)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in [Path(__file__), project_root/'building_ops/telemetry.py',
                                project_root/'building_ops/adapters/gardena_ble.py',
                                project_root/'building_ops/detectors/irrigation_monitor.py']}
    report = {'schema_version': 1, 'code_revision': revision, 'dirty': dirty,
              'implementation_sha256': implementation, 'python': platform.python_version(),
              'input_sha256': hashlib.sha256(Path(args.input).read_bytes()).hexdigest(),
              'decisions_sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'observation_count': len(rows), 'decision_count': len(decisions),
              'source_modes': sorted({r['source_mode'] for r in rows}), 'as_of_utc': cutoff,
              'monitoring_policy': asdict(policy), 'hotel_data_combined': False,
              'physical_hardware_test': 'not_performed_by_replay', 'actual_flow_measurement': 'not_measured' if not flows else 'separately_supplied_assertions',
              'real_valve_actuation': 'excluded', 'operational_outcome': 'not_measured'}
    with report_path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(report, indent=2, sort_keys=True))
    return report
