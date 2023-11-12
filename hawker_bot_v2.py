import calendar
import datetime
import logging
import re
import time
from pathlib import Path
from pprint import pformat
from typing import Any
from typing import Generator
from typing import List
from typing import Optional
from typing import Tuple

import requests

import config
import utils
from api_wrappers.data_gov_sg_v2.weather import Forecast
from api_wrappers.data_gov_sg_v2.weather import weather_24h_grouped
from api_wrappers.data_gov_sg_v2.weather import weather_2h
from api_wrappers.data_gov_sg_v2.weather import weather_4d
from api_wrappers.location import Location
from api_wrappers.onemap_sg_v2 import onemap_search
from api_wrappers.postal_code import InvalidZip
from api_wrappers.postal_code import RE_ZIPCODE
from api_wrappers.postal_code import ZipBlank
from api_wrappers.postal_code import ZipNonExistent
from api_wrappers.postal_code import ZipNonNumeric
from api_wrappers.postal_code import fix_zipcode
from api_wrappers.postal_code import locate_zipcode
from api_wrappers.string_formatting import format_date
from api_wrappers.string_formatting import format_datetime
from fastbot import FastBot
from fastbot import Markdown
from fastbot import Message
from fastbot import Response
from fastbot import Text
from fastbot.inline import InlineArticle
from fastbot.inline import InlineQuery
from fastbot.inline import InlineVenue
from fastbot.response import Animation
from hawkers import DateRange
from hawkers import Hawker

# noinspection PyUnresolvedReferences
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

# set up logging appropriately
utils.setup_logging(app_name='hawker-bot-v2')

# # disable SSL verification
# utils.no_ssl_verification()

# load hawker center data
hawker_data = utils.load_hawker_data()

# create bot
bot = FastBot(config.SECRETS['hawker_centre_bot_token'])


def __fix_zip(query: str) -> Tuple[Optional[str], Optional[Markdown]]:
    try:
        return fix_zipcode(query), None

    except ZipBlank:
        return None, Markdown('  \n'.join([
            'No postal code provided',
            '`/postal` usage example:',
            '`/postal 078881`',
        ]), notification=False)

    except ZipNonNumeric:
        return None, Markdown('  \n'.join([
            f'Invalid postal code provided: "{query}"',
            'Postal code must be digits 0-9',
            '`/postal` usage example:',
            '`/postal 078881`',
        ]), notification=False)

    except ZipNonExistent:
        return None, Markdown('  \n'.join([
            f'Postal code provided cannot possibly exist in Singapore: "{int(query):06d}"',
            '`/postal` usage example:',
            '`/postal 078881`',
        ]), notification=False)


def __search(query: str, threshold=0.6, onemap=False, num_results=3) -> Tuple[List[Hawker], List[Response]]:
    if not query:
        logging.info('QUERY_BLANK')
        return [], [Text('no search query received', notification=False)]

    # try exact matched for zip code
    try:
        zip_code = fix_zipcode(query)
        results = [hawker for hawker in hawker_data if hawker.addresspostalcode == int(zip_code)]
        if results:
            responses = [Text(f'Displaying postal code matched for "{zip_code}"', notification=False)]
            for result in results:
                logging.info(f'QUERY_MATCHED_ZIP="{query}" ZIPCODE={zip_code} RESULT="{result.name}"')
                responses.append(Markdown(result.to_markdown(), notification=False))
            return results, responses
    except InvalidZip:
        pass

    # try to find exact (case-insensitive) matched for name
    for hawker in hawker_data:
        if hawker.name.casefold() == query.casefold():
            logging.info(f'QUERY_EXACT_MATCH="{query}" RESULT="{hawker.name}"')
            return [hawker], [Text(f'Displaying exact matched for "{query}"', notification=False),
                              Markdown(hawker.to_markdown(), notification=False)]

    # run fuzzy search over fields
    results = sorted([(hawker, hawker.text_similarity(query)) for hawker in hawker_data], key=lambda x: x[1],
                     reverse=True)
    results = [result for result in results if result[1] > (threshold, 0)]  # filter out bad matches
    if results:
        responses = [Text(f'Displaying top {min(num_results, len(results))} results for "{query}"', notification=False)]
        for hawker, score in results[:num_results]:
            logging.info(f'QUERY="{query}" SIMILARITY={hawker.text_similarity(query)} RESULT="{hawker.name}"')
            responses.append(Markdown(hawker.to_markdown(), notification=False))
        return [hawker for hawker, score in results], responses

    logging.info(f'QUERY_NO_RESULTS="{query}"')
    responses = [Text(f'Zero hawker centres matched "{query}"', notification=False)]
    if not onemap:
        return [], responses

    # if we have don't have to reply, exit early
    results = onemap_search(query)

    # if we have to reply, try to be a bit more intelligent
    if not results:
        logging.info(f'QUERY_ONEMAP_NO_RESULTS="{query}"')
        responses.append(Text(f'Zero matches from OneMap.sg for {query}', notification=False))
        return [], responses

    responses.append(Text(f'Displaying top {min(5, len(results))} results from OneMapSG', notification=False))

    lines = []
    for result in results[:5]:
        logging.info(f'QUERY_ONEMAP="{query}" RESULT="{result.building_name}" ADDRESS="{result.address}"')
        lines.extend([
            f'*{result.building_name}*',
            f'[{result.block_no} {result.road_name}, SINGAPORE {result.zipcode}]'
            f'(https://www.google.com/maps/search/?api=1&query={result.latitude},{result.longitude})',
            ''
        ])
    responses.append(Markdown('  \n'.join(lines), notification=False, web_page_preview=False))
    return [], responses


