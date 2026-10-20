"""The shared request path (utils._make_request / _throttled_request), offline.

Acceptance criteria (spec: pyopenfec-efile-report-handoff.md, Scope):
  AC-C  Process-wide pacing floor between requests, monkeypatchable.
  AC-D  API key read from the environment at call time; clear error when missing.
  AC-E  Every failure surfaces as PyOpenFecException; a hard 500 exhausts
        BoundedRetry(total=3) in seconds.
  AC-F  Response matrix: 200 results / empty / missing fields / malformed JSON,
        403, 404 HTML, 429 short and long Retry-After, 500xN, ConnectionError,
        ReadTimeout, missing key, pagination.  (200 results / empty / missing
        fields / pagination live in test_efile_report.py.)
"""
import unittest
from unittest import mock

from urllib3.exceptions import ReadTimeoutError

from pyopenfec import Committee, EfileReport
from pyopenfec import utils
from pyopenfec.utils import PyOpenFecException

from .support import FakeClock, FakeTransport, json_response, page, patch_env, text_response


def row(file_number=1):
    return {"committee_id": "C00000001", "file_number": file_number, "report_type": "Q3"}


class TransportTestCase(unittest.TestCase):
    def setUp(self):
        patch_env(self)
        self.sleep = mock.patch.object(utils.time, "sleep").start()
        self.addCleanup(mock.patch.stopall)
        utils._last_request_at = None

    def fetch(self):
        return list(EfileReport.fetch(committee_id="C00000001"))

    def sleeps(self):
        return [call[0][0] for call in self.sleep.call_args_list]


class StatusHandlingTestCase(TransportTestCase):
    """AC-E / AC-F: statuses urllib3 does not retry come straight back as PyOpenFecException."""

    def test_200_malformed_json_body(self):
        with FakeTransport(text_response(200, "<html>Internal Server Error</html>")) as transport:
            with self.assertRaises(PyOpenFecException) as raised:
                self.fetch()
        self.assertEqual(len(transport.requests), 1)
        self.assertIn("JSON", str(raised.exception))

    def test_403_invalid_key(self):
        body = {"error": {"code": "API_KEY_INVALID", "message": "An invalid api_key was supplied."}}
        with FakeTransport(json_response(403, body)) as transport:
            with self.assertRaises(PyOpenFecException) as raised:
                self.fetch()
        self.assertEqual(len(transport.requests), 1)
        self.assertIn("403", str(raised.exception))

    def test_404_html_body(self):
        with FakeTransport(text_response(404, "<html><body>Not Found</body></html>")) as transport:
            with self.assertRaises(PyOpenFecException) as raised:
                self.fetch()
        self.assertEqual(len(transport.requests), 1)
        self.assertIn("404", str(raised.exception))


class RetryTestCase(TransportTestCase):
    """AC-E / AC-F: BoundedRetry really runs underneath requests."""

    def test_429_with_short_retry_after_is_retried_and_honoured(self):
        throttled = json_response(
            429,
            {"error": {"code": "OVER_RATE_LIMIT"}},
            headers={"Retry-After": "2", "X-RateLimit-Limit": "7200", "X-RateLimit-Remaining": "0"},
        )
        with FakeTransport(throttled, json_response(200, page([row()]))) as transport:
            reports = self.fetch()
        self.assertEqual([r.file_number for r in reports], [1])
        self.assertEqual(len(transport.requests), 2)
        self.assertIn(2, self.sleeps())

    def test_429_with_long_retry_after_fails_fast_as_quota_exhausted(self):
        throttled = json_response(
            429,
            {"error": {"code": "OVER_RATE_LIMIT"}},
            headers={"Retry-After": "3600", "X-RateLimit-Limit": "7200", "X-RateLimit-Remaining": "0"},
        )
        with FakeTransport(throttled, repeat_last=True) as transport:
            with self.assertRaises(PyOpenFecException) as raised:
                self.fetch()
        self.assertEqual(len(transport.requests), 1)
        self.assertIn("quota exhausted", str(raised.exception))
        self.assertTrue(all(seconds < 1 for seconds in self.sleeps()), self.sleeps())

    def test_persistent_500_exhausts_retries_in_seconds(self):
        with FakeTransport(json_response(500, {"message": "Internal Server Error"}), repeat_last=True) as transport:
            with self.assertRaises(PyOpenFecException) as raised:
                self.fetch()
        # BoundedRetry(total=3): the first attempt plus three retries, then give up.
        self.assertEqual(len(transport.requests), 4)
        self.assertIn("500", str(raised.exception))
        self.assertLessEqual(sum(self.sleeps()), 10)

    def test_connection_error(self):
        with FakeTransport(ConnectionRefusedError("[Errno 61] Connection refused"), repeat_last=True) as transport:
            with self.assertRaises(PyOpenFecException):
                self.fetch()
        self.assertEqual(len(transport.requests), 4)

    def test_read_timeout(self):
        timeout = ReadTimeoutError(None, "/v1/efile/reports/house-senate/", "Read timed out. (read timeout=30)")
        with FakeTransport(timeout, repeat_last=True) as transport:
            with self.assertRaises(PyOpenFecException):
                self.fetch()
        self.assertEqual(len(transport.requests), 4)


