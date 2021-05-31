import calendar
import datetime
import json
import logging
import uuid
from typing import List

from telegram import InlineQueryResultArticle
from telegram import InlineQueryResultVenue
from telegram import InputTextMessageContent
from telegram import ParseMode
from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext import Filters

import utils
from api_wrappers.location import Location
from api_wrappers.onemap_sg import onemap_search
from api_wrappers.postal_code import InvalidZip
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
from fastbot.response import Markdown
from fastbot.response import Text
from hawkers import DateRange
from hawkers import Hawker

utils.setup_logging(app_name='hawker-bot')
utils.no_ssl_verification()

with open('secrets.json') as f:
    secrets = json.load(f)

bot = FastBot(secrets['hawker_center_bot_token (dev)'])

BOT_USERNAMES = {
    'hawker_centre_bot',  # prod
    'hawker_center_bot',  # dev
}

hawkers = utils.load_hawker_data()


def _fix_zip(query, effective_message=None):
    try:
        return fix_zipcode(query)

    except ZipBlank:
        if effective_message is not None:
            effective_message.reply_markdown('  \n'.join([
                'No zip code provided',
                '`/zip` usage example:',
                '`/zip 078881`',
            ]), disable_notification=True)

    except ZipNonNumeric:
        if effective_message is not None:
            effective_message.reply_markdown('  \n'.join([
                f'Invalid zip code provided: "{query}"',
                'Zip code must be digits 0-9',
                '`/zip` usage example:',
                '`/zip 078881`',
            ]), disable_notification=True)

    except ZipNonExistent:
        if effective_message is not None:
            effective_message.reply_markdown('  \n'.join([
                f'Zip code provided cannot possibly exist in Singapore: "{int(query):06d}"',
                '`/zip` usage example:',
                '`/zip 078881`',
            ]), disable_notification=True)


def _search(query, effective_message=None, threshold=0.6) -> List[Hawker]:
    if not query:
        if effective_message is not None:
            effective_message.reply_text('no search query received',
                                         disable_notification=True)
        logging.info('QUERY_BLANK')
        return []

    # try exact match for zip code
    try:
        zip_code = fix_zipcode(query)
        results = [hawker for hawker in hawkers if hawker.addresspostalcode == int(zip_code)]
        if results:
            if effective_message is not None:
                effective_message.reply_text(f'Displaying zip code match for "{zip_code}"',
                                             disable_notification=True)
            for result in results:
                logging.info(f'QUERY_MATCHED_ZIP="{query}" ZIPCODE={zip_code} RESULT="{result.name}"')
                if effective_message is not None:
                    effective_message.reply_markdown(result.to_markdown(),
                                                     disable_notification=True)
            return results
    except InvalidZip:
        pass

    # try to find exact (case-insensitive) match for name
    for hawker in hawkers:
        if hawker.name.casefold() == query.casefold():
            logging.info(f'QUERY_EXACT_MATCH="{query}" RESULT="{hawker.name}"')
            if effective_message is not None:
                effective_message.reply_text(f'Displaying exact match for "{query}"',
                                             disable_notification=True)
                effective_message.reply_markdown(hawker.to_markdown(),
                                                 disable_notification=True)
            return [hawker]

    # run fuzzy search over fields
    results = sorted([(hawker, hawker.text_similarity(query)) for hawker in hawkers], key=lambda x: x[1], reverse=True)
    results = [result for result in results if result[1] > (threshold, 0)]  # filter out bad matches
    if results:
        if effective_message is not None:
            effective_message.reply_text(f'Displaying top {min(5, len(results))} results for "{query}"',
                                         disable_notification=True)
        for hawker, score in results[:5]:
            logging.info(f'QUERY="{query}" SIMILARITY={hawker.text_similarity(query)} RESULT="{hawker.name}"')
            if effective_message is not None:
                effective_message.reply_markdown(hawker.to_markdown(),
                                                 disable_notification=True)
        return [hawker for hawker, score in results]

    else:
        logging.info(f'QUERY_NO_RESULTS="{query}"')
        if effective_message is not None:
            effective_message.reply_text(f'Zero hawker centres match "{query}"',
                                         disable_notification=True)
        # return []

    # if we have don't have to reply, exit early
    if effective_message is None:
        return []
    results = onemap_search(query)

    # if we have to reply, try to be a bit more intelligent
    if not results:
        logging.info(f'QUERY_ONEMAP_NO_RESULTS="{query}"')
        effective_message.reply_text(f'Zero matches from OneMap.sg for {query}',
                                     disable_notification=True)
        return []

    effective_message.reply_text(f'Displaying top {min(5, len(results))} results from OneMapSG',
                                 disable_notification=True)

    lines = []
    for result in results[:5]:
        logging.info(f'QUERY_ONEMAP="{query}" RESULT="{result.building_name}" ADDRESS="{result.address}"')
        lines.extend([
            f'*{result.building_name}*',
            f'[{result.block_no} {result.road_name}, SINGAPORE {result.zipcode}]'
            f'(https://www.google.com/maps/search/?api=1&query={result.latitude},{result.longitude})',
            ''
        ])
    effective_message.reply_markdown('  \n'.join(lines),
                                     disable_web_page_preview=True,
                                     disable_notification=True)
    return []


