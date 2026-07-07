import json
import os
import time
import logging
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from requests.packages.urllib3.exceptions import MaxRetryError, ResponseError
from pytz import timezone


API_KEY = os.environ.get("OPENFEC_API_KEY", None)
BASE_URL = "https://api.open.fec.gov"
VERSION = "/v1"

#: When the remaining hourly request budget drops to or below this, log a
#: heads-up so approaching the limit is visible *before* we start getting 429'd.
LOW_RATELIMIT_REMAINING = 25

eastern = timezone("US/Eastern")

date_formats = ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S+00:00", "%Y-%m-%dT%H:%M:%S.%f+00:00"]

class TimeoutHTTPAdapter(HTTPAdapter):
    # (connect timeout, read timeout) in seconds. FEC finance endpoints can be
    # slow to respond, so the read timeout is generous while connect stays short.
    # A too-short timeout was the old default (5s), which made heavier endpoints
    # read-timeout and trigger retry storms.
    def __init__(self, *args, **kwargs):
        self.timeout = (10, 30)
        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]
            del kwargs["timeout"]
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        timeout = kwargs.get("timeout")
        if timeout is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)


class BoundedRetry(Retry):
    """urllib3 Retry that uses the size of a 429's ``Retry-After`` to tell a
    transient throttle apart from hourly-quota exhaustion.

    FEC (via api.data.gov / api-umbrella) sends an accurate ``Retry-After`` on a
    429. A short wait means a burst/per-minute throttle -- worth riding out. A
    long wait means the rolling hourly quota is spent and won't reopen within any
    reasonable budget, so retrying just hammers an endpoint that will keep
    rejecting us. In that case we fail fast; the consuming job checkpoints its
    progress and resumes on the next run.
    """

    #: The boundary, in seconds, between the two cases above. A ``Retry-After``
    #: at or below this is treated as a transient throttle we ride out (and honor
    #: as our per-retry sleep cap); anything above it is treated as hourly-quota
    #: exhaustion and we fail fast instead of retrying.
    max_retry_after = 60

    def get_retry_after(self, response):
        retry_after = super().get_retry_after(response)
        if retry_after is None:
            return None
        return min(retry_after, self.max_retry_after)

    def increment(self, method=None, url=None, response=None, error=None, _pool=None, _stacktrace=None):
        if response is not None and getattr(response, "status", None) == 429:
            headers = getattr(response, "headers", None) or {}
            retry_after = super().get_retry_after(response)
            limit = headers.get("x-ratelimit-limit")
            remaining = headers.get("x-ratelimit-remaining")

            if retry_after is not None and retry_after > self.max_retry_after:
                # Hourly quota exhausted -- the window won't reopen within our
                # budget, so stop rather than hammer an endpoint that will keep
                # rejecting us. This is the actionable "quota too low" signal.
                logging.warning(
                    "FEC hourly API quota exhausted (HTTP 429): limit=%s/hour, "
                    "remaining=%s, server asked to wait %ss (> %ss budget). "
                    "Failing fast (the job resumes next run). Recurring hits mean "
                    "the quota is too low -- consider requesting a higher OpenFEC quota.",
                    limit, remaining, retry_after, self.max_retry_after,
                )
                raise MaxRetryError(_pool, url, ResponseError("FEC hourly quota exhausted"))

            # Short/transient throttle (e.g. a per-minute burst limit). urllib3
            # honors Retry-After and retries; keep this at DEBUG so a run that
            # recovers on its own -- the logic doing its job -- stays quiet.
            logging.debug(
                "FEC throttled request (HTTP 429): retry-after=%ss, remaining=%s; retrying.",
                retry_after, remaining,
            )
        return super().increment(
            method, url, response=response, error=error, _pool=_pool, _stacktrace=_stacktrace
        )


def _log_ratelimit_usage(response):
    """Record FEC rate-limit budget from a response's headers.

    DEBUG on every response (enable it for a run to observe real usage and
    confirm the actual hourly limit), plus a WARNING once we're down to the last
    ``LOW_RATELIMIT_REMAINING`` requests so we see the limit approaching before a
    429 rather than after.
    """
    headers = getattr(response, "headers", None) or {}
    remaining = headers.get("x-ratelimit-remaining")
    limit = headers.get("x-ratelimit-limit")
    if remaining is None:
        return
    logging.debug("FEC rate limit: %s of %s requests remaining this hour.", remaining, limit)
    try:
        remaining = int(remaining)
    except (TypeError, ValueError):
        return
    if remaining <= LOW_RATELIMIT_REMAINING:
        logging.warning(
            "Approaching FEC hourly rate limit: only %s of %s requests remaining this hour.",
            remaining, limit,
        )


class PyOpenFecException(Exception):
    """
    An exception from the PyOpenFec API.
    """

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

    def __repr__(self):
        return repr(self.value)