class ApiKeyTestCase(TransportTestCase):
    """AC-D"""

    def test_missing_key_is_a_clear_error_before_any_request(self):
        patch_env(self, OPENFEC_API_KEY=None)
        with FakeTransport() as transport:
            with self.assertRaises(PyOpenFecException) as raised:
                self.fetch()
        self.assertEqual(transport.requests, [])
        self.assertIn("OPENFEC_API_KEY", str(raised.exception))

    def test_empty_key_counts_as_missing(self):
        patch_env(self, OPENFEC_API_KEY="")
        with FakeTransport() as transport:
            with self.assertRaises(PyOpenFecException):
                self.fetch()
        self.assertEqual(transport.requests, [])

    def test_key_is_read_from_the_environment_at_call_time(self):
        with FakeTransport(json_response(200, page([])), json_response(200, page([]))) as transport:
            patch_env(self, OPENFEC_API_KEY="first-key")
            self.fetch()
            patch_env(self, OPENFEC_API_KEY="second-key")
            self.fetch()
        self.assertEqual(transport.query(0)["api_key"], "first-key")
        self.assertEqual(transport.query(1)["api_key"], "second-key")

    def test_key_is_scrubbed_from_transport_error_messages(self):
        # requests quotes the request URL, query string included, in RetryError.
        patch_env(self, OPENFEC_API_KEY="hunter2-secret")
        with FakeTransport(json_response(500, {"message": "Internal Server Error"}), repeat_last=True):
            with self.assertRaises(PyOpenFecException) as raised:
                self.fetch()
        self.assertIn("api.open.fec.gov", str(raised.exception))
        self.assertNotIn("hunter2-secret", str(raised.exception))

    def test_key_is_never_logged(self):
        patch_env(self, OPENFEC_API_KEY="hunter2-secret")
        with FakeTransport(json_response(200, page([row()]))):
            with self.assertLogs(level="DEBUG") as logs:
                self.fetch()
        self.assertTrue(logs.output)
        for line in logs.output:
            self.assertNotIn("hunter2-secret", line)


class PacingTestCase(unittest.TestCase):
    """AC-C"""

    def setUp(self):
        patch_env(self)
        self.clock = FakeClock()
        mock.patch.object(utils, "time", self.clock).start()
        self.addCleanup(mock.patch.stopall)
        utils._last_request_at = None

    def test_consecutive_requests_are_held_to_the_floor(self):
        with FakeTransport(json_response(200, page([])), json_response(200, page([]))):
            list(EfileReport.fetch(committee_id="C00000001"))
            self.clock.now += 0.1
            list(EfileReport.fetch(committee_id="C00000001"))
        self.assertEqual(len(self.clock.sleeps), 1)
        self.assertAlmostEqual(self.clock.sleeps[0], utils.MIN_REQUEST_INTERVAL - 0.1, places=6)

    def test_floor_is_shared_across_resources(self):
        committee = page([{"committee_id": "C00000001", "name": "X"}])
        with FakeTransport(json_response(200, page([])), json_response(200, committee)):
            list(EfileReport.fetch(committee_id="C00000001"))
            list(Committee.fetch(committee_id="C00000001"))
        self.assertEqual(len(self.clock.sleeps), 1)
        self.assertAlmostEqual(self.clock.sleeps[0], utils.MIN_REQUEST_INTERVAL, places=6)

    def test_no_sleep_when_enough_time_has_passed(self):
        with FakeTransport(json_response(200, page([])), json_response(200, page([]))):
            list(EfileReport.fetch(committee_id="C00000001"))
            self.clock.now += utils.MIN_REQUEST_INTERVAL + 1
            list(EfileReport.fetch(committee_id="C00000001"))
        self.assertEqual(self.clock.sleeps, [])

    def test_floor_is_monkeypatchable(self):
        with mock.patch.object(utils, "MIN_REQUEST_INTERVAL", 0):
            with FakeTransport(json_response(200, page([])), json_response(200, page([]))):
                list(EfileReport.fetch(committee_id="C00000001"))
                list(EfileReport.fetch(committee_id="C00000001"))
        self.assertEqual(self.clock.sleeps, [])

    def test_default_floor_matches_the_hourly_quota(self):
        # 7,200 requests/hour is one every 0.5 s.
        self.assertEqual(utils.MIN_REQUEST_INTERVAL, 0.5)
