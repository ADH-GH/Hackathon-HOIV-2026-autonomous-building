import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from building_ops.gardena_experience import demo,render
from building_ops.external_dashboard import payload
from building_ops.gardena_interaction import answers,ask,QUESTIONS,TOOLS_JS
from building_ops.telemetry import TelemetryError


class InteractionTest(unittest.TestCase):
    def test_all_questions_share_policy_and_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'demo';demo(root);view=payload(evidence=root/'decisions.evidence.json')
            responses=answers(view)
            for key,question in QUESTIONS.items():self.assertEqual(ask(view,question),responses[key])
            self.assertEqual(responses['duration']['watering_limit_seconds'],60)
            self.assertEqual(len(responses['duration']['findings']),1)
            self.assertIn('not measured',responses['consumption']['answer'])
            self.assertFalse(responses['control']['actuator_control_enabled'])
            self.assertFalse(responses['flow']['flow_measurement_verified'])
            self.assertTrue(all(r['verification_status']=='NOT_TESTED' for r in responses.values()))
            with self.assertRaises(TelemetryError):ask(view,'do a completely unrelated task')
            self.assertEqual(ask(view,'Close valve and reset device'),responses['control'])
            serialized=json.dumps(responses)
            for row in view['devices']:self.assertNotIn(row['device_alias'],serialized)
            self.assertIn('unknown',serialized);self.assertIn('STALE',serialized)

    def test_browser_answers_equal_cli_and_voice_handlers_no_control(self):
        if not shutil.which('node'):self.skipTest('Node required for actual JS handler execution')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'demo';demo(root)
            data=answers(payload(evidence=root/'decisions.evidence.json'))
            page=(root/'experience.html').read_text()
            embedded=json.loads(re.search(r'<script id="irrigation-answers" type="application/json">(.*?)</script>',page,re.S)[1])
            self.assertEqual(data,embedded)
            js=TOOLS_JS+'\nconst t=irrigationTools('+json.dumps(data)+');console.log(JSON.stringify({keys:Object.keys(t),status:t.get_irrigation_status(),findings:t.get_irrigation_findings(),bad:t.explain_irrigation_finding({finding_id:"missing"})}));'
            result=subprocess.run(['node','-e',js],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr);got=json.loads(result.stdout)
            self.assertEqual(got['status'],data['status']);self.assertEqual(got['findings'],data['warnings'])
            self.assertIn('error',got['bad'])
            self.assertFalse(any(word in key for word in ('close','start','stop','control','write') for key in got['keys']))

    def test_voice_opt_in_and_no_automatic_microphone(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'demo';demo(root)
            offline=(root/'experience.html').read_text();self.assertNotIn('cdn.jsdelivr',offline);self.assertNotIn('getUserMedia',offline)
            render(root/'decisions.evidence.json',root/'voice.html',voice_agent='test_public_agent')
            voice=(root/'voice.html').read_text()
            self.assertIn('Explicit consent required; microphone not accessed.',voice)
            self.assertLess(voice.index("if(!document.getElementById('voice-consent').checked)"),voice.index("await import('https://"))
            self.assertIn('No raw device identifiers',voice)
            # No automatic connection in top-level code: the import/session is inside a click handler.
            self.assertLess(voice.index("document.getElementById('voice').onclick=async"),voice.index('Conversation.startSession'))
