import asyncio
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone

from building_ops.adapters.gardena_ble import GardenaBLE
from building_ops.telemetry import TelemetryError, append_observation, observation, read_observations, validate_observation

T = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)
DEVICE = 'private-device-uuid'
VALUES = dict(model_number='1889-20', valve_state=False, active_watering=False,
              remaining_open_seconds=0, manual_watering_seconds=300, battery_percent=82, activation_reason='manual')


class FakeBackend:
    physical = False
    def __init__(self, values=None):
        self.values = dict(VALUES if values is None else values)
        self.connections = []; self.reads = []; self.disconnects = 0; self.writes = 0
    async def discover(self, seconds):
        return [{'id': DEVICE, 'product_type': 'water_computer'}, {'id': 'other', 'product_type': 'mower'}]
    async def connect(self, candidate, seconds): self.connections.append(candidate['id'])
    async def read(self, name):
        self.reads.append(name)
        value = self.values.get(name)
        if isinstance(value, Exception): raise value
        return value
    async def disconnect(self): self.disconnects += 1
    async def write_gatt_char(self, *args):
        self.writes += 1
        raise AssertionError('no writes allowed')


class BLETest(unittest.IsolatedAsyncioTestCase):
    async def test_authorization_selection_redaction_and_read(self):
        fake = FakeBackend()
        denied = GardenaBLE(backend=fake)
        with self.assertRaises(TelemetryError): await denied.discover_devices()
        self.assertEqual(fake.reads, [])
        reader = GardenaBLE(authorized=True, backend=fake, clock=lambda:T)
        candidates = await reader.discover_devices()
        self.assertEqual(len(candidates), 1)
        self.assertNotIn(DEVICE, json.dumps(candidates))
        with self.assertRaises(TelemetryError): await reader.connect_readonly('other')
        await reader.connect_readonly(DEVICE)
        row = await reader.read_status()
        self.assertEqual(row['quality'], 'VALID')
        self.assertEqual(row['valve_state'], 'closed')
        self.assertIs(row['active_watering'], False)
        self.assertEqual(row['remaining_open_seconds'], 0)
        self.assertIsNone(row['flow_liters_per_minute'])
        self.assertEqual(row['source_mode'], 'simulated_fixture')
        await reader.disconnect()
        self.assertEqual(fake.connections, [DEVICE]); self.assertEqual(fake.writes, 0)
        self.assertEqual(fake.disconnects, 1)

    async def test_partial_invalid_and_disconnected(self):
        for change, quality in [({'valve_state': None}, 'PARTIAL'), ({'battery_percent': 150}, 'INVALID'),
                                ({'valve_state': ConnectionError('private info')}, 'DISCONNECTED'),
                                ({'battery_percent': NotImplementedError()}, 'PARTIAL')]:
            with self.subTest(change=change):
                fake=FakeBackend(dict(VALUES, **change))
                reader=GardenaBLE(authorized=True, backend=fake, clock=lambda:T)
                await reader.connect_readonly(DEVICE)
                row=await reader.read_status()
                self.assertEqual(row['quality'], quality)
                if quality in ('DISCONNECTED','INVALID'):
                    self.assertEqual(row['valve_state'], 'unknown')
                self.assertEqual(fake.writes, 0)
                await reader.disconnect()

    async def test_model_and_timeout_fail_closed(self):
        for model in (None, '19033-20'):
            fake=FakeBackend(dict(VALUES,model_number=model))
            reader=GardenaBLE(authorized=True,backend=fake)
            with self.assertRaises(TelemetryError): await reader.connect_readonly(DEVICE)
            self.assertEqual(fake.disconnects,1)
        fake=FakeBackend(dict(VALUES,model_number=None))
        reader=GardenaBLE(authorized=True,backend=fake,confirmed_model='1889-20',clock=lambda:T)
        await reader.connect_readonly(DEVICE)
        self.assertEqual((await reader.read_status())['model_verification'],'owner_declared')
        await reader.disconnect()
        class Slow(FakeBackend):
            async def connect(self,*args): await asyncio.sleep(1)
        slow=Slow();reader=GardenaBLE(authorized=True,backend=slow,timeout_seconds=.01)
        with self.assertRaises(TelemetryError): await reader.connect_readonly(DEVICE)
        self.assertEqual(slow.disconnects,1)
        class Denied(FakeBackend):
            async def discover(self,*args): raise PermissionError('private device id')
        with self.assertRaisesRegex(TelemetryError,'permission'):
            await GardenaBLE(authorized=True,backend=Denied()).discover_devices()