def __closed(date, date_name) -> Generator[Markdown, Any, None]:
    lines = [f'Closed {date_name}:']
    idx = 0
    yielded = False

    for hawker in sorted(hawker_data, key=lambda x: x.name):
        if hawker.closed_on_dates(date):
            idx += 1
            logging.info(f'CLOSED="{date_name}" DATE="{date}" RESULT="{hawker.name}"')
            lines.append(f'{idx}.  {hawker.name}')
            if sum(map(len, lines)) > 3200:
                yield Markdown('  \n'.join(lines), notification=False)
                yielded = True
                lines.clear()
    if len(lines) > 1 or yielded:
        yield Markdown('  \n'.join(lines), notification=False)
    else:
        logging.info(f'ZERO_CLOSED="{date_name}" DATE="{date}"')
        yield Markdown(f'No records of any closures {date_name}')


def __nearby(loc, num_results=3):
    assert isinstance(loc, Location), loc
    # noinspection PyTypeChecker
    results: List[Hawker] = loc.k_nearest(hawker_data, k=-1)
    responses = []
    for result in results[:num_results]:
        logging.info(f'LAT={loc.latitude} LON={loc.longitude} DISTANCE={loc.distance(result)} RESULT="{result.name}"')
        responses.append(Markdown(f'{round(loc.distance(result))} meters away:  \n{result.to_markdown()}',
                                  notification=False))
    return responses


def _diff_hawkers(original_list, new_list):
    original_data = {hawker.name: hawker for hawker in original_list}
    new_hawkers = set()
    for hawker in new_list:
        if hawker.name not in original_data:
            yield Text(f'new hawker:\n{pformat(hawker.name)}')
        elif hawker != original_data[hawker.name]:
            before = dict()
            after = dict()
            new_json = hawker.to_json()
            for key, val in original_data[hawker.name].to_json().items():
                if new_json[key] != val:
                    before[key] = val
                    after[key] = new_json[key]
            yield Markdown(f'{hawker.name} changed from:\n```{pformat(before)}```\nto:\n```{pformat(after)}```')
        new_hawkers.add(hawker.name)
    for hawker_name, hawker in original_data.items():
        if hawker_name not in new_hawkers:
            yield Text(f'removed hawker:\n{pformat(hawker.name)}')


@bot.keyword('hi')
@bot.keyword('hello')
@bot.keyword('start')
@bot.command('start', prefix_match=True)
@bot.chat_created
@bot.new_chat_members
def cmd_start():
    return [Text('Hi!', notification=False),
            Markdown(utils.load_template('start'), notification=False)]


@bot.keyword('thank you')
@bot.command('thanks', noslash=True)
def cmd_thanks():
    return Animation(Path("data/moana-you're-welcome.gif"))


