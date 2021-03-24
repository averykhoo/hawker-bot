import datetime
import time
from functools import wraps

import cachetools


def cache_1s(func):
    @wraps(func)
    @cachetools.cached(cachetools.TTLCache(maxsize=0xFF, ttl=1.0))
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def cache_5s(func):
    @wraps(func)
    @cachetools.cached(cachetools.TTLCache(maxsize=0xFF, ttl=5.0))
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def cache_10s(func):
    @wraps(func)
    @cachetools.cached(cachetools.TTLCache(maxsize=0xFF, ttl=10.0))
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def cache_15s(func):
    @wraps(func)
    @cachetools.cached(cachetools.TTLCache(maxsize=0xFF, ttl=15.0))
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def cache_30s(func):
    @wraps(func)
    @cachetools.cached(cachetools.TTLCache(maxsize=0xFF, ttl=30.0))
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def cache_1m(func):
    @wraps(func)
    @cachetools.cached(cachetools.TTLCache(maxsize=0xFF, ttl=60.0))
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def cache_5m(func):
    @wraps(func)
    @cachetools.cached(cachetools.TTLCache(maxsize=0xFF, ttl=300.0))
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def cache_10m(func):
    @wraps(func)
    @cachetools.cached(cachetools.TTLCache(maxsize=0xFF, ttl=600.0))
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def cache_15m(func):
    @wraps(func)
    @cachetools.cached(cachetools.TTLCache(maxsize=0xFF, ttl=900.0))
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def cache_30m(func):
    @wraps(func)
    @cachetools.cached(cachetools.TTLCache(maxsize=0xFF, ttl=1800.0))
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def cache_1h(func):
    @wraps(func)
    @cachetools.cached(cachetools.TTLCache(maxsize=0xFF, ttl=3600.0))
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def cache_2h(func):
    @wraps(func)
    @cachetools.cached(cachetools.TTLCache(maxsize=0xFF, ttl=7200.0))
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def cache_3h(func):
    @wraps(func)
    @cachetools.cached(cachetools.TTLCache(maxsize=0xFF, ttl=10800.0))
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def cache_4h(func):
    @wraps(func)
    @cachetools.cached(cachetools.TTLCache(maxsize=0xFF, ttl=14400.0))
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def cache_6h(func):
    @wraps(func)
    @cachetools.cached(cachetools.TTLCache(maxsize=0xFF, ttl=21600.0))
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def cache_12h(func):
    @wraps(func)
    @cachetools.cached(cachetools.TTLCache(maxsize=0xFF, ttl=43200.0))
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def cache_1d(func):
    @wraps(func)
    @cachetools.cached(cachetools.TTLCache(maxsize=0xFF, ttl=86400.0))
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


if __name__ == '__main__':

    @cache_5s
    def now():
        return datetime.datetime.now()


    for _ in range(100):
        print(now())
        time.sleep(0.25)
