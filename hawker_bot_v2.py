import calendar
import datetime
import json
import logging
import re
import uuid
from typing import List
from typing import Optional
from typing import Tuple

from telegram import InlineQueryResultArticle
from telegram import InlineQueryResultVenue
from telegram import InputTextMessageContent
from telegram import ParseMode
from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext import Filters

import config
import utils
from api_wrappers.location import Location
from api_wrappers.onemap_sg import onemap_search
from api_wrappers.postal_code import InvalidZip
from api_wrappers.postal_code import RE_ZIPCODE
from api_wrappers.postal_code import ZipBlank
from api_wrappers.postal_code import ZipNonExistent
from api_wrappers.postal_code import ZipNonNumeric
from api_wrappers.postal_code import fix_zipcode
from api_wrappers.postal_code import locate_zipcode
from api_wrappers.string_formatting import format_date
from api_wrappers.string_formatting import format_datetime
from api_wrappers.weather import Forecast
from api_wrappers.weather import weather_24h_grouped
from api_wrappers.weather import weather_2h
from api_wrappers.weather import weather_4d
from fastbot.fast_bot import FastBot
from fastbot.message import Message
from fastbot.response import Markdown
from fastbot.response import Response
from fastbot.response import Text
from hawkers import DateRange
from hawkers import Hawker

# set up logging appropriately
utils.setup_logging(app_name='hawker-bot')

# disable SSL verification because of the enterprise firewall
utils.no_ssl_verification()

# load hawker center data
hawkers = utils.load_hawker_data()

# create bot
bot = FastBot(config.SECRETS['hawker_center_bot_token (dev)'])


def __fix_zip(query: str) -> Tuple[Optional[str], Optional[Markdown]]:
    try:
        return fix_zipcode(query), None

    except ZipBlank:
        return None, Markdown('  \n'.join([
            'No zip code provided',
            '`/zip` usage example:',
            '`/zip 078881`',
        ]), notification=False)

    except ZipNonNumeric:
        return None, Markdown('  \n'.join([
            f'Invalid zip code provided: "{query}"',
            'Zip code must be digits 0-9',
            '`/zip` usage example:',
            '`/zip 078881`',
        ]), notification=False)

    except ZipNonExistent:
        return None, Markdown('  \n'.join([
            f'Zip code provided cannot possibly exist in Singapore: "{int(query):06d}"',
            '`/zip` usage example:',
            '`/zip 078881`',
        ]), notification=False)


def __search(query: str, threshold=0.6, onemap=False) -> Tuple[List[Hawker], List[Response]]:
    if not query:
        logging.info('QUERY_BLANK')
        return [], [Text('no search query received', notification=False)]

    # try exact match for zip code
    try:
        zip_code = fix_zipcode(query)
        results = [hawker for hawker in hawkers if hawker.addresspostalcode == int(zip_code)]
        if results:
            responses = [Text(f'Displaying zip code match for "{zip_code}"', notification=False)]
            for result in results:
                logging.info(f'QUERY_MATCHED_ZIP="{query}" ZIPCODE={zip_code} RESULT="{result.name}"')
                responses.append(Markdown(result.to_markdown(), notification=False))
            return results, responses
    except InvalidZip:
        pass

    # try to find exact (case-insensitive) match for name
    for hawker in hawkers:
        if hawker.name.casefold() == query.casefold():
            logging.info(f'QUERY_EXACT_MATCH="{query}" RESULT="{hawker.name}"')
            return [hawker], [Text(f'Displaying exact match for "{query}"', notification=False),
                              Markdown(hawker.to_markdown(), notification=False)]

    # run fuzzy search over fields
    results = sorted([(hawker, hawker.text_similarity(query)) for hawker in hawkers], key=lambda x: x[1], reverse=True)
    results = [result for result in results if result[1] > (threshold, 0)]  # filter out bad matches
    if results:
        responses = [Text(f'Displaying top {min(5, len(results))} results for "{query}"', notification=False)]
        for hawker, score in results[:5]:
            logging.info(f'QUERY="{query}" SIMILARITY={hawker.text_similarity(query)} RESULT="{hawker.name}"')
            responses.append(Markdown(hawker.to_markdown(), notification=False))
        return [hawker for hawker, score in results], responses

    logging.info(f'QUERY_NO_RESULTS="{query}"')
    responses = [Text(f'Zero hawker centres match "{query}"', notification=False)]
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