@bot.regex(re.compile(r'(?P<command>[/\\]?\?+)'))
@bot.command('halp', noslash=True)
@bot.command('h', noslash=True)
@bot.command('help', noslash=True)  # canonical name, because bottom decorator is applied first
def cmd_help():
    return Markdown(utils.load_template('help'), notification=False)


@bot.command('search', noslash=True, boundary=False, prefix_match=True)
@bot.command('hawker', noslash=True, boundary=False, prefix_match=True)
def cmd_search(message: Message):
    assert message.matched is not None
    query = message.argument

    results, responses = __search(query, onemap=True)
    return responses


@bot.command('where', noslash=True, boundary=False, prefix_match=True)
@bot.command('onemap', noslash=True, boundary=False, prefix_match=True)
def cmd_onemap(message: Message):
    assert message.matched is not None
    query = message.argument

    if not query:
        logging.info('QUERY_ONEMAP_BLANK')
        yield Markdown('  \n'.join([
            'No query provided',
            '`/onemap` usage example:',
            '`/onemap lau pa sat`',
        ]), notification=False)
        return

    results = onemap_search(query)
    if not results:
        logging.info(f'QUERY_ONEMAP_NO_RESULTS="{query}"')
        yield Text(f'No results for {query}',
                   notification=False)
        return

    logging.info(f'QUERY_ONEMAP="{query}" NUM_RESULTS={len(results)}')
    yield Text(f'Displaying top {min(10, len(results))} results from OneMapSG',
               notification=False)

    out = []
    for result in results[:10]:
        logging.info(f'QUERY_ONEMAP="{query}" RESULT="{result.building_name}" ADDRESS="{result.address}"')
        out.extend([
            f'*{result.building_name}*',
            f'[{result.address_without_building}]'
            f'(https://www.google.com/maps/search/?api=1&query={result.latitude},{result.longitude})',
            ''
        ])
    yield Markdown('  \n'.join(out),
                   web_page_preview=False,
                   notification=False)


@bot.command('share', noslash=True)
@bot.command('about', noslash=True)
def cmd_about():
    return Markdown(utils.load_template('about'), notification=False, web_page_preview=False)


@bot.regex(re.compile(rf'[/\\]?(?P<argument>{RE_ZIPCODE.pattern})', flags=re.I | re.U))
@bot.command('zipcode', boundary=False, prefix_match=True)
@bot.command('zip', boundary=False, prefix_match=True)
@bot.command('postcode', boundary=False, prefix_match=True)
@bot.command('post', boundary=False, prefix_match=True)
@bot.command('postalcode', boundary=False, prefix_match=True)
@bot.command('postal', boundary=False, prefix_match=True)
def cmd_zip(message: Message):
    assert message.matched is not None
    query = message.argument

    zip_code, response = __fix_zip(query)
    if zip_code is None:
        if response is not None:
            yield response
        return

    loc = locate_zipcode(zip_code)
    if not loc:
        logging.info(f'ZIPCODE_NOT_FOUND={zip_code}')
        yield Markdown(f'Postal code does not exist in Singapore: "{zip_code}"', notification=False)
        return

    try:
        # noinspection PyTypeChecker
        forecast: Forecast = loc.nearest(weather_2h())
        yield Markdown('  \n'.join([
            f'*Weather near your postal code ({forecast.name} Area)*',
            f'{format_datetime(forecast.time_start)} to {format_datetime(forecast.time_end)}: {forecast.forecast}',
        ]), notification=False, web_page_preview=False)

    except KeyError:
        yield Markdown('The `data.gov.sg` weather API is not responding')
    except Exception:
        yield Markdown('Not able to check the weather right now')

    # found!
    logging.info(f'ZIPCODE={zip_code} LAT={loc.latitude} LON={loc.longitude} ADDRESS="{loc.address}"')
    yield Text(f'Displaying nearest 3 results to "{loc.address}"', notification=False)
    yield from __nearby(loc)