def _closed(date, effective_message, date_name):
    lines = [f'Closed {date_name}:']

    for hawker in sorted(hawkers, key=lambda x: x.name):
        if hawker.closed_on_dates(date):
            logging.info(f'CLOSED="{date_name}" DATE="{date}" RESULT="{hawker.name}"')
            lines.append(f'{len(lines)}.  {hawker.name}')

    effective_message.reply_markdown('  \n'.join(lines),
                                     disable_notification=True)


def _nearby(loc, effective_message):
    assert isinstance(loc, Location), loc
    # noinspection PyTypeChecker
    results: List[Hawker] = loc.k_nearest(hawkers, k=-1)
    for result in results[:5]:
        logging.info(f'LAT={loc.latitude} LON={loc.longitude} DISTANCE={loc.distance(result)} RESULT="{result.name}"')
        text = f'{round(loc.distance(result))} meters away:  \n' + result.to_markdown()
        effective_message.reply_markdown(text,
                                         disable_notification=True)


@bot.router.command('start', allow_backslash=True, allow_noslash=True)
def cmd_start(update: Update, context: CallbackContext):
    update.effective_message.reply_text('Hi!',
                                        disable_notification=True)
    update.effective_message.reply_markdown(utils.load_template('start'),
                                            disable_notification=True)


@bot.router.command('help', allow_backslash=True, allow_noslash=True)
@bot.router.command('halp', allow_backslash=True, allow_noslash=True)
@bot.router.command('h', allow_backslash=True, allow_noslash=True)
@bot.router.command('?', allow_backslash=True, allow_noslash=True)
@bot.router.command('??', allow_backslash=True, allow_noslash=True)
@bot.router.command('???', allow_backslash=True, allow_noslash=True)
def cmd_help(update: Update, context: CallbackContext):
    return Markdown(utils.load_template('help'), notification=False)


@bot.router.command('search')
def cmd_search(update: Update, context: CallbackContext):
    query = update.effective_message.text
    command, query = utils.split_command(query, 'search')
    assert command is not None

    _search(query, update.effective_message)


@bot.router.command('onemap')
def cmd_onemap(update: Update, context: CallbackContext):
    query = update.effective_message.text
    command, query = utils.split_command(query, 'onemap')
    assert command is not None

    if not query:
        update.effective_message.reply_markdown('  \n'.join([
            'No query provided',
            '`/onemap` usage example:',
            '`/onemap lau pa sat`',
        ]), disable_notification=True)
        logging.info('QUERY_ONEMAP_BLANK')
        return None

    results = onemap_search(query)
    if not results:
        logging.info(f'QUERY_ONEMAP_NO_RESULTS="{query}"')
        update.effective_message.reply_text('No results',
                                            disable_notification=True)
        return

    update.effective_message.reply_text(f'Displaying top {min(10, len(results))} results from OneMapSG',
                                        disable_notification=True)

    out = []
    for result in results[:10]:
        logging.info(f'QUERY_ONEMAP="{query}" RESULT="{result.building_name}" ADDRESS="{result.address}"')
        out.extend([
            f'*{result.building_name}*',
            f'[{result.block_no} {result.road_name}, SINGAPORE {result.zipcode}]'
            f'(https://www.google.com/maps/search/?api=1&query={result.latitude},{result.longitude})',
            ''
        ])
    update.effective_message.reply_markdown('  \n'.join(out),
                                            disable_web_page_preview=True,
                                            disable_notification=True)