def __closed(date, date_name) -> Markdown:
    lines = [f'Closed {date_name}:']

    for hawker in sorted(hawkers, key=lambda x: x.name):
        if hawker.closed_on_dates(date):
            logging.info(f'CLOSED="{date_name}" DATE="{date}" RESULT="{hawker.name}"')
            lines.append(f'{len(lines)}.  {hawker.name}')

    return Markdown('  \n'.join(lines), notification=False)


def __nearby(loc):
    assert isinstance(loc, Location), loc
    # noinspection PyTypeChecker
    results: List[Hawker] = loc.k_nearest(hawkers, k=-1)
    responses = []
    for result in results[:5]:
        logging.info(f'LAT={loc.latitude} LON={loc.longitude} DISTANCE={loc.distance(result)} RESULT="{result.name}"')
        responses.append(Markdown(f'{round(loc.distance(result))} meters away:  \n{result.to_markdown()}',
                                  notification=False))
    return responses


@bot.command('start', allow_backslash=True, allow_noslash=True)
def cmd_start(message: Message):
    return [Text('Hi!', notification=False),
            Markdown(utils.load_template('start'), notification=False)]


@bot.command('help', allow_backslash=True, allow_noslash=True)
@bot.command('halp', allow_backslash=True, allow_noslash=True)
@bot.command('h', allow_backslash=True, allow_noslash=True)
@bot.command('?', allow_backslash=True, allow_noslash=True)
@bot.command('??', allow_backslash=True, allow_noslash=True)
@bot.command('???', allow_backslash=True, allow_noslash=True)
def cmd_help(message: Message):
    return Markdown(utils.load_template('help'), notification=False)


@bot.command('search', allow_backslash=True, boundary=False, prefix_match=True)
def cmd_search(message: Message, query=None):
    if query is None:
        assert message.match is not None
        query = message.argument

    results, responses = __search(query, onemap=True)
    return responses


@bot.command('onemap', allow_backslash=True, boundary=False, prefix_match=True)
def cmd_onemap(message: Message, query=None):
    if query is None:
        assert message.match is not None
        query = message.argument

    if not query:
        yield Markdown('  \n'.join([
            'No query provided',
            '`/onemap` usage example:',
            '`/onemap lau pa sat`',
        ]), notification=False)
        logging.info('QUERY_ONEMAP_BLANK')
        return None

    results = onemap_search(query)
    if not results:
        logging.info(f'QUERY_ONEMAP_NO_RESULTS="{query}"')
        yield Text('No results',
                   notification=False)
        return

    yield Text(f'Displaying top {min(10, len(results))} results from OneMapSG',
               notification=False)

    out = []
    for result in results[:10]:
        logging.info(f'QUERY_ONEMAP="{query}" RESULT="{result.building_name}" ADDRESS="{result.address}"')
        out.extend([
            f'*{result.building_name}*',
            f'[{result.block_no} {result.road_name}, SINGAPORE {result.zipcode}]'
            f'(https://www.google.com/maps/search/?api=1&query={result.latitude},{result.longitude})',
            ''
        ])
    yield Markdown('  \n'.join(out),
                   web_page_preview=False,
                   notification=False)


@bot.command('about', allow_backslash=True, allow_noslash=True)
@bot.command('share', allow_backslash=True, allow_noslash=True)
def cmd_about(message: Message):
    return Markdown(utils.load_template('about'), notification=False, web_page_preview=False)