@bot.command('nearby', noslash=True, prefix_match=True)
@bot.command('near', noslash=True, prefix_match=True)
def cmd_near(message: Message):
    assert message.matched is not None
    query = message.argument

    if not query:
        yield Markdown('  \n'.join([
            'No query provided',
            '`/near` usage example:',
            '`/near MacPherson MRT Station`',
        ]), notification=False)
        logging.info('QUERY_NEAR_BLANK')
        return

    if query.lower() in {'me', 'myself', 'here', 'home'}:
        yield Text('You seem to be looking for hawker_data near your current location. '
                   'If so, please send your location.')

    results = onemap_search(query)
    if not results:
        logging.info(f'QUERY_NEAR_NO_RESULTS="{query}"')
        yield Text(f'No results for {query}', notification=False)

        if re.search(r'\b(hawker|food)\s*(centre|center)\b', query, flags=re.I) is not None:
            query = ' '.join(re.sub(r'\b(hawker|food)\s*(centre|center)\b', ' ', query, flags=re.I).split())

        elif re.search(r'\bblo?c?k\s*([1-9]\d\d?)\b', query, flags=re.I) is not None:
            query = ' '.join(re.sub(r'\bblo?c?k\s*([1-9]\d\d?)\b', r'\1', query, flags=re.I).split())

        else:
            return

        results = onemap_search(query)
        if not results:
            logging.info(f'QUERY_NEAR_RETRY_NO_RESULTS="{query}"')
            return

    address = re.sub(r'\b(' + '|'.join(map(re.escape, query.split())) + r')\b',
                     r'*\1*',
                     results[0].address,
                     flags=re.I | re.U)
    logging.info(f'NEARBY={query} LAT={results[0].latitude} LON={results[0].longitude} '
                 f'ADDRESS="{results[0].address}" MARKDOWN="{address}')
    yield Markdown(f'Displaying nearest 3 results to "{address}"', notification=False)
    yield from __nearby(results[0])


@bot.keyword('weather forecast')
@bot.command('rain', noslash=True)
@bot.command('forecast', noslash=True)
@bot.command('weather', noslash=True)
def cmd_weather():
    try:
        weather_data = weather_24h_grouped()
        for time_start, time_end in sorted(weather_data.keys()):
            start_str = format_datetime(time_start, use_deictic_temporal_pronouns=True)
            end_str = format_datetime(time_end, use_deictic_temporal_pronouns=True)

            # format message
            lines = [f'*Weather forecast from {start_str} to {end_str}*']
            for forecast in weather_data[time_start, time_end]:
                lines.append(f'{forecast.name}: {forecast.forecast}')

            # send message
            yield Markdown('  \n'.join(lines), notification=False, web_page_preview=False)

    except KeyError:
        yield Markdown('The `data.gov.sg` weather API is not responding')
    except Exception:
        yield Markdown('Not able to check the weather right now')


@bot.keyword('list all')
@bot.keyword('list everything')
@bot.command('everything', noslash=True)
@bot.command('all', noslash=True)
@bot.command('list', noslash=True)
def cmd_list():
    lines = []
    idx = 0

    logging.info(f'LIST_ALL')
    for hawker in sorted(hawker_data, key=lambda x: x.name):
        idx += 1
        lines.append(f'{idx}.  {hawker.name}')
        if sum(map(len, lines)) > 3200:
            yield Markdown('  \n'.join(lines), notification=False)
            lines.clear()
    if lines:
        yield Markdown('  \n'.join(lines), notification=False)


@bot.command('tdy', noslash=True)
@bot.command('day', noslash=True)
@bot.command('today', noslash=True)
def cmd_today():
    soon = datetime.datetime.now() + datetime.timedelta(minutes=30)
    # noinspection PyBroadException
    try:
        for (time_start, time_end), forecasts in weather_24h_grouped().items():
            if time_start <= soon < time_end:
                start_str = format_datetime(time_start, use_deictic_temporal_pronouns=True)
                end_str = format_datetime(time_end, use_deictic_temporal_pronouns=True)

                # format message
                lines = [f'*Weather forecast from {start_str} to {end_str}*']
                for forecast in forecasts:
                    lines.append(f'{forecast.name}: {forecast.forecast}')

                # send message
                yield Markdown('  \n'.join(lines), notification=False, web_page_preview=False)
                break
    except KeyError:
        yield Markdown('The `data.gov.sg` weather API is not responding')
    except Exception:
        yield Markdown('Not able to check the weather right now')

    # send what's closed today
    yield from __closed(datetime.date.today(), 'today')