class ObservationTest(unittest.TestCase):
    def test_append_retention_and_provenance(self):
        row=observation(device_alias='fixture',observed_at=T,source_mode='simulated_fixture',values=VALUES)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'observations.jsonl'
            self.assertTrue(append_observation(p,row,max_records=1))
            original=p.read_bytes()
            self.assertFalse(append_observation(p,row,max_records=1))
            changed=dict(row, observed_at_utc='2026-11-15T12:01:00Z')
            with self.assertRaises(TelemetryError): append_observation(p,changed,max_records=1)
            self.assertEqual(original,p.read_bytes())
            self.assertEqual(len(read_observations(p)),1)
            with self.assertRaises(TelemetryError): append_observation(p,dict(row,battery_percent=50))
        for change in ({'observed_at_utc':'2026-02-30T00:00:00Z'}, {'active_watering':0},
                       {'flow_liters_per_minute':2}, {'source_mode':'pretend_real'}, {'serial_number':'private'}):
            with self.subTest(change=change),self.assertRaises(TelemetryError): validate_observation(dict(row,**change))

    def test_normal_workflow_has_no_ble_import_or_access(self):
        code="import sys; import building_ops.__main__; assert 'bleak' not in sys.modules; assert 'gardena_bluetooth' not in sys.modules"
        self.assertEqual(subprocess.run([sys.executable,'-c',code],capture_output=True).returncode,0)
        r=subprocess.run([sys.executable,'-m','building_ops','gardena','scan'],capture_output=True,text=True)
        self.assertNotEqual(r.returncode,0);self.assertIn('authorization',r.stderr)
        self.assertNotIn('Traceback',r.stderr)


@unittest.skipUnless(importlib.util.find_spec('gardena_bluetooth') is not None, 'optional pinned BLE dependency profile not installed')
class PinnedProtocolTest(unittest.IsolatedAsyncioTestCase):
    async def test_upstream_decoders_and_write_guard(self):
        from building_ops.adapters.gardena_ble import NativeBackend
        backend=NativeBackend()
        class Char: properties=['read']
        class Service:
            def get_characteristic(self,uuid):return Char()
        class Services:
            def get_service(self,uuid):return Service()
        class Gatt:
            services=Services()
            def __init__(self):self.data=b'\x00';self.writes=0
            async def read_gatt_char(self,char):return self.data
            async def write_gatt_char(self,*args):self.writes+=1;raise AssertionError()
        transport=Gatt();backend.client=transport
        self.assertIs(await backend.read('valve_state'),False)
        transport.data=b'\x01';self.assertIs(await backend.read('active_watering'),True)
        transport.data=(120).to_bytes(4,'little',signed=True)
        self.assertEqual(await backend.read('remaining_open_seconds'),120)
        transport.data=b'\x52';self.assertEqual(await backend.read('battery_percent'),82)
        transport.data=b'\x00';self.assertEqual(await backend.read('activation_reason'),'manual')
        transport.data=b'';self.assertIsNone(await backend.read('remaining_open_seconds'))
        with self.assertRaises(TelemetryError):await backend.read('clock')
        guard=object.__new__(backend.client_class)
        for name in ('write_gatt_char','write_gatt_descriptor','start_notify','pair','unpair'):
            with self.subTest(name=name),self.assertRaises(TelemetryError):await getattr(guard,name)('ignored')
        self.assertEqual(transport.writes,0)

    async def test_discovery_uses_service_filter_without_connections(self):
        from types import SimpleNamespace
        from building_ops.adapters.gardena_ble import NativeBackend,SCAN_SERVICE
        backend=NativeBackend(); captured={}
        class Scanner:
            def __init__(self,**kw):captured.update(kw)
            async def __aenter__(self):
                for model in (0,2):
                    captured['detection_callback'](SimpleNamespace(address=str(model)),SimpleNamespace(service_uuids=[SCAN_SERVICE],manufacturer_data={0x0426:bytes([4,6,18,model,1])}))
            async def __aexit__(self,*args):pass
        backend.scanner=Scanner
        result=await backend.discover(.001)
        self.assertEqual([r['id'] for r in result],['0'])
        self.assertEqual(captured['service_uuids'],[SCAN_SERVICE])
        self.assertIsNone(backend.client)
