import json
import unittest
import threading
from datetime import datetime,timedelta,timezone
from http.server import BaseHTTPRequestHandler,HTTPServer
from building_ops.gardena import Reader, normalize, detect

T=datetime(2026,1,1,tzinfo=timezone.utc)
def state(entity,value,t,unit=None):
    return dict(entity_id=entity,state=value,last_reported=t.isoformat(),attributes={'unit_of_measurement':unit})
class GardenaTest(unittest.TestCase):
    def test_read_only_local_pipeline(self):
        requests=[]
        clock=[T]
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(('GET',self.path));self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers()
                entity=self.path.rsplit('/',1)[-1]
                self.wfile.write(json.dumps(state(entity,'closed' if entity.startswith('valve.') else '2',clock[0],None if entity.startswith('valve.') else 'L/min')).encode())
            def log_message(self,*args):pass
        server=HTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever);thread.start()
        try:
            reader=Reader(f'http://127.0.0.1:{server.server_port}')
            records=[]
            for offset in (0,60,120,180):
                clock[0]=T+timedelta(seconds=offset)
                for metric,entity in [('valve_state','valve.garden'),('flow_l_min','sensor.flow')]:
                    records.append(normalize(reader.state(entity),asset='GARDEN',metric=metric,now=clock[0]))
        finally:server.shutdown();thread.join();server.server_close()
        self.assertEqual(requests,[('GET','/api/states/valve.garden'),('GET','/api/states/sensor.flow')]*4)
        cfg=dict(flow_tolerance_l_min=.1,persistence_seconds=60,settle_seconds=30,max_skew_seconds=90,hydraulic_scope_confirmed=True)
        self.assertEqual(len(detect(records,cfg)),1)
        self.assertEqual(detect([r for r in records if r['metric']=='valve_state'],cfg),[])
        self.assertTrue(detect(records,cfg)[0]['shadow_only'])
    def test_quality_and_authorization(self):
        for value,age,expected in [('unknown',0,'unknown'),('on',181,'stale')]:
            self.assertEqual(normalize(state('valve.g',value,T),asset='G',metric='valve_state',now=T+timedelta(seconds=age))['quality'],expected)
        with self.assertRaises(ValueError):Reader('https://example.invalid')
        with self.assertRaises(ValueError):Reader('http://192.168.1.2',live_authorized=True)
