import datetime
import time
from functools import wraps
from typing import Optional
from typing import Union

import cachetools


def cache_ttl(seconds: Union[int, float, datetime.timedelta],
              maxsize: Optional[int] = None):
    if isinstance(seconds, datetime.timedelta):
        seconds = seconds.total_seconds()
    assert isinstance(seconds, (int, float)), seconds

    def decorator(func):
        @wraps(func)
        @cachetools.cached(cachetools.TTLCache(maxsize=maxsize, ttl=seconds))
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator


cache_1s = cache_ttl(1, 0xFF)
cache_5s = cache_ttl(5, 0xFF)
cache_1m = cache_ttl(60, 0xFF)
cache_1h = cache_ttl(60 * 60, 0xFF)
cache_1d = cache_ttl(24 * 60 * 60, 0xFF)

if __name__ == '__main__':

    @cache_5s
    def now():
        return datetime.datetime.now()


    for _ in range(100):
        print(now())
        time.sleep(0.25)
