"""Native macOS BLE reads; all optional dependencies are imported after authorization."""
from __future__ import annotations

import asyncio
import hashlib
import importlib.metadata
import platform
import sys
from datetime import datetime, timezone

from ..telemetry import TelemetryError, alias, observation

SCAN_SERVICE = '98bd0001-0b0e-421a-84e5-ddbf75dc6de4'
SUPPORTED = ('valve_state', 'active_watering', 'remaining_open_seconds',
             'manual_watering_seconds', 'battery_percent', 'activation_reason')


def bounded(value, name, maximum=60):
    if type(value) not in (float, int) or not 0 < value <= maximum:
        raise TelemetryError(f'{name} must be positive and at most {maximum} seconds')
    return value


class NativeBackend:
    """Uses pinned upstream decoders, never its segmented read/write client."""
    physical = True

    def __init__(self):
        if sys.version_info < (3, 12) or platform.system() != 'Darwin':
            raise TelemetryError('native adapter requires macOS and isolated Python 3.12+')
        try:
            for package, version in (('gardena-bluetooth', '3.1.0'), ('bleak', '3.1.0')):
                if importlib.metadata.version(package) != version:
                    raise TelemetryError('optional BLE package version does not match pinned profile')
            from bleak import BleakClient, BleakScanner
            from gardena_bluetooth.const import Valve, Battery, DeviceInformation
            from gardena_bluetooth.parse import ManufacturerData, ProductType
        except ImportError as exc:
            raise TelemetryError('install the pinned optional BLE environment first') from exc
        self.scanner = BleakScanner
        self.manufacturer = ManufacturerData
        self.product_type = ProductType
        self.info = DeviceInformation
        self.specs = dict(valve_state=Valve.state, active_watering=Valve.active_state,
                          remaining_open_seconds=Valve.remaining_open_time,
                          manual_watering_seconds=Valve.manual_watering_time,
                          battery_percent=Battery.battery_level, activation_reason=Valve.activation_reason,
                          model_number=DeviceInformation.model_number)
        class ReadOnlyClient(BleakClient):
            async def write_gatt_char(self, *args, **kwargs):
                raise TelemetryError('GATT writes are prohibited')
            async def write_gatt_descriptor(self, *args, **kwargs):
                raise TelemetryError('GATT writes are prohibited')
            async def start_notify(self, *args, **kwargs):
                raise TelemetryError('notification subscription writes are prohibited')
            async def pair(self, *args, **kwargs):
                raise TelemetryError('explicit pairing is prohibited')
            async def unpair(self, *args, **kwargs):
                raise TelemetryError('unpairing is prohibited')
        self.client_class = ReadOnlyClient
        self.client = None

    async def discover(self, seconds):
        # Supplying service UUIDs also covers macOS 12.0–12.2 filtering.
        accumulated = {}
        def receive(device, adv):
            if SCAN_SERVICE not in [x.lower() for x in adv.service_uuids] and self.manufacturer.company not in adv.manufacturer_data:
                return
            item = accumulated.setdefault(device.address, {'device': device, 'data': self.manufacturer()})
            try:
                item['data'].update(adv.manufacturer_data.get(self.manufacturer.company, b''))
            except (ValueError, IndexError, TypeError):
                return
            item['device'] = device
        async with self.scanner(detection_callback=receive, service_uuids=[SCAN_SERVICE]):
            await asyncio.sleep(seconds)
        return [{'id': key, 'device': item['device'], 'product_type': 'water_computer'}
                for key, item in accumulated.items() if item['data'].product_type == self.product_type.WATER_COMPUTER]

    async def connect(self, candidate, seconds):
        self.client = self.client_class(candidate['device'], timeout=seconds, pair=False)
        await self.client.connect()

    async def read(self, name):
        if name not in self.specs:
            raise TelemetryError('read outside status whitelist')
        spec = self.specs[name]
        # Service-scoped lookup avoids ambiguous characteristics across device families.
        service = self.client.services.get_service(spec.service_uuid)
        char = service.get_characteristic(spec.uuid) if service else None
        if char is None or 'read' not in char.properties:
            return None
        data = await self.client.read_gatt_char(char)
        if not data:
            return None
        value = spec.decode(data)
        if name == 'model_number':
            value = value.strip(' \x00')
        return value.name.lower() if name == 'activation_reason' and hasattr(value, 'name') else value

    async def disconnect(self):
        if self.client is not None:
            try:
                await self.client.disconnect()
            finally:
                self.client = None


