import datetime
import math
from typing import Dict
from typing import Union


def format_bytes(num_bytes: int) -> str:
    # handle negatives
    if num_bytes < 0:
        minus = '-'
    else:
        minus = ''
    num_bytes = abs(num_bytes)

    # ±1 byte (singular form)
    if num_bytes == 1:
        return f'{minus}1 Byte'

    # determine unit
    unit = 0
    while unit < 8 and num_bytes > 999:
        num_bytes /= 1024.0
        unit += 1
    unit = ['Bytes', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB'][unit]

    # exact or float
    if num_bytes % 1:
        return f'{minus}{num_bytes:,.2f} {unit}'
    else:
        return f'{minus}{num_bytes:,.0f} {unit}'


def format_seconds(num_seconds: Union[int, float]) -> str:
    """
    string formatting
    note that the days in a month is kinda fuzzy
    kind of takes leap years into account, but as a result the years are fuzzy
    """

    # handle negatives
    if num_seconds < 0:
        minus = '-'
    else:
        minus = ''
    num_seconds = abs(num_seconds)

    # zero (not compatible with decimals below)
    if num_seconds == 0:
        return '0 seconds'

    # 1 or more seconds
    if num_seconds >= 1:
        unit = 0
        denominators = [60.0, 60.0, 24.0, 7.0, 365.25 / 84.0, 12.0, 10.0]
        while unit < 6 and num_seconds > denominators[unit] * 0.9:
            num_seconds /= denominators[unit]
            unit += 1
        unit_str = ['seconds', 'minutes', 'hours', 'days', 'weeks', 'months', 'years', 'decades'][unit]

        # singular form
        if num_seconds == 1:
            unit_str = unit_str[:-1]

        # exact or float
        if num_seconds % 1:
            return f'{minus}{num_seconds:,.2f} {unit_str}'
        else:
            return f'{minus}{num_seconds:,.0f} {unit_str}'

    # fractions of a second (ms, μs, ns)
    else:
        unit = 0
        while unit < 3 and num_seconds < 0.9:
            num_seconds *= 1000
            unit += 1
        unit = ['seconds', 'milliseconds', 'microseconds', 'nanoseconds'][unit]

        # singular form
        if num_seconds == 1:
            unit = unit[:-1]

        # exact or float
        if num_seconds % 1 and num_seconds > 1:
            return f'{minus}{num_seconds:,.2f} {unit}'
        elif num_seconds % 1:
            # noinspection PyStringFormat
            num_seconds = f'{{N:,.{1 - int(math.floor(math.log10(abs(num_seconds))))}f}}'.format(N=num_seconds)
            return f'{minus}{num_seconds} {unit}'
        else:
            return f'{minus}{num_seconds:,.0f} {unit}'


def format_time(timestamp) -> str:
    if not isinstance(timestamp, (datetime.time, datetime.datetime)):
        raise TypeError(timestamp)
    if timestamp.minute:
        return timestamp.strftime('%I:%m%p').lstrip('0').lower()
    else:
        return timestamp.strftime('%I%p').lstrip('0').lower()


def format_date(timestamp, use_deictic_temporal_pronouns=False, print_day=False) -> str:
    if not isinstance(timestamp, (datetime.date, datetime.datetime)):
        raise TypeError(timestamp)

    today = datetime.date.today()
    day_str = timestamp.strftime(' (%a)') if print_day else ''

    if use_deictic_temporal_pronouns:
        # The Cambridge Grammar of the English Language (2017); chapter 2 section 17 (page 68)
        # see also chapter 17 section 10.1.2
        deictic_temporal_pronouns: Dict[str, datetime.date] = {
            'yesterday': today - datetime.timedelta(days=1),
            'today':     today,
            'tomorrow':  today + datetime.timedelta(days=1),
        }
        for pronoun, date in deictic_temporal_pronouns.items():
            if date.year == timestamp.year and date.month == timestamp.month and date.day == timestamp.day:
                return pronoun + day_str

    if today.year == timestamp.year:
        return timestamp.strftime('%d %b').lstrip('0') + day_str
    else:
        return timestamp.strftime('%d %b %Y').lstrip('0') + day_str


def format_datetime(timestamp, use_deictic_temporal_pronouns=False, print_day=False) -> str:
    if format_date(timestamp, use_deictic_temporal_pronouns=True) == 'today':
        return format_time(timestamp)

    day_str = timestamp.strftime(' (%a)') if print_day else ''
    date_str = format_date(timestamp, use_deictic_temporal_pronouns=use_deictic_temporal_pronouns)

    if use_deictic_temporal_pronouns:
        return f'{format_time(timestamp)} {date_str}' + day_str

    else:
        return f'{format_time(timestamp)}, {date_str}' + day_str