class PyOpenFecApiClass(object):
    """
    Universal class for PyOpenFec API classes to inherit from.
    """

    def to_dict(self):
        return self.__dict__

    def to_json(self):
        return json.dumps(self.to_dict())

    @classmethod
    def count(cls, **kwargs):
        resource = "{class_name}s".format(class_name=cls.__name__.lower())
        initial_results = cls._make_request(resource, **kwargs)
        if initial_results.get("pagination", None):
            return initial_results["pagination"]["count"]

    @classmethod
    def _throttled_request(cls, url, params):
        # Retries (including 429 rate-limit handling and Retry-After waits) are
        # owned entirely by urllib3's Retry -- no separate manual back-off loop.
        # A low total plus a bounded Retry-After keeps a slow or throttled FEC
        # from spinning long enough to trip the consumer's overall timeout.
        session = requests.Session()
        retry = BoundedRetry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503],
            respect_retry_after_header=True,
        )
        session.mount("https://", TimeoutHTTPAdapter(max_retries=retry))

        start = time.perf_counter()
        try:
            response = session.get(url, params=params)
        except requests.exceptions.RequestException as exc:
            # Retries exhausted (rate limit / server errors / timeouts) or the
            # request otherwise failed. Fail fast with the library's own
            # exception type instead of spinning.
            raise PyOpenFecException(
                "Request to OpenFEC failed after retries: {}".format(exc)
            )
        logging.debug("Request completed in {} secs.".format(round(time.perf_counter() - start, 2)))
        _log_ratelimit_usage(response)
        return response

    @classmethod
    def fetch(cls, **kwargs):
        raise NotImplementedError("fetch command implemented in subclasses only")

    @classmethod
    def fetch_one(cls, **kwargs):
        if "resource" in kwargs:
            resource = kwargs.pop("resource")
        else:
            resource = "%ss" % cls.__name__.lower()
        initial_results = cls._make_request(resource, **kwargs)

        if initial_results.get("results", None):
            if len(initial_results["results"]) > 0:
                first_result = initial_results["results"][0]
                return cls(**first_result)
        return None

    @classmethod
    def _make_request(cls, resource, **kwargs):
        url = BASE_URL + VERSION + "/%s/" % resource

        if not API_KEY:
            raise PyOpenFecException(
                "Please export an env var OPENFEC_API_KEY with your API key."
            )

        params = dict(kwargs)
        params["api_key"] = API_KEY

        r = cls._throttled_request(url, params)
        logging.debug(r.url)

        if r.status_code != 200:
            raise PyOpenFecException(
                "OpenFEC site returned a status code of %s for this request."
                % r.status_code
            )

        return r.json()


class PyOpenFecApiPaginatedClass(PyOpenFecApiClass):
    @classmethod
    def fetch(cls, **kwargs):
        if "resource" in kwargs:
            resource = kwargs.pop("resource")
        else:
            resource = "%ss" % cls.__name__.lower()
        initial_results = cls._make_request(resource, **kwargs)

        if initial_results.get("results", None):
            if len(initial_results["results"]) > 0:
                for result in initial_results["results"]:
                    yield cls(**result)

        if initial_results.get("pagination", None):
            if initial_results["pagination"].get("pages", None):
                if initial_results["pagination"]["pages"] > 1:
                    current_page = 2

                    while current_page <= initial_results["pagination"]["pages"]:
                        params = dict(kwargs)
                        params["page"] = current_page
                        paged_results = cls._make_request(resource, **params)

                        if paged_results.get("results", None):
                            if len(paged_results["results"]) > 0:
                                for result in paged_results["results"]:
                                    yield cls(**result)

                        current_page += 1


class PyOpenFecApiIndexedClass(PyOpenFecApiClass):
    @classmethod
    def fetch(cls, **kwargs):
        if "resource" in kwargs:
            resource = kwargs.pop("resource")
        else:
            resource = "%ss" % cls.__name__.lower()
        initial_results = cls._make_request(resource, **kwargs)

        if initial_results.get("results", None):
            if len(initial_results["results"]) > 0:
                for result in initial_results["results"]:
                    yield cls(**result)

        if initial_results.get("pagination", None):
            if initial_results["pagination"].get("pages", None):
                if initial_results["pagination"]["pages"] > 1:
                    last_index = initial_results["pagination"]["last_indexes"][
                        "last_index"
                    ]

                    while last_index is not None:
                        params = dict(kwargs)
                        params["last_index"] = int(last_index)
                        indexed_results = cls._make_request(resource, **params)

                        if indexed_results.get("results", None):
                            if len(indexed_results["results"]) > 0:
                                for result in indexed_results["results"]:
                                    yield cls(**result)
                            last_index = indexed_results["pagination"]["last_indexes"][
                                "last_index"
                            ]
                        else:
                            last_index = None


class SearchMixin(object):
    @classmethod
    def search(cls, querystring):
        resource = "names/%ss" % cls.__name__.lower()
        search_result = cls._make_request(**{"resource": resource, "q": querystring})
        identifiers = [r["id"] for r in search_result["results"]]
        identifier_field = "{c}_id".format(c=cls.__name__.lower())
        for o in cls.fetch(**{identifier_field: identifiers}):
            yield o


def default_empty_list(func):
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TypeError:
            return []

    return inner


def set_instance_attr(instance, attribute_name, value, date_fields):
    """
    Set an attribute on an instance with special handling for date fields.

    Args:
        instance: The instance on which to set the attribute.
        attribute_name: The name of the attribute to set.
        value: The value to set for the attribute.
        date_fields: List of attribute names that represent date fields.

    Returns:
        None
    """
    if attribute_name in date_fields and value is not None:
        parsed_date = None
        # Try parsing the date string with different formats
        for format_str in date_formats:
            try:
                parsed_date = datetime.strptime(value, format_str)
                # Convert the parsed date to a timezone-aware datetime
                tz_aware = eastern.localize(parsed_date)
                setattr(instance, attribute_name, tz_aware)
                return
            except ValueError:
                pass

    setattr(instance, attribute_name, value)