@bot.command('zip', argument_pattern=RE_ZIPCODE, allow_backslash=True, boundary=False, prefix_match=True)
@bot.command('zipcode', argument_pattern=RE_ZIPCODE, allow_backslash=True, boundary=False, prefix_match=True)
@bot.command('post', argument_pattern=RE_ZIPCODE, allow_backslash=True, boundary=False, prefix_match=True)
@bot.command('postal', argument_pattern=RE_ZIPCODE, allow_backslash=True, boundary=False, prefix_match=True)
@bot.command('postcode', argument_pattern=RE_ZIPCODE, allow_backslash=True, boundary=False, prefix_match=True)
@bot.command('postalcode', argument_pattern=RE_ZIPCODE, allow_backslash=True, boundary=False, prefix_match=True)
@bot.command('singapore', argument_pattern=re.compile(r'\d{6}'),
             allow_backslash=True, allow_noslash=True, boundary=False, prefix_match=True)
def cmd_zip(message: Message, query=None):
    if query is None:
        assert message.match is not None
        query = message.argument

    zip_code, response = __fix_zip(query)
    if zip_code is None:
        yield response
    else:
        loc = locate_zipcode(zip_code)
        if not loc:
            logging.info(f'ZIPCODE_NOT_FOUND={zip_code}')
            yield Markdown('  \n'.join([
                f'Zip code not found: "{zip_code}"',
            ]), notification=False)
            return None  # invalid postal code

        # noinspection PyTypeChecker
        forecast: Forecast = loc.nearest(weather_2h())
        yield Markdown('  \n'.join([
            f'*Weather near your zipcode ({forecast.name})*',
            f'{format_datetime(forecast.time_start)} to {format_datetime(forecast.time_end)}: {forecast.forecast}',
        ]), notification=False, web_page_preview=False)

        # found!
        yield Text(f'Displaying nearest 5 results to "{loc.address}"', notification=False)
        logging.info(f'ZIPCODE={zip_code} LAT={loc.latitude} LON={loc.longitude} ADDRESS="{loc.address}"')
        yield from __nearby(loc)


@bot.command('rain', allow_backslash=True, allow_noslash=True)
@bot.command('weather', allow_backslash=True, allow_noslash=True)
@bot.command('forecast', allow_backslash=True, allow_noslash=True)
def cmd_weather(message: Message):
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


@bot.command('day', allow_backslash=True, allow_noslash=True)
@bot.command('today', allow_backslash=True, allow_noslash=True)
def cmd_today(message: Message):
    soon = datetime.datetime.now() + datetime.timedelta(minutes=30)
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

    # send what's closed today
    yield __closed(datetime.date.today(), 'today')


@bot.command('tomorrow', allow_backslash=True, allow_noslash=True)
def cmd_tomorrow(message: Message):
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    for detailed_forecast in weather_4d():
        if detailed_forecast.date == tomorrow:
            yield Markdown('  \n'.join([
                f'*Weather forecast for tomorrow, {format_date(tomorrow, print_day=True)}:*',
                detailed_forecast.forecast,
            ]), notification=False, web_page_preview=False)
            break

    yield __closed(datetime.date.today() + datetime.timedelta(days=1), 'tomorrow')


@bot.command('week', allow_backslash=True, allow_noslash=True)
@bot.command('thisweek', allow_backslash=True, allow_noslash=True)
@bot.command('this_week', allow_backslash=True, allow_noslash=True)
def cmd_this_week(message: Message):
    today = datetime.date.today()
    week_end = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=6)
    return __closed(DateRange(today, week_end), 'this week')


@bot.command('next', allow_backslash=True, allow_noslash=True)
@bot.command('nextweek', allow_backslash=True, allow_noslash=True)
@bot.command('next_week', allow_backslash=True, allow_noslash=True)
def cmd_next_week(message: Message):
    today = datetime.date.today()
    next_week_start = today + datetime.timedelta(days=7) - datetime.timedelta(days=today.weekday())
    next_week_end = next_week_start + datetime.timedelta(days=6)
    return __closed(DateRange(next_week_start, next_week_end), '_next_ week')