class GardenaBLE:
    def __init__(self, *, authorized=False, device_alias='gardena', backend=None,
                 timeout_seconds=15, confirmed_model=None, clock=None):
        self.authorized = authorized
        self.device_alias = alias(device_alias)
        self.backend = backend
        self.timeout = bounded(timeout_seconds, 'timeout')
        if confirmed_model not in (None, '1889-20'):
            raise TelemetryError('unsupported owner-confirmed model')
        self.confirmed_model = confirmed_model
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.candidates = {}
        self.connected = False
        self.model = None
        self.verification = 'unknown'

    def _backend(self):
        if not self.authorized:
            raise TelemetryError('explicit owner authorization required before any Bluetooth access')
        if self.backend is None:
            self.backend = NativeBackend()
        return self.backend

    async def discover_devices(self, timeout_seconds=12, *, reveal_ids=False):
        backend = self._backend()
        seconds = bounded(timeout_seconds, 'scan duration')
        try:
            rows = await asyncio.wait_for(backend.discover(seconds), seconds + 2)
        except Exception as exc:
            raise TelemetryError('Bluetooth discovery failed: timeout, permission denial or unavailable adapter; no reset attempted') from exc
        self.candidates = {r['id']: r for r in rows if r.get('product_type') == 'water_computer'}
        return [{'device_handle': hashlib.sha256(key.encode()).hexdigest()[:12],
                 **({'device_id': key} if reveal_ids else {}),
                 'product_type': 'water_computer', 'exact_model_verified': False}
                for key in sorted(self.candidates)]

    async def connect_readonly(self, device_id):
        backend = self._backend()
        if not self.candidates:
            await self.discover_devices(min(12, self.timeout))
        if device_id not in self.candidates:
            raise TelemetryError('selected device was not a supported discovery candidate')
        try:
            await asyncio.wait_for(backend.connect(self.candidates[device_id], self.timeout), self.timeout)
            try:
                raw = await asyncio.wait_for(backend.read('model_number'), self.timeout)
            except NotImplementedError:
                raw = None
            if raw in ('1889-20', '01889-20'):
                self.model, self.verification = '1889-20', 'reported'
            elif self.confirmed_model == '1889-20' and raw in (None, '', 'unknown'):
                self.model, self.verification = '1889-20', 'owner_declared'
            else:
                raise TelemetryError('exact model not established; stop for owner identification, not reset or reconfiguration')
            self.connected = True
        except Exception as exc:
            await self.disconnect()
            if isinstance(exc, TelemetryError):
                raise
            raise TelemetryError('read-only connection failed; check Bluetooth permission, pairing ownership and availability') from exc

    async def read_status(self):
        backend = self._backend()
        mode = 'physical_device_read' if getattr(backend, 'physical', False) else 'simulated_fixture'
        values = {}
        connection = 'connected' if self.connected else 'disconnected'
        if self.connected:
            try:
                for name in SUPPORTED:
                    try:
                        values[name] = await asyncio.wait_for(backend.read(name), self.timeout)
                    except NotImplementedError:
                        values[name] = None
            except Exception:
                # Keep last successful observations in the file; do not assert stale values now.
                connection = 'disconnected'
                await self.disconnect()
                values = {}
        try:
            return observation(device_alias=self.device_alias, observed_at=self.clock(), source_mode=mode,
                               connection=connection, values=values, model=self.model, model_verification=self.verification)
        except TelemetryError:
            return observation(device_alias=self.device_alias, observed_at=self.clock(), source_mode=mode,
                               connection=connection, model=self.model, model_verification=self.verification, quality='INVALID')

    async def disconnect(self):
        self.connected = False
        if self.backend is not None:
            try:
                await asyncio.wait_for(self.backend.disconnect(), self.timeout)
            except Exception as exc:
                raise TelemetryError('Bluetooth cleanup failed; stop rather than reconnect automatically') from exc
