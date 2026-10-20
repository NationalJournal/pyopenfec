"""Offline doubles for the OpenFEC request path.

``FakeTransport`` scripts what urllib3's connection pool hands back for each
HTTP attempt, one level *below* ``requests.Session``. Everything above that
point is genuine: urllib3's ``Retry`` loop (so ``BoundedRetry`` really runs),
``HTTPAdapter.build_response``, ``requests.Response`` status handling and JSON
decoding. Each scripted response is parsed from raw HTTP bytes by
``http.client``, so headers, reason phrases and body framing are real too.

No socket is ever opened.
"""
import http.client
import io
import json
import os
from unittest import mock
from urllib.parse import parse_qs, urlsplit

import urllib3
from urllib3.connectionpool import HTTPConnectionPool

URLLIB3_MAJOR = int(urllib3.__version__.split(".")[0])

TEST_API_KEY = "test-key"


class _FakeSocket(object):
    """The only thing http.client.HTTPResponse wants from a socket is makefile()."""

    def __init__(self, raw):
        self._file = io.BytesIO(raw)

    def makefile(self, *args, **kwargs):
        return self._file


def httplib_response(status, body=b"", headers=None, reason=None):
    """Build a genuine ``http.client.HTTPResponse`` from status, headers and body."""
    if isinstance(body, str):
        body = body.encode("utf-8")
    if reason is None:
        reason = http.client.responses.get(status, "Unknown")
    lines = ["HTTP/1.1 {} {}".format(status, reason)]
    for key, value in (headers or {}).items():
        lines.append("{}: {}".format(key, value))
    lines.append("Content-Length: {}".format(len(body)))
    raw = ("\r\n".join(lines) + "\r\n\r\n").encode("latin-1") + body
    response = http.client.HTTPResponse(_FakeSocket(raw), method="GET")
    response.begin()
    return response


def json_response(status, payload, headers=None):
    hdrs = {"Content-Type": "application/json"}
    hdrs.update(headers or {})
    return {"status": status, "body": json.dumps(payload).encode("utf-8"), "headers": hdrs}


def text_response(status, text, content_type="text/html", headers=None):
    hdrs = {"Content-Type": content_type}
    hdrs.update(headers or {})
    return {"status": status, "body": text.encode("utf-8"), "headers": hdrs}


def page(results, pages=1, count=None, per_page=20, current=1):
    """A paginated OpenFEC envelope."""
    if count is None:
        count = len(results)
    return {
        "api_version": "1.0",
        "pagination": {"count": count, "page": current, "pages": pages, "per_page": per_page},
        "results": results,
    }


class FakeTransport(object):
    """Context manager scripting the responses (or exceptions) each HTTP attempt gets.

    ``responses`` is consumed in order. With ``repeat_last=True`` the final
    entry is served for every further attempt (a persistently broken
    endpoint). An entry that is an exception instance is raised from inside
    the pool, exactly where a socket error or read timeout would surface.

    ``requests`` records the full URL of every attempt, retries included.
    """

    def __init__(self, *responses, **options):
        self.responses = list(responses)
        self.repeat_last = options.pop("repeat_last", False)
        assert not options, "unknown options: {}".format(sorted(options))
        self.requests = []
        self._patches = []

    def _next_spec(self):
        if not self.responses:
            raise AssertionError("FakeTransport ran out of scripted responses")
        if self.repeat_last and len(self.responses) == 1:
            return self.responses[0]
        return self.responses.pop(0)

    def _make_request(self, pool, conn, method, url, *args, **kwargs):
        self.requests.append("{}://{}{}".format(pool.scheme, pool.host, url))
        spec = self._next_spec()
        if isinstance(spec, BaseException):
            raise spec
        response = httplib_response(spec["status"], spec.get("body", b""), spec.get("headers"))
        if URLLIB3_MAJOR >= 2:
            # urllib3 2.x pools return their own HTTPResponse; 1.x pools return
            # the http.client response and urlopen() wraps it itself.
            return urllib3.response.HTTPResponse(
                body=response,
                headers=list(response.msg.items()),
                status=response.status,
                version=response.version,
                reason=response.reason,
                preload_content=False,
                decode_content=kwargs.get("decode_content", False),
                original_response=response,
                request_url=url,
            )
        return response

    def __enter__(self):
        transport = self

        def _make_request(pool, conn, method, url, *args, **kwargs):
            return transport._make_request(pool, conn, method, url, *args, **kwargs)

        self._patches = [
            mock.patch.object(HTTPConnectionPool, "_make_request", new=_make_request),
            # Never let a proxy from the developer's environment turn this into a real connection.
            mock.patch("requests.sessions.get_environ_proxies", return_value={}),
        ]
        for patch in self._patches:
            patch.start()
        return self

    def __exit__(self, *exc_info):
        for patch in reversed(self._patches):
            patch.stop()
        return False

    def path(self, index=-1):
        return urlsplit(self.requests[index]).path

    def query(self, index=-1):
        """Query parameters of a recorded request as {name: value} (single-valued) or {name: [values]}."""
        parsed = parse_qs(urlsplit(self.requests[index]).query)
        return {k: (v[0] if len(v) == 1 else v) for k, v in parsed.items()}


class FakeClock(object):
    """Stand-in for the ``time`` module: sleeping advances the clock instead of waiting."""

    def __init__(self, start=1000.0):
        self.now = start
        self.sleeps = []

    def monotonic(self):
        return self.now

    def perf_counter(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def patch_env(testcase, **values):
    """Scope environment changes to a test; ``OPENFEC_API_KEY`` is set unless overridden with None."""
    env = dict(os.environ)
    env["OPENFEC_API_KEY"] = TEST_API_KEY
    for key, value in values.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    patcher = mock.patch.dict(os.environ, env, clear=True)
    patcher.start()
    testcase.addCleanup(patcher.stop)
