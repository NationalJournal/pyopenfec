import json
import os
import time
import logging
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from pytz import timezone


API_KEY = os.environ.get("OPENFEC_API_KEY", None)
BASE_URL = "https://api.open.fec.gov"
VERSION = "/v1"

eastern = timezone("US/Eastern")

date_formats = ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S+00:00", "%Y-%m-%dT%H:%M:%S.%f+00:00"]

class TimeoutHTTPAdapter(HTTPAdapter):
    def __init__(self, *args, **kwargs):
        self.timeout = 5  # in seconds
        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]
            del kwargs["timeout"]
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        timeout = kwargs.get("timeout")
        if timeout is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)


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

    ratelimit_remaining = 1000
    wait_time = 0.5

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
        response = None
        session = requests.Session()
        retry = Retry(
            total=100,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503],
            respect_retry_after_header=False,
        )
        session.mount("https://", TimeoutHTTPAdapter(max_retries=retry))

        if not cls.ratelimit_remaining == 0:
            start = time.perf_counter()
            response = session.get(url, params=params)
            logging.debug("Request completed in {} secs.".format(round(time.perf_counter() - start, 2)))

            if "x-ratelimit-remaining" in response.headers:
                cls.ratelimit_remaining = int(response.headers["x-ratelimit-remaining"])
            else:
                cls.ratelimit_remaining = 1000

        if cls.ratelimit_remaining == 0 or response.status_code == 429:
            while cls.ratelimit_remaining == 0 or response.status_code == 429:
                cls.wait_time += 0.5
                logging.warning("API rate limit exceeded. Waiting {}s.".format(cls.wait_time))
                time.sleep(cls.wait_time)
                start = time.perf_counter()
                response = session.get(url, params=params)
                logging.debug("Request completed in {} secs.".format(round(time.perf_counter() - start, 2)))

                if "x-ratelimit-remaining" in response.headers:
                    cls.ratelimit_remaining = int(
                        response.headers["x-ratelimit-remaining"]
                    )
                elif response.status_code == 200:
                    cls.ratelimit_remaining = 120
                else:
                    cls.ratelimit_remaining = 0

        cls.wait_time = 0.5
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