@bot.command('tmr', noslash=True)
@bot.command('tomorrow', noslash=True)
def cmd_tomorrow():
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    # noinspection PyBroadException
    try:
        for _forecast in weather_4d():
            if _forecast.date == tomorrow:
                yield Markdown('  \n'.join([
                    f'*Weather forecast for tomorrow, {format_date(tomorrow, print_day=True)}:*',
                    _forecast.forecast,
                ]), notification=False, web_page_preview=False)
                break

    except KeyError:
        yield Markdown('The `data.gov.sg` weather API is not responding')
    except Exception:
        yield Markdown('Not able to check the weather right now')

    yield from __closed(datetime.date.today() + datetime.timedelta(days=1), 'tomorrow')


@bot.command('yesterday', noslash=True)
def cmd_yesterday():
    yesterday = datetime.date.today() - datetime.timedelta(days=1)

    data_dir = Path('data/dates-of-hawker-centres-closure')
    paths = sorted(str(path) for path in data_dir.glob('dates-of-hawker-centres-closure*.csv'))
    timestamp_str = re.findall(r'\d{4}-\d{2}-\d{2}--\d{2}-\d{2}-\d{2}', paths[-1])[0]
    timestamp = datetime.datetime.strptime(timestamp_str, '%Y-%m-%d--%H-%M-%S')
    if timestamp.date() >= yesterday:
        # note that %#d is a windows-only format specifier, for linux, use %-d
        yield Markdown(f'NEA last modified the hawker closure list at around '
                       f'{yesterday.strftime("%#I:%M%p")} on {yesterday.strftime("%#d %b %Y")}, '
                       f"'and may have done housekeeping on yesterday's closure dates'", notification=False)

    yield from __closed(yesterday, 'yesterday')


@bot.keyword('this week')
@bot.command('this_week', noslash=True)
@bot.command('thisweek', noslash=True)
@bot.command('week', noslash=True)
def cmd_this_week():
    today = datetime.date.today()
    week_end = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=6)
    yield from __closed(DateRange(today, week_end), 'this week')


@bot.keyword('next week')
@bot.command('next_week', noslash=True)
@bot.command('nxt', noslash=True)
@bot.command('next', noslash=True)
@bot.command('nextweek', noslash=True)
def cmd_next_week():
    today = datetime.date.today()
    next_week_start = today + datetime.timedelta(days=7) - datetime.timedelta(days=today.weekday())
    next_week_end = next_week_start + datetime.timedelta(days=6)
    yield from __closed(DateRange(next_week_start, next_week_end), '_next_ week')


@bot.keyword('this month')
@bot.command('this_month', noslash=True)
@bot.command('thismonth', noslash=True)
@bot.command('month', noslash=True)
def cmd_this_month():
    today = datetime.date.today()
    month_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    yield from __closed(DateRange(today, month_end), 'this month')


@bot.keyword('next month')
@bot.command('next_month', noslash=True)
@bot.command('nextmonth', noslash=True)
def cmd_next_month():
    today = datetime.date.today()
    month_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    next_month_start = month_end + datetime.timedelta(days=1)
    next_month_end = next_month_start.replace(day=calendar.monthrange(next_month_start.year, next_month_start.month)[1])
    yield from __closed(DateRange(next_month_start, next_month_end), 'next month')


@bot.keyword('this year')
@bot.command('this_year', noslash=True)
@bot.command('thisyear', noslash=True)
@bot.command('year', noslash=True)
def cmd_this_year():
    today = datetime.date.today()
    year_end = today.replace(month=12, day=calendar.monthrange(today.year, 12)[1])
    yield from __closed(DateRange(today, year_end), 'this year')


@bot.keyword('next year')
@bot.command('next_year', noslash=True)
@bot.command('nextyear', noslash=True)
def cmd_next_year():
    year_start = datetime.date(year=datetime.date.today().year + 1, month=1, day=1)
    year_end = year_start.replace(month=12, day=calendar.monthrange(year_start.year, 12)[1])
    yield from __closed(DateRange(year_start, year_end), 'next year')


@bot.command('ping')
def cmd_ping():
    yield Text(f'pong {datetime.datetime.now()}', notification=False)


# @bot.command('markdown', prefix_match=True)
# def cmd_near(message: Message):
#     assert message.matched is not None
#     yield Markdown(message.argument, notification=False)


