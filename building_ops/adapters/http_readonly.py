"""Bounded standard-library GET/JSON transport; no service or actuator calls.

Isolated from the existing SenML shadow adapter for the HA publication boundary.
No SenML mapping, hotel detector or unrelated pipeline dependency is included.
"""
import json
import math
import os
import time
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler

from ..telemetry import TelemetryError

MAX_BYTES = 1024 * 1024


def finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise TelemetryError('duplicate JSON key')
        result[key] = value
    return result


def _json_float(value):
    number=float(value)
    if not math.isfinite(number):raise TelemetryError('non-finite JSON number')
    return number


def decode(raw):
    if not isinstance(raw, bytes):
        raise TelemetryError("JSON payload must be bytes")
    if len(raw) > MAX_BYTES:
        raise TelemetryError('input exceeds one MiB profile limit')
    try:
        return json.loads(raw, object_pairs_hook=_pairs, parse_float=_json_float,
                          parse_constant=lambda _: (_ for _ in ()).throw(TelemetryError('non-finite JSON number')))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise TelemetryError('invalid bounded JSON input') from exc


class NoRedirect(HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, message, headers):
        fp.close()
        raise TelemetryError('redirects are not allowed')

    http_error_301 = http_error_303 = http_error_307 = http_error_308 = http_error_302

    def redirect_request(self, *args, **kwargs):
        raise TelemetryError('redirects are not allowed')


class Reader:
    def __init__(self, url, *, authorized=False, attempts=3, timeout=5, token_env=None, media_type="application/json"):
        if not isinstance(url,str) or any(ord(c)<33 or ord(c)>126 for c in url):
            raise TelemetryError("feed URL must be printable ASCII without whitespace")
        try:
            parsed = urlsplit(url)
            port = parsed.port
        except ValueError as exc:
            raise TelemetryError("invalid feed URL") from exc
        loopback = parsed.hostname in {'127.0.0.1', '::1'}
        if (not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.scheme not in {'https','http'} or parsed.scheme == 'http' and not loopback):
            raise TelemetryError('use an HTTPS read-only feed without URL credentials/query; HTTP only for literal loopback')
        if not loopback and authorized is not True:
            raise TelemetryError('explicit owner authorization required before non-loopback access')
        if type(attempts) is not int or not 1 <= attempts <= 3 or not finite(timeout) or not 0 < timeout <= 10:
            raise TelemetryError('attempts must be 1..3 and timeout must be in (0,10] seconds')
        if token_env is not None and (not isinstance(token_env,str) or not token_env.isidentifier()):
            raise TelemetryError('token must be supplied by a named environment variable')
        if media_type not in {"application/senml+json", "application/json"}:
            raise TelemetryError("unsupported read-only transport media type")
        self.media_type = media_type
        self.url, self.attempts, self.timeout, self.token_env = url, attempts, timeout, token_env
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def read(self):
        token = os.environ.get(self.token_env) if self.token_env else None
        if token and any(ord(c)<32 or ord(c)>126 for c in token):
            raise TelemetryError("invalid credential format")
        if self.token_env and not token:
            raise TelemetryError('configured token environment variable is empty')
        for attempt in range(1,self.attempts+1):
            request = Request(self.url, method='GET', headers={'Accept':self.media_type})
            if token:
                request.add_header('Authorization','Bearer '+token)
            try:
                deadline=time.monotonic()+self.timeout
                with self.opener.open(request, timeout=self.timeout) as response:
                    if response.headers.get_content_type() != self.media_type:
                        raise TelemetryError('unsupported feed media type')
                    chunks=[]; size=0
                    while size <= MAX_BYTES:
                        if time.monotonic()>deadline:
                            raise TimeoutError("bounded telemetry read elapsed")
                        chunk=response.read1(min(65536, MAX_BYTES+1-size))
                        if not chunk:
                            break
                        chunks.append(chunk); size+=len(chunk)
                    raw=b"".join(chunks)
                if len(raw)>MAX_BYTES:
                    raise TelemetryError('feed response exceeds profile limit')
                return raw, {'state':'received', 'attempts':attempt}
            except HTTPError as exc:
                exc.close()
                if exc.code < 500:
                    return None, {'state':'unavailable','attempts':attempt,'reason':'http_request_rejected','http_status':exc.code}
            except (URLError, TimeoutError, OSError, HTTPException):
                pass
            if attempt < self.attempts:
                time.sleep(.1 * attempt)
        return None, {'state':'unavailable','attempts':self.attempts,'reason':'connection_failed'}
