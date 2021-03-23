import datetime
import time
from functools import wraps


def cache_1s(func):
    reset_time: float = -1.0
    prev_value = None

    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal reset_time, prev_value
        curr_time = time.time()
        if curr_time > reset_time:
            reset_time = curr_time + 1.0
            prev_value = func(*args, **kwargs)

        return prev_value

    return wrapper


def cache_5s(func):
    reset_time: float = -1.0
    prev_value = None

    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal reset_time, prev_value
        curr_time = time.time()
        if curr_time > reset_time:
            reset_time = curr_time + 5.0
            prev_value = func(*args, **kwargs)

        return prev_value

    return wrapper


def cache_10s(func):
    reset_time: float = -1.0
    prev_value = None

    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal reset_time, prev_value
        curr_time = time.time()
        if curr_time > reset_time:
            reset_time = curr_time + 10.0
            prev_value = func(*args, **kwargs)

        return prev_value

    return wrapper


def cache_15s(func):
    reset_time: float = -1.0
    prev_value = None

    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal reset_time, prev_value
        curr_time = time.time()
        if curr_time > reset_time:
            reset_time = curr_time + 15.0
            prev_value = func(*args, **kwargs)

        return prev_value

    return wrapper


def cache_30s(func):
    reset_time: float = -1.0
    prev_value = None

    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal reset_time, prev_value
        curr_time = time.time()
        if curr_time > reset_time:
            reset_time = curr_time + 30.0
            prev_value = func(*args, **kwargs)

        return prev_value

    return wrapper


def cache_1m(func):
    reset_time: float = -1.0
    prev_value = None

    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal reset_time, prev_value
        curr_time = time.time()
        if curr_time > reset_time:
            reset_time = curr_time + 60.0
            prev_value = func(*args, **kwargs)

        return prev_value

    return wrapper


def cache_5m(func):
    reset_time: float = -1.0
    prev_value = None

    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal reset_time, prev_value
        curr_time = time.time()
        if curr_time > reset_time:
            reset_time = curr_time + 300.0
            prev_value = func(*args, **kwargs)

        return prev_value

    return wrapper


def cache_10m(func):
    reset_time: float = -1.0
    prev_value = None

    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal reset_time, prev_value
        curr_time = time.time()
        if curr_time > reset_time:
            reset_time = curr_time + 600.0
            prev_value = func(*args, **kwargs)

        return prev_value

    return wrapper


def cache_15m(func):
    reset_time: float = -1.0
    prev_value = None

    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal reset_time, prev_value
        curr_time = time.time()
        if curr_time > reset_time:
            reset_time = curr_time + 900.0
            prev_value = func(*args, **kwargs)

        return prev_value

    return wrapper


def cache_30m(func):
    reset_time: float = -1.0
    prev_value = None

    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal reset_time, prev_value
        curr_time = time.time()
        if curr_time > reset_time:
            reset_time = curr_time + 1800.0
            prev_value = func(*args, **kwargs)

        return prev_value

    return wrapper


def cache_1h(func):
    reset_time: float = -1.0
    prev_value = None

    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal reset_time, prev_value
        curr_time = time.time()
        if curr_time > reset_time:
            reset_time = curr_time + 3600.0
            prev_value = func(*args, **kwargs)

        return prev_value

    return wrapper


def cache_2h(func):
    reset_time: float = -1.0
    prev_value = None

    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal reset_time, prev_value
        curr_time = time.time()
        if curr_time > reset_time:
            reset_time = curr_time + 7200.0
            prev_value = func(*args, **kwargs)

        return prev_value

    return wrapper


def cache_3h(func):
    reset_time: float = -1.0
    prev_value = None

    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal reset_time, prev_value
        curr_time = time.time()
        if curr_time > reset_time:
            reset_time = curr_time + 10800.0
            prev_value = func(*args, **kwargs)

        return prev_value

    return wrapper


def cache_4h(func):
    reset_time: float = -1.0
    prev_value = None

    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal reset_time, prev_value
        curr_time = time.time()
        if curr_time > reset_time:
            reset_time = curr_time + 14400.0
            prev_value = func(*args, **kwargs)

        return prev_value

    return wrapper


def cache_6h(func):
    reset_time: float = -1.0
    prev_value = None

    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal reset_time, prev_value
        curr_time = time.time()
        if curr_time > reset_time:
            reset_time = curr_time + 21600.0
            prev_value = func(*args, **kwargs)

        return prev_value

    return wrapper


def cache_12h(func):
    reset_time: float = -1.0
    prev_value = None

    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal reset_time, prev_value
        curr_time = time.time()
        if curr_time > reset_time:
            reset_time = curr_time + 43200.0
            prev_value = func(*args, **kwargs)

        return prev_value

    return wrapper


def cache_1d(func):
    reset_time: float = -1.0
    prev_value = None

    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal reset_time, prev_value
        curr_time = time.time()
        if curr_time > reset_time:
            reset_time = curr_time + 86400.0
            prev_value = func(*args, **kwargs)

        return prev_value

    return wrapper


if __name__ == '__main__':

    @cache_5s
    def now():
        return datetime.datetime.now()


    for _ in range(100):
        print(now())
        time.sleep(0.25)
