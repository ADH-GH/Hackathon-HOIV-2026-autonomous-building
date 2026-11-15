import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from building_ops.dashboard import build
from building_ops.external_dashboard import payload
from tests.test_pipeline import write_fixture
from tests.test_irrigation_monitor import ROOT

class ExternalDashboardTest(unittest.TestCase):
    def test_optional_static_isolated_view(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);write_fixture(root)
            decisions=root/'decisions.jsonl';decisions.write_text('')
            old=build(root,decisions,root/'old.html').read_text()
            old_data=json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>',old,re.S)[1])
            self.assertNotIn('externalGardena',old_data)
            new=build(root,decisions,root/'new.html',gardena_observations=ROOT/'watering.jsonl',gardena_as_of='2026-11-15T12:06:00Z').read_text()
            data=json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>',new,re.S)[1])
            self.assertEqual(data['episodes'],old_data['episodes'])
            ext=data['externalGardena']
            self.assertEqual(ext['devices'][0]['quality'],'STALE')
            self.assertEqual(ext['devices'][0]['source_mode'],'simulated_fixture')
            self.assertEqual(ext['operational_outcome'],'not_measured')
            self.assertNotIn('device_id',json.dumps(ext))
            if shutil.which('node'):
                script=re.findall(r'<script>(.*?)</script>',new,re.S)[-1]
                p=root/'page.js';p.write_text(script)
                result=subprocess.run(['node','--check',str(p)],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                # Execute the actual view renderer without a browser or network.
                function=script[script.index('function gardenaView'):script.index('function render()')]
                harness="const seen=[]; const el=(tag,cls,text)=>({append(...x){},}); const D={externalGardena:"+json.dumps(ext)+"}; const root={append(){}};\n"+function+"\ngardenaView(root);"
                result=subprocess.run(['node','-e',harness],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)

    def test_cutoff_does_not_include_future_observation(self):
        data=payload(ROOT/'watering.jsonl',as_of='2026-11-15T11:00:00Z')
        self.assertEqual(data['devices'],[])
        self.assertEqual(data['findings'],[])
