import datetime
from typing import Dict


def pprint_time(timestamp):
    if not isinstance(timestamp, (datetime.time, datetime.datetime)):
        raise TypeError(timestamp)
    if timestamp.minute:
        return timestamp.strftime('%I:%m%p').lstrip('0').lower()
    else:
        return timestamp.strftime('%I%p').lstrip('0').lower()


def pprint_date(timestamp, use_deictic_temporal_pronouns=False, print_day=False):
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


def pprint_datetime(timestamp, use_deictic_temporal_pronouns=False, print_day=False):
    if pprint_date(timestamp, use_deictic_temporal_pronouns=True) == 'today':
        return pprint_time(timestamp)

    day_str = timestamp.strftime(' (%a)') if print_day else ''
    date_str = pprint_date(timestamp, use_deictic_temporal_pronouns=use_deictic_temporal_pronouns)

    if use_deictic_temporal_pronouns:
        return f'{pprint_time(timestamp)} {date_str}' + day_str

    else:
        return f'{pprint_time(timestamp)}, {date_str}' + day_str
