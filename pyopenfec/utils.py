import json
import os
import time
import logging
from datetime import datetime

import requests
import six
from pytz import timezone

if six.PY2:
    from exceptions import Exception, NotImplementedError, TypeError


API_KEY = os.environ.get('OPENFEC_API_KEY', None)
BASE_URL = 'https://api.open.fec.gov'
VERSION = '/v1'

eastern = timezone('US/Eastern')

class PyOpenFecException(Exception):
    """
    An exception from the PyOpenFec API.
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

    def __unicode__(self):
        return unicode(self.value)

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
        resource = '{class_name}s'.format(class_name=cls.__name__.lower())
        initial_results = cls._make_request(resource, **kwargs)
        if initial_results.get('pagination', None):
            return initial_results['pagination']['count']

    @classmethod
    def _throttled_request(cls, url, params):
        response = None
        if not cls.ratelimit_remaining == 0:
            response = requests.get(url, params=params)
            if 'x-ratelimit-remaining' in response.headers:
                cls.ratelimit_remaining = int(response.headers['x-ratelimit-remaining'])
            else:
                cls.ratelimit_remaining = 1000

        if cls.ratelimit_remaining == 0 or response.status_code == 429:
            while cls.ratelimit_remaining == 0 or response.status_code == 429:
                cls.wait_time *= 1.5
                logging.warn(
                    'API rate limit exceeded. Waiting {}s.'.format(
                        cls.wait_time))
                time.sleep(cls.wait_time)
                response = requests.get(url, params=params)
                if 'x-ratelimit-remaining' in response.headers:
                    cls.ratelimit_remaining = int(response.headers['x-ratelimit-remaining'])
                else:
                    cls.ratelimit_remaining = 0

        cls.wait_time = 0.5
        return response

    @classmethod
    def fetch(cls, **kwargs):
        raise NotImplementedError('fetch command implemented in subclasses only')

    @classmethod
    def fetch_one(cls, **kwargs):
        if 'resource' in kwargs:
            resource = kwargs.pop('resource')
        else:
            resource = '%ss' % cls.__name__.lower()
        initial_results = cls._make_request(resource, **kwargs)

        if initial_results.get('results', None):
            if len(initial_results['results']) > 0:
                first_result = initial_results['results'][0]
                return cls(**first_result)
        return None

    @classmethod
    def _make_request(cls, resource, **kwargs):
        url = BASE_URL + VERSION + '/%s' % resource

        if not API_KEY:
            raise PyOpenFecException('Please export an env var OPENFEC_API_KEY with your API key.')

        params = dict(kwargs)
        params['api_key'] = API_KEY

        r = cls._throttled_request(url, params)
        logging.debug(r.url)

        if r.status_code != 200:
            raise PyOpenFecException('OpenFEC site returned a status code of %s for this request.' % r.status_code)

        return r.json()


class PyOpenFecApiPaginatedClass(PyOpenFecApiClass):

    @classmethod
    def fetch(cls, **kwargs):
        if 'resource' in kwargs:
            resource = kwargs.pop('resource')
        else:
            resource = '%ss' % cls.__name__.lower()
        initial_results = cls._make_request(resource, **kwargs)

        if initial_results.get('results', None):
            if len(initial_results['results']) > 0:
                for result in initial_results['results']:
                    yield cls(**result)

        if initial_results.get('pagination', None):
            if initial_results['pagination'].get('pages', None):
                if initial_results['pagination']['pages'] > 1:
                    current_page = 2

                    while current_page <= initial_results['pagination']['pages']:
                        params = dict(kwargs)
                        params['page'] = current_page
                        paged_results = cls._make_request(resource, **params)

                        if paged_results.get('results', None):
                            if len(paged_results['results']) > 0:
                                for result in paged_results['results']:
                                    yield cls(**result)

                        current_page += 1


class PyOpenFecApiIndexedClass(PyOpenFecApiClass):

    @classmethod
    def fetch(cls, **kwargs):
        if 'resource' in kwargs:
            resource = kwargs.pop('resource')
        else:
            resource = '%ss' % cls.__name__.lower()
        initial_results = cls._make_request(resource, **kwargs)

        if initial_results.get('results', None):
            if len(initial_results['results']) > 0:
                for result in initial_results['results']:
                    yield cls(**result)

        if initial_results.get('pagination', None):
            if initial_results['pagination'].get('pages', None):
                if initial_results['pagination']['pages'] > 1:
                    last_index = initial_results['pagination']['last_indexes']['last_index']

                    while last_index is not None:
                        params = dict(kwargs)
                        params['last_index'] = int(last_index)
                        indexed_results = cls._make_request(resource, **params)

                        if indexed_results.get('results', None):
                            if len(indexed_results['results']) > 0:
                                for result in indexed_results['results']:
                                    yield cls(**result)
                            last_index = indexed_results['pagination']['last_indexes']['last_index']
                        else:
                            last_index = None


class SearchMixin(object):

    @classmethod
    def search(cls, querystring):
        resource = 'names/%ss' % cls.__name__.lower()
        search_result = cls._make_request(**{"resource": resource,
                                             "q": querystring})
        identifiers = [r['id'] for r in search_result['results']]
        identifier_field = '{c}_id'.format(c=cls.__name__.lower())
        for o in cls.fetch(**{identifier_field: identifiers}):
            yield o


def default_empty_list(func):
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TypeError:
            return []
    return inner


def set_instance_attr(instance, k, v, date_fields):
    if k in date_fields and v is not None:
        parsed_date = datetime.strptime(v, date_fields[k])
        tz_aware = eastern.localize(parsed_date)
        setattr(instance, k, tz_aware)
        return
    setattr(instance, k, v)