@bot.router.command('about', allow_backslash=True, allow_noslash=True)
@bot.router.command('share', allow_backslash=True, allow_noslash=True)
def cmd_about(update: Update, context: CallbackContext):
    return Markdown(utils.load_template('about'), notification=False, web_page_preview=False)


@bot.router.command('zip', allow_backslash=True, allow_noslash=True)
@bot.router.command('zipcode', allow_backslash=True, allow_noslash=True)
@bot.router.command('post', allow_backslash=True, allow_noslash=True)
@bot.router.command('postal', allow_backslash=True, allow_noslash=True)
@bot.router.command('postcode', allow_backslash=True, allow_noslash=True)
@bot.router.command('postalcode', allow_backslash=True, allow_noslash=True)
def cmd_zip(update: Update, context: CallbackContext):
    query = update.effective_message.text
    command, query = utils.split_command(query)
    assert command is not None

    zip_code = _fix_zip(query, update.effective_message)
    if not zip_code:
        return None

    loc = locate_zipcode(zip_code)
    if not loc:
        logging.info(f'ZIPCODE_NOT_FOUND={zip_code}')
        update.effective_message.reply_markdown('  \n'.join([
            f'Zip code not found: "{zip_code}"',
        ]), disable_notification=True)
        return None  # invalid postal code

    # noinspection PyTypeChecker
    forecast: Forecast = loc.nearest(weather_2h())
    update.effective_message.reply_markdown('  \n'.join([
        f'*Weather near your zipcode ({forecast.name})*',
        f'{format_datetime(forecast.time_start)} to {format_datetime(forecast.time_end)}: {forecast.forecast}',
    ]), disable_notification=True, disable_web_page_preview=True)

    # found!
    update.effective_message.reply_text(f'Displaying nearest 5 results to "{loc.address}"',
                                        disable_notification=True)
    logging.info(f'ZIPCODE={zip_code} LAT={loc.latitude} LON={loc.longitude} ADDRESS="{loc.address}"')
    _nearby(loc, update.effective_message)


@bot.router.command('rain', allow_backslash=True, allow_noslash=True)
@bot.router.command('weather', allow_backslash=True, allow_noslash=True)
@bot.router.command('forecast', allow_backslash=True, allow_noslash=True)
def cmd_weather(update: Update, context: CallbackContext):
    weather_data = weather_24h_grouped()
    for time_start, time_end in sorted(weather_data.keys()):
        start_str = format_datetime(time_start, use_deictic_temporal_pronouns=True)
        end_str = format_datetime(time_end, use_deictic_temporal_pronouns=True)

        # format message
        lines = [f'*Weather forecast from {start_str} to {end_str}*']
        for forecast in weather_data[time_start, time_end]:
            lines.append(f'{forecast.name}: {forecast.forecast}')

        # send message
        update.effective_message.reply_markdown('  \n'.join(lines),
                                                disable_notification=True,
                                                disable_web_page_preview=True)


@bot.router.command('day', allow_backslash=True, allow_noslash=True)
@bot.router.command('today', allow_backslash=True, allow_noslash=True)
def cmd_today(update: Update, context: CallbackContext):
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
            update.effective_message.reply_markdown('  \n'.join(lines),
                                                    disable_notification=True,
                                                    disable_web_page_preview=True)
            break

    # send what's closed today
    _closed(datetime.date.today(), update.effective_message, 'today')


