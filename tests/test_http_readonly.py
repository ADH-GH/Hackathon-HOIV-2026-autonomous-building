"""Isolated transport rejection controls; no external endpoints are contacted."""
from email.message import Message
from unittest import TestCase
from unittest.mock import patch
from pathlib import Path
import tempfile

from building_ops.adapters.http_readonly import Reader, decode, MAX_BYTES
from building_ops.artifact_io import _write_json
from building_ops.telemetry import TelemetryError


class ReadOnlyTransportTest(TestCase):
    def test_bounded_json_positive_and_negative_controls(self):
        self.assertEqual(decode(b'{"value":0,"missing":null}'), {'value':0,'missing':None})
        for raw in (b'{"a":1,"a":2}', b'NaN', b'1e999', b'not json', b' '* (MAX_BYTES+1), 'not bytes'):
            with self.subTest(raw_type=type(raw)), self.assertRaises(TelemetryError):
                decode(raw)

    def test_authorization_urls_and_credential_controls(self):
        for url in ('https://example.invalid', 'http://example.invalid', 'https://u:p@example.invalid',
                    'https://example.invalid/?secret=x', 'https://example.invalid/#fragment', 'http://localhost'):
            with self.subTest(url=url), self.assertRaises(TelemetryError): Reader(url)
        for kwargs in ({'attempts':4}, {'timeout':float('nan')}, {'token_env':'not a name'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(TelemetryError): Reader('http://127.0.0.1', **kwargs)
        for token in ('', 'secret\r\nInjected: yes'):
            with patch.dict('os.environ', {'TEST_HA_TOKEN':token}), self.assertRaises(TelemetryError):
                Reader('http://127.0.0.1', token_env='TEST_HA_TOKEN').read()

    def test_media_size_and_get_only_positive_control(self):
        class Response:
            def __init__(self, media, raw):
                self.headers=Message();self.headers['Content-Type']=media;self.raw=raw
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read1(self,size):
                chunk,self.raw=self.raw[:size],self.raw[size:];return chunk
        reader=Reader('http://127.0.0.1',media_type='application/json')
        with patch.object(reader.opener,'open',return_value=Response('application/json',b'[]')) as opened:
            self.assertEqual(reader.read(),(b'[]',{'state':'received','attempts':1}))
            self.assertEqual(opened.call_args.args[0].get_method(),'GET')
        for response in (Response('text/html',b'[]'),Response('application/json',b' '*(MAX_BYTES+1))):
            with patch.object(reader.opener,'open',return_value=response), self.assertRaises(TelemetryError):reader.read()

    def test_atomic_failure_preserves_previous_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'evidence.json';_write_json(path,{'before':True});before=path.read_bytes()
            with patch('building_ops.artifact_io.os.replace',side_effect=OSError('simulated replacement failure')):
                with self.assertRaises(OSError):_write_json(path,{'after':True})
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual(list(Path(directory).iterdir()),[path])

    def test_redirect_is_not_followed(self):
        from http.server import BaseHTTPRequestHandler, HTTPServer
        from threading import Thread
        paths=[]
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                paths.append(self.path);self.send_response(302)
                self.send_header('Location','/must-not-read');self.end_headers()
            def log_message(self,*args):pass
        server=HTTPServer(('127.0.0.1',0),Handler)
        thread=Thread(target=server.serve_forever);thread.start()
        try:
            with self.assertRaises(TelemetryError):Reader(f'http://127.0.0.1:{server.server_port}/states').read()
            self.assertEqual(paths,['/states'])
        finally:
            server.shutdown();thread.join();server.server_close()
