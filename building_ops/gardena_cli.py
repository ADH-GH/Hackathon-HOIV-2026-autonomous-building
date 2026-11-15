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
    ask = commands.add_parser('ask')
    ask.add_argument('--evidence',required=True)
    ask.add_argument('--question',required=True)
    commands.add_parser('doctor')
    demo = commands.add_parser('demo')
    demo.add_argument('--out', default='out/gardena-demo')
    report = commands.add_parser('report')
    report.add_argument('--evidence',required=True)
    report.add_argument('--out',required=True)
    report.add_argument('--voice-agent',help='optional opt-in ElevenLabs public agent ID; no automatic network or microphone')
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
    replay.add_argument('--flow-map',help='JSON object mapping controller aliases to independently confirmed hydraulic zone aliases')
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
    if args.gardena_command=='ask':
        from .external_dashboard import payload
        from .gardena_interaction import ask
        return ask(payload(evidence=args.evidence),args.question)
    if args.gardena_command in ('doctor','demo','report'):
        from .gardena_experience import doctor,demo,render
        if args.gardena_command=='doctor':return doctor()
        if args.gardena_command=='demo':return demo(args.out)
        return render(args.evidence,args.out,voice_agent=args.voice_agent)
    if args.gardena_command != 'replay':
        return asyncio.run(_hardware(args))
    from .gardena_assessment import replay
    relationships=None
    if args.flow_map:
        if Path(args.flow_map).stat().st_size>65536:raise TelemetryError('flow mapping exceeds size limit')
        try:relationships=json.loads(Path(args.flow_map).read_text())
        except ValueError as exc:raise TelemetryError('invalid flow mapping JSON') from exc
    return replay(args.input,args.out,policy=MonitoringPolicy(
        watering_limit_seconds=args.watering_limit_seconds,battery_low_percent=args.battery_low_percent,
        freshness_seconds=args.freshness_seconds,flow_tolerance_l_min=args.flow_tolerance_l_min,flow_relationships=relationships),
        as_of=args.as_of,flow_input=args.flow_input)