@bot.command('month', allow_backslash=True, allow_noslash=True)
@bot.command('thismonth', allow_backslash=True, allow_noslash=True)
@bot.command('this_month', allow_backslash=True, allow_noslash=True)
def cmd_this_month(message: Message):
    today = datetime.date.today()
    month_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    return __closed(DateRange(today, month_end), 'this month')


@bot.command('nextmonth', allow_backslash=True, allow_noslash=True)
@bot.command('next_month', allow_backslash=True, allow_noslash=True)
def cmd_next_month(message: Message):
    today = datetime.date.today()
    month_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    next_month_start = month_end + datetime.timedelta(days=1)
    next_month_end = next_month_start.replace(day=calendar.monthrange(next_month_start.year, next_month_start.month)[1])
    return __closed(DateRange(next_month_start, next_month_end), 'next month')


@bot.command('year', allow_backslash=True, allow_noslash=True)
@bot.command('thisyear', allow_backslash=True, allow_noslash=True)
@bot.command('this_year', allow_backslash=True, allow_noslash=True)
def cmd_this_year(message: Message):
    today = datetime.date.today()
    year_end = today.replace(month=12, day=calendar.monthrange(today.year, 12)[1])
    return __closed(DateRange(today, year_end), 'this year')


def cmd_unknown(update: Update, context: CallbackContext):
    # todo: this is terrible
    fuzzy_matches = {
        'postal': ('postal', cmd_zip),  # /postal123456 or /postalcode123456
        'zip':    ('postal', cmd_zip),  # /zip123456 or /zipcode123456
        'onemap': ('onemap', cmd_onemap),  # /onemapclementi
        'search': ('search', cmd_search),  # /searchclementi
    }

    query = update.effective_message.text.strip()
    for command, (func_name, func) in fuzzy_matches.items():
        _command, _query = utils.split_command(query, command)
        if _command is not None:
            logging.info(f'FUZZY_MATCHED_COMMAND="{utils.get_command(query)}" COMMAND="{command}"')
            update.effective_message.reply_markdown(f'Assuming you meant:  \n'
                                                    f'`/{command} {_query}`')
            func(update, context, _query)
            break
    else:
        logging.info(f'UNSUPPORTED_COMMAND="{utils.get_command(query)}" QUERY="{query}"')
        update.effective_message.reply_markdown(f'Unsupported command: {utils.get_command(query)}',
                                                disable_notification=True)


@bot.command('ping')
def cmd_ping(message: Message):
    return Text('pong', notification=False)


@bot.default
def handle_text(message: Message):
    if message.via_bot is not None:
        bot_username = message.via_bot.username
        if bot_username in config.BOT_USERNAMES:
            logging.debug(f'VIA_BOT="{bot_username}"')
            return

    query = message.text
    if utils.get_command(query) is not None:
        cmd_unknown(message.update, message.context)
        return

    fuzzy_matches = {
        'about':      ('about', cmd_about),
        'help':       ('help', cmd_help),
        '?':          ('help', cmd_help),
        '??':         ('help', cmd_help),
        '???':        ('help', cmd_help),
        '/?':         ('help', cmd_help),
        'today':      ('today', cmd_today),
        'tomorrow':   ('tomorrow', cmd_tomorrow),
        'week':       ('week', cmd_this_week),
        'thisweek':   ('week', cmd_this_week),
        'this week':  ('week', cmd_this_week),
        'next':       ('nextweek', cmd_next_week),
        'nextweek':   ('nextweek', cmd_next_week),
        'next_week':  ('nextweek', cmd_next_week),
        'next week':  ('nextweek', cmd_next_week),
        'month':      ('month', cmd_this_month),
        'thismonth':  ('month', cmd_this_month),
        'this month': ('month', cmd_this_month),
        'nextmonth':  ('nextmonth', cmd_next_month),
        'next_month': ('nextmonth', cmd_next_month),
        'next month': ('nextmonth', cmd_next_month),
        'weather':    ('weather', cmd_weather),
        'forecast':   ('weather', cmd_weather),
        'rain':       ('weather', cmd_weather),
    }

    if query.casefold() in fuzzy_matches:
        func_name, func = fuzzy_matches[query.casefold()]
        logging.info(f'FUZZY_MATCHED_COMMAND="{utils.get_command(query)}" COMMAND="/{func_name}"')
        yield Markdown(f'Assuming you meant:  \n'
                       f'`/{func_name}`',
                       notification=False)
        func(message)

    else:
        results, responses = __search(query, onemap=True)
        yield from responses