@bot.command('update')
def cmd_update():
    global hawker_data
    prev_data = hawker_data[:]

    hawker_data = utils.load_hawker_data()
    yield Text(f'updated to dataset published on {utils.last_loaded_date.strftime("%Y-%m-%d %H:%M:%S")}',
               notification=False)

    yield from _diff_hawkers(prev_data, hawker_data)


@bot.command('diff')
@bot.command('delta')
@bot.command('changed')
def cmd_diff():
    data_dir = Path('data/dates-of-hawker-centres-closure')
    paths = sorted(str(path) for path in data_dir.glob('dates-of-hawker-centres-closure*.csv'))
    yield Text(f'most recent dataset: {paths[-1]}')
    yield from _diff_hawkers(utils.load_hawker_data(paths[-2]), utils.load_hawker_data(paths[-1]))


@bot.command('shutdown', prefix_match=True)
def cmd_shutdown(message: Message):
    assert message.matched is not None
    time.sleep(5)  # avoid brute-force attacks
    if message.argument == config.SECRETS['hawker_centre_bot_token']:
        yield Text('shutting down...')
        bot.shutdown()
    else:
        logging.info(f'got incorrect token "{message.argument}", not shutting down')
        yield Text('incorrect bot token provided, will not shut down')


@bot.default
def handle_text(message: Message):
    # ignore stuff sent via my own inline bot
    if message.via_bot is not None:
        bot_username = message.via_bot.username
        if bot_username in config.BOT_USERNAMES:
            logging.debug(f'VIA_BOT="{bot_username}"')
            return

    # looks like a command
    if utils.get_command(message.text) is not None:
        logging.info(f'UNSUPPORTED_COMMAND="{utils.get_command(message.text)}" QUERY="{message.text}"')
        yield Markdown(f'Unsupported command:  \n{message.text}', notification=False)
        return

    # reuse the nearby handler
    message.matched = re.fullmatch(r'(?P<argument>.*)', message.text)
    yield from cmd_near(message)


@bot.location
def handle_location(message: Message):
    loc = Location(latitude=message.update.effective_message.location.latitude,
                   longitude=message.update.effective_message.location.longitude,
                   )

    # outside the SVY21 bounding box
    if not loc.within_singapore():
        yield Text('You appear to be outside of Singapore, so this bot will probably not be very useful to you',
                   notification=False)

    try:
        # noinspection PyTypeChecker
        forecast: Forecast = loc.nearest(weather_2h())
        yield Markdown(f'*Weather near you ({forecast.name})*  \n'
                       f'{format_datetime(forecast.time_start)} to {format_datetime(forecast.time_end)}: '
                       f'{forecast.forecast}',
                       notification=False,
                       web_page_preview=False)

    except KeyError:
        yield Markdown('The `data.gov.sg` weather API is not responding')
    except Exception:
        yield Markdown('Not able to check the weather right now')

    yield Text('Displaying nearest 3 results to your location', notification=False)
    yield from __nearby(loc)


@bot.unrecognized
def handle_unrecognized(message: Message):
    logging.warning(f'INVALID_MESSAGE_TYPE MESSAGE_JSON={message.to_json()}')

    # return Text('Unable to handle this message type', notification=False)
    yield Text('Unable to handle this message type', notification=False)


@bot.error
def error(message: Message):
    logging.warning(f'ERROR="{message.context.error}" MESSAGE_JSON={message.to_json()}')
    # raise message.context.error


@bot.logger
def log_message(message: Message):
    logging.info(f'MESSAGE_JSON={message.to_json()}')


@bot.inline
def handle_inline(message: InlineQuery) -> None:
    query = message.text
    logging.info(f'INLINE="{query}"')

    results, responses = __search(query)
    if results:
        for hawker in results[:5]:
            yield InlineVenue(title=hawker.name,
                              content=hawker.to_markdown(),
                              latitude=hawker.latitude,
                              longitude=hawker.longitude,
                              address=hawker.address_myenv,
                              )
    elif query:
        yield InlineArticle(title='No results found',
                            content=f'No hawker centres matched the provided search term:  \n`{query}`',
                            )
    else:
        yield InlineArticle(title='Enter search query',
                            content='*Inline mode usage example:*  \n`@hawker_centre_bot clementi`',
                            )


if __name__ == '__main__':
    bot.run_forever(lambda: list(cmd_update()))