@bot.router.command('tomorrow', allow_backslash=True, allow_noslash=True)
def cmd_tomorrow(update: Update, context: CallbackContext):
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    for detailed_forecast in weather_4d():
        if detailed_forecast.date == tomorrow:
            update.effective_message.reply_markdown('  \n'.join([
                f'*Weather forecast for tomorrow, {format_date(tomorrow, print_day=True)}:*',
                detailed_forecast.forecast,
            ]), disable_notification=True, disable_web_page_preview=True)
            break

    _closed(datetime.date.today() + datetime.timedelta(days=1), update.effective_message, 'tomorrow')


@bot.router.command('week', allow_backslash=True, allow_noslash=True)
@bot.router.command('thisweek', allow_backslash=True, allow_noslash=True)
@bot.router.command('this_week', allow_backslash=True, allow_noslash=True)
def cmd_this_week(update: Update, context: CallbackContext):
    today = datetime.date.today()
    week_end = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=6)
    _closed(DateRange(today, week_end), update.effective_message, 'this week')


@bot.router.command('next', allow_backslash=True, allow_noslash=True)
@bot.router.command('nextweek', allow_backslash=True, allow_noslash=True)
@bot.router.command('next_week', allow_backslash=True, allow_noslash=True)
def cmd_next_week(update: Update, context: CallbackContext):
    today = datetime.date.today()
    next_week_start = today + datetime.timedelta(days=7) - datetime.timedelta(days=today.weekday())
    next_week_end = next_week_start + datetime.timedelta(days=6)
    _closed(DateRange(next_week_start, next_week_end), update.effective_message, '_next_ week')


@bot.router.command('month', allow_backslash=True, allow_noslash=True)
@bot.router.command('thismonth', allow_backslash=True, allow_noslash=True)
@bot.router.command('this_month', allow_backslash=True, allow_noslash=True)
def cmd_this_month(update: Update, context: CallbackContext):
    today = datetime.date.today()
    month_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    _closed(DateRange(today, month_end), update.effective_message, 'this month')


@bot.router.command('nextmonth', allow_backslash=True, allow_noslash=True)
@bot.router.command('next_month', allow_backslash=True, allow_noslash=True)
def cmd_next_month(update: Update, context: CallbackContext):
    today = datetime.date.today()
    month_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    next_month_start = month_end + datetime.timedelta(days=1)
    next_month_end = next_month_start.replace(day=calendar.monthrange(next_month_start.year, next_month_start.month)[1])
    _closed(DateRange(next_month_start, next_month_end), update.effective_message, 'next month')


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
                                                    f'`{query[:len(command)]} {query[len(command):]}`')
            func(update, context)
            break
    else:
        logging.info(f'UNSUPPORTED_COMMAND="{utils.get_command(query)}" QUERY="{query}"')
        update.effective_message.reply_markdown(f'Unsupported command: {utils.get_command(query)}',
                                                disable_notification=True)


@bot.router.command('ping')
def cmd_ping(update: Update, context: CallbackContext):
    return Text('pong', notification=False)


def handle_text(update: Update, context: CallbackContext):
    if update.effective_message.via_bot is not None:
        bot_username = update.effective_message.via_bot.username
        if bot_username in BOT_USERNAMES:
            logging.debug(f'VIA_BOT="{bot_username}"')
            return

    query = update.effective_message.text.strip()
    if utils.get_command(query) is not None:
        cmd_unknown(update, context)
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
        update.effective_message.reply_markdown(f'Assuming you meant:  \n'
                                                f'`/{func_name}`')
        func(update, context)

    else:
        _search(query, update.effective_message)


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
    _nearby(loc, update.effective_message)


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
    # raise context.error


def log_message(update: Update, context: CallbackContext):
    logging.debug(f'MESSAGE_JSON={json.dumps(update.to_dict())}')


def handle_inline(update: Update, _: CallbackContext) -> None:
    """Handle the inline query."""
    query = update.inline_query.query.strip()
    logging.info(f'INLINE="{query}"')

    results = _search(query)
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

    # by name / zip code
    bot.add_message_handler(handle_text, Filters.text)
    # by location
    bot.add_message_handler(handle_location, Filters.location)
    # handle non-commands
    bot.add_message_handler(handle_unknown, Filters.all)

    # log all errors
    bot.add_error_handler(error)

    # run the Bot
    bot.run_forever()