def handle_location(update: Update, context: CallbackContext):
    loc = Location(latitude=update.effective_message.location.latitude,
                   longitude=update.effective_message.location.longitude,
                   )

    # lat = update.effective_message.location.latitude
    # lon = update.effective_message.location.longitude

    # outside the SVY21 bounding box
    if not loc.within_singapore():
        update.effective_message.reply_text(f'You appear to be outside of Singapore, '
                                            f'so this bot will probably not be very useful to you',
                                            disable_notification=True)

    # noinspection PyTypeChecker
    forecast: Forecast = loc.nearest(weather_2h())
    update.effective_message.reply_markdown('  \n'.join([
        f'*Weather near you ({forecast.name})*',
        f'{format_datetime(forecast.time_start)} to {format_datetime(forecast.time_end)}: {forecast.forecast}',
    ]), disable_notification=True, disable_web_page_preview=True)

    update.effective_message.reply_text(f'Displaying nearest 5 results to your location',
                                        disable_notification=True)

    message = Message(update, context)
    responses = __nearby(loc)
    for response in responses:
        response.send(message)


def handle_unknown(update: Update, context: CallbackContext):
    logging.warning(f'INVALID_MESSAGE_TYPE MESSAGE_JSON={json.dumps(update.to_dict())}')

    # return Text('Unable to handle this message type', notification=False)
    update.effective_message.reply_text('Unable to handle this message type',
                                        disable_notification=True)


def error(update: Update, context: CallbackContext):
    """
    Log Errors caused by Updates.
    """
    logging.warning(f'ERROR="{context.error}" MESSAGE_JSON={json.dumps(update.to_dict() if update else None)}')
    raise context.error


def log_message(update: Update, context: CallbackContext):
    logging.debug(f'MESSAGE_JSON={json.dumps(update.to_dict())}')


def handle_inline(update: Update, _: CallbackContext) -> None:
    """Handle the inline query."""
    query = update.inline_query.query.strip()
    logging.info(f'INLINE="{query}"')

    results, responses = __search(query)
    if results:
        update.inline_query.answer([
            InlineQueryResultVenue(
                id=str(uuid.uuid4()),
                latitude=hawker.latitude,
                longitude=hawker.longitude,
                title=hawker.name,
                address=hawker.address_myenv,
                input_message_content=InputTextMessageContent(hawker.to_markdown(),
                                                              parse_mode=ParseMode.MARKDOWN
                                                              ),
            ) for hawker in results[:5]
        ])
    elif query:
        update.inline_query.answer([
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title='No results found',
                input_message_content=InputTextMessageContent('  \n'.join([
                    'No hawker centres match the provided search term:',
                    f'`{query}`',
                ]),
                    parse_mode=ParseMode.MARKDOWN,
                ),
            )
        ])
    else:
        update.inline_query.answer([
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title='Enter search query',
                input_message_content=InputTextMessageContent('  \n'.join([
                    '*Inline mode usage example:*',
                    '`@hawker_centre_bot clementi`',
                ]),
                    parse_mode=ParseMode.MARKDOWN,
                ),
            )
        ])


if __name__ == '__main__':
    # log message
    bot.add_message_handler(log_message, Filters.all, 1)

    # inline handler
    bot.add_inline_handler(handle_inline)

    # by location
    bot.add_message_handler(handle_location, Filters.location)

    # handle non-commands
    bot.add_message_handler(handle_unknown, Filters.all)

    # log all errors
    bot.add_error_handler(error)

    # run the Bot
    bot.run_forever()
