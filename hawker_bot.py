import datetime
import json
import logging
import uuid
from typing import List

from telegram import InlineQueryResultArticle
from telegram import InputTextMessageContent
from telegram import ParseMode
from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.ext import InlineQueryHandler
from telegram.ext import MessageHandler
from telegram.ext import Updater

from api_wrappers.onemap import query_onemap
from api_wrappers.postal_code import InvalidZip
from api_wrappers.postal_code import ZipBlank
from api_wrappers.postal_code import ZipNonExistent
from api_wrappers.postal_code import ZipNonNumeric
from api_wrappers.postal_code import fix_zipcode
from api_wrappers.postal_code import locate_zipcode
from api_wrappers.weather import weather_forecast
from api_wrappers.weather import weather_today
from hawkers import DateRange
from hawkers import Hawker
from utils import get_command
from utils import load_hawker_data
from utils import setup_logging

setup_logging(app_name='hawker-bot')

BOT_USERNAMES = {
    'hawker_centre_bot',  # prod
    'hawker_center_bot',  # dev
}

hawkers = load_hawker_data()


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
            effective_message.reply_text(f'Zero results found for "{query}"',
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


def _nearby(lat, lon, effective_message):
    assert isinstance(lat, float), lat
    assert isinstance(lon, float), lon
    results = sorted([(hawker, hawker.distance_from(lat, lon)) for hawker in hawkers], key=lambda x: x[1])
    for result, distance in results[:5]:
        logging.info(f'LAT={lat} LON={lon} DISTANCE={distance} RESULT="{result.name}"')
        text = f'{round(distance)} meters away:  \n' + result.to_markdown()
        effective_message.reply_markdown(text,
                                         disable_notification=True)


def cmd_start(update: Update, context: CallbackContext):
    update.effective_message.reply_text('Hi!',
                                        disable_notification=True)
    update.effective_message.reply_markdown('  \n'.join([
        '*Usage:*',
        '/ABOUT about this bot',
        '/HELP list all commands',
        '/TODAY list hawker centers closed today',
        '/TOMORROW list hawker centers closed tomorrow',
        '/WEEK list hawker centers closed this week',
        '/NEXTWEEK list hawker centers closed next week',
        '/WEATHER 24h weather forecast',
        '/ZIP <zipcode> list hawker centers near a zipcode',
        '/ONEMAP <query> search OneMap.sg',
        'sending a text message will return matching hawker centers',
        'sending a location will return nearby hawker centers',
    ]),
        disable_notification=True)


def cmd_help(update: Update, context: CallbackContext):
    assert isinstance(update, Update)
    assert isinstance(context, CallbackContext)
    update.effective_message.reply_markdown('  \n'.join([
        '*Usage:*',
        "/START start using the bot (you've already done this)",
        '/ABOUT about this bot',
        '/HELP list all commands (this command)',
        '/TODAY list hawker centers closed today',
        '/TOMORROW list hawker centers closed tomorrow',
        '/WEEK list hawker centers closed this week',
        '/NEXTWEEK list hawker centers closed next week',
        '/WEATHER 24h weather forecast',
        '/ZIP <zipcode> list hawker centers near a zipcode',
        '/ONEMAP <query> search OneMap.sg',
        'sending a text message will return matching hawker centers',
        'sending a location will return nearby hawker centers',
    ]),
        disable_notification=True)


def cmd_search(update: Update, context: CallbackContext):
    expected_cmd = '/search'
    query = update.effective_message.text
    assert query.casefold().startswith(expected_cmd.casefold())
    query = query[len(expected_cmd):].strip()

    _search(query, update.effective_message)


def cmd_onemap(update: Update, context: CallbackContext):
    expected_cmd = '/onemap'
    query = update.effective_message.text
    assert query.casefold().startswith(expected_cmd.casefold())
    query = query[len(expected_cmd):].strip()

    if not query:
        update.effective_message.reply_markdown('  \n'.join([
            'No query provided',
            '`/onemap` usage example:',
            '`/onemap lau pa sat`',
        ]),
            disable_notification=True)
        logging.info('QUERY_ONEMAP_BLANK')
        return None

    results = query_onemap(query)
    if not results:
        logging.info(f'QUERY_ONEMAP_NO_RESULTS="{query}"')
        update.effective_message.reply_text('No results',
                                            disable_notification=True)
        return

    update.effective_message.reply_text(f'Displaying top {min(10, len(results))} results from OneMapSG',
                                        disable_notification=True)

    out = []
    for result in results[:10]:
        logging.info(f'QUERY_ONEMAP="{query}" RESULT="{result["SEARCHVAL"]}" ADDRESS="{result["ADDRESS"]}"')
        # update.effective_message.reply_markdown(f'```\n{json.dumps(result, indent=4)}\n```',
        #                                         disable_notification=True)
        out.extend([
            f'*{result["SEARCHVAL"]}*',
            f'[{result["BLK_NO"]} {result["ROAD_NAME"]}, SINGAPORE {result["POSTAL"]}]'
            f'(https://www.google.com/maps/search/?api=1&query={result["LATITUDE"]},{result["LONGITUDE"]})',
            ''
        ])
    update.effective_message.reply_markdown('  \n'.join(out),
                                            disable_web_page_preview=True,
                                            disable_notification=True)


def cmd_about(update: Update, context: CallbackContext):
    update.effective_message.reply_markdown('  \n'.join([
        '[@hawker_centre_bot](https://t.me/hawker_centre_bot)',
        'Github: [averykhoo/hawker-bot](https://github.com/averykhoo/hawker-bot)',
        '',
        'Data sources and APIs:',
        '1. [data.gov.sg: Dates of Hawker Centres Closure](https://data.gov.sg/dataset/dates-of-hawker-centres-closure)',
        '2. [data.gov.sg: Hawker Centres](https://data.gov.sg/dataset/hawker-centres)',
        '3. [data.gov.sg: Weather Forecast](https://data.gov.sg/dataset/weather-forecast)',
        '4. [OneMap API](https://docs.onemap.sg/#onemap-rest-apis)',
        '5. [OneMap Hawker Centres](https://assets.onemap.sg/kml/hawkercentre.kml)',
    ]),
        disable_notification=True,
        disable_web_page_preview=True)


def cmd_zip(update: Update, context: CallbackContext):
    expected_cmd = '/zip'
    query = update.effective_message.text
    assert query.casefold().startswith(expected_cmd.casefold())
    query = query[len(expected_cmd):].strip()

    zip_code = _fix_zip(query, update.effective_message)
    if not zip_code:
        return None

    loc = locate_zipcode(zip_code)
    if not loc:
        logging.info(f'ZIPCODE_NOT_FOUND={zip_code}')
        update.effective_message.reply_markdown('  \n'.join([
            f'Zip code not found: "{zip_code}"',
        ]),
            disable_notification=True)
        return None  # invalid postal code

    # found!
    update.effective_message.reply_text(f'Displaying nearest 5 results to "{loc.address}"',
                                        disable_notification=True)
    logging.info(f'ZIPCODE={zip_code} LAT={loc.latitude} LON={loc.longitude} ADDRESS="{loc.address}"')
    _nearby(loc.latitude, loc.longitude, update.effective_message)


def cmd_weather(update: Update, context: CallbackContext):
    weather_data = weather_today()
    if weather_data:
        fmt_str = '%Y-%m-%dT%H:%M:%S+08:00'
        today = datetime.date.today()

        for period_data in weather_data['periods']:

            time_start = datetime.datetime.strptime(period_data['time']['start'], fmt_str)
            time_end = datetime.datetime.strptime(period_data['time']['end'], fmt_str)

            # stringify the time
            start = time_start.strftime('%I %p').lstrip('0')
            end = time_end.strftime('%I %p').lstrip('0')
            if time_start.date() > today:
                start += ' (tomorrow)'
            if time_end.date() > today:
                end += ' (tomorrow)'

            # send weather as message
            update.effective_message.reply_markdown('  \n'.join([
                f'*Weather forecast from {start} to {end}*',
                'Central: ' + period_data['regions']['central'],
                'North: ' + period_data['regions']['north'],
                'South: ' + period_data['regions']['south'],
                'East: ' + period_data['regions']['east'],
                'West: ' + period_data['regions']['west'],
            ]), disable_notification=True, disable_web_page_preview=True)


def cmd_today(update: Update, context: CallbackContext):
    weather_data = weather_today()
    if weather_data:
        fmt_str = '%Y-%m-%dT%H:%M:%S+08:00'
        # check first item
        idx = 0
        time_start = datetime.datetime.strptime(weather_data['periods'][idx]['time']['start'], fmt_str)
        time_end = datetime.datetime.strptime(weather_data['periods'][idx]['time']['end'], fmt_str)
        assert time_start - datetime.timedelta(hours=1) <= datetime.datetime.now()
        assert datetime.datetime.now() <= time_end + datetime.timedelta(hours=1)

        # if we're 30 minutes to next item, take next item
        if datetime.datetime.now() + datetime.timedelta(hours=0.5) >= time_end:
            idx += 1
            time_start = datetime.datetime.strptime(weather_data['periods'][idx]['time']['start'], fmt_str)
            time_end = datetime.datetime.strptime(weather_data['periods'][idx]['time']['end'], fmt_str)

        # stringify the time
        start = time_start.strftime('%I %p').lstrip('0')
        end = time_end.strftime('%I %p').lstrip('0')
        if time_end.date() > datetime.date.today():
            end += ' (tomorrow)'

        # send weather as message
        update.effective_message.reply_markdown('  \n'.join([
            f'*Weather forecast from {start} to {end}*',
            'Central: ' + weather_data['periods'][idx]['regions']['central'],
            'North: ' + weather_data['periods'][idx]['regions']['north'],
            'South: ' + weather_data['periods'][idx]['regions']['south'],
            'East: ' + weather_data['periods'][idx]['regions']['east'],
            'West: ' + weather_data['periods'][idx]['regions']['west'],
        ]), disable_notification=True, disable_web_page_preview=True)

    # send what's closed today
    _closed(datetime.date.today(), update.effective_message, 'today')


def cmd_tomorrow(update: Update, context: CallbackContext):
    weather_data = weather_forecast()
    if weather_data:
        # make sure we have tomorrow
        tomorrow_str = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        idx = 0
        while weather_data['forecasts'][idx]['date'] < tomorrow_str:
            idx += 1

        # send weather as message
        if datetime.date.today().year < (datetime.date.today() + datetime.timedelta(days=1)).year:
            tomorrow_str = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%d %b %Y').lstrip('0')
        else:
            tomorrow_str = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%d %b').lstrip('0')
        update.effective_message.reply_markdown('  \n'.join([
            f'*Weather forecast for tomorrow ({tomorrow_str}):*',
            weather_data['forecasts'][idx]['forecast'].rstrip('.'),
        ]), disable_notification=True, disable_web_page_preview=True)

    _closed(datetime.date.today() + datetime.timedelta(days=1), update.effective_message, 'tomorrow')


def cmd_this_week(update: Update, context: CallbackContext):
    today = datetime.date.today()
    week_end = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=6)
    _closed(DateRange(today, week_end), update.effective_message, 'this week')


def cmd_next_week(update: Update, context: CallbackContext):
    today = datetime.date.today()
    next_week_start = today + datetime.timedelta(days=7) - datetime.timedelta(days=today.weekday())
    next_week_end = next_week_start + datetime.timedelta(days=6)
    _closed(DateRange(next_week_start, next_week_end), update.effective_message, '_next_ week')


def cmd_unknown(update: Update, context: CallbackContext):
    fuzzy_matches = {
        '/zip':    cmd_zip,
        '/onemap': cmd_onemap,
        '/search': cmd_search,
    }

    query = update.effective_message.text.strip()
    for command, func in fuzzy_matches.items():
        if query.casefold().startswith(command.casefold()):
            logging.info(f'FUZZY_MATCHED_COMMAND="{get_command(query)}" COMMAND="{command}"')
            update.effective_message.reply_markdown(f'Assuming you meant:  \n'
                                                    f'`{query[:len(command)]} {query[len(command):]}`')
            func(update, context)
            break
    else:
        logging.info(f'UNSUPPORTED_COMMAND="{get_command(query)}" QUERY="{query}"')
        update.effective_message.reply_markdown(f'Unsupported command: {get_command(query)}',
                                                disable_notification=True)


def handle_text(update: Update, context: CallbackContext):
    if update.effective_message.via_bot is not None:
        bot_username = update.effective_message.via_bot.username
        if bot_username in BOT_USERNAMES:
            logging.debug(f'VIA_BOT="{bot_username}"')
            return

    query = update.effective_message.text.strip()
    if get_command(query) is not None:
        cmd_unknown(update, context)
        return

    fuzzy_matches = {
        'about':     cmd_about,
        'help':      cmd_help,
        'today':     cmd_today,
        'tomorrow':  cmd_tomorrow,
        'week':      cmd_this_week,
        'nextweek':  cmd_next_week,
        'next_week': cmd_next_week,
        'next week': cmd_next_week,
        'weather':   cmd_weather,
    }

    for fuzzy_match, func in fuzzy_matches.items():
        func_name = fuzzy_match.replace('_', '').replace(' ', '')
        if query.casefold() == fuzzy_match.casefold():
            logging.info(f'FUZZY_MATCHED_COMMAND="{get_command(query)}" COMMAND="/{func_name}"')
            update.effective_message.reply_markdown(f'Assuming you meant:  \n'
                                                    f'`/{func_name}`')
            func(update, context)
            break

    else:
        _search(query, update.effective_message)


def handle_location(update: Update, context: CallbackContext):
    lat = update.effective_message.location.latitude
    lon = update.effective_message.location.longitude

    # outside the SVY21 bounding box
    if not (1.13 >= lat >= 1.47) or not (103.59 >= lon >= 104.07):
        update.effective_message.reply_text(f'You appear to be outside of Singapore, '
                                            f'so this bot will probably not be very useful to you',
                                            disable_notification=True)

    update.effective_message.reply_text(f'Displaying nearest 5 results to your location',
                                        disable_notification=True)
    _nearby(lat, lon, update.effective_message)


def handle_unknown(update: Update, context: CallbackContext):
    logging.warning(f'INVALID_MESSAGE_TYPE MESSAGE_JSON={json.dumps(update.to_dict())}')
    update.effective_message.reply_text('Unable to handle this message type',
                                        disable_notification=True)


def error(update: Update, context: CallbackContext):
    """
    Log Errors caused by Updates.
    """
    logging.warning(f'ERROR="{context.error}" MESSAGE_JSON={json.dumps(update.to_dict())}')
    raise context.error


def log_message(update: Update, context: CallbackContext):
    logging.debug(f'MESSAGE_JSON={json.dumps(update.to_dict())}')


def handle_inline(update: Update, _: CallbackContext) -> None:
    """Handle the inline query."""
    query = update.inline_query.query.strip()
    logging.info(f'INLINE="{query}"')

    results = _search(query)
    if results:
        update.inline_query.answer([
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=hawker.name,
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
                input_message_content=InputTextMessageContent('\n'.join([
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
    with open('secrets.json') as f:
        secrets = json.load(f)

    updater = Updater(secrets['hawker_bot_token'])

    # inline
    updater.dispatcher.add_handler(InlineQueryHandler(handle_inline))

    # log message
    updater.dispatcher.add_handler(MessageHandler(Filters.all, log_message), 1)

    # handle commands
    updater.dispatcher.add_handler(CommandHandler('start', cmd_start), 2)
    updater.dispatcher.add_handler(CommandHandler('help', cmd_help), 2)
    updater.dispatcher.add_handler(CommandHandler('halp', cmd_help), 2)
    updater.dispatcher.add_handler(CommandHandler('about', cmd_about), 2)
    updater.dispatcher.add_handler(CommandHandler('aboot', cmd_about), 2)
    updater.dispatcher.add_handler(CommandHandler('share', cmd_about), 2)
    updater.dispatcher.add_handler(CommandHandler('weather', cmd_weather), 2)

    # by date
    updater.dispatcher.add_handler(CommandHandler('today', cmd_today), 2)
    updater.dispatcher.add_handler(CommandHandler('tomorrow', cmd_tomorrow), 2)
    updater.dispatcher.add_handler(CommandHandler('week', cmd_this_week), 2)
    updater.dispatcher.add_handler(CommandHandler('this', cmd_this_week), 2)
    updater.dispatcher.add_handler(CommandHandler('thisweek', cmd_this_week), 2)
    updater.dispatcher.add_handler(CommandHandler('this_week', cmd_this_week), 2)
    updater.dispatcher.add_handler(CommandHandler('next', cmd_next_week), 2)
    updater.dispatcher.add_handler(CommandHandler('nextweek', cmd_next_week), 2)
    updater.dispatcher.add_handler(CommandHandler('next_week', cmd_next_week), 2)

    # by name / zip code
    updater.dispatcher.add_handler(CommandHandler('search', cmd_search), 2)
    updater.dispatcher.add_handler(CommandHandler('onemap', cmd_onemap), 2)
    updater.dispatcher.add_handler(CommandHandler('zip', cmd_zip), 2)
    updater.dispatcher.add_handler(MessageHandler(Filters.text, handle_text), 2)

    # by location
    updater.dispatcher.add_handler(MessageHandler(Filters.location, handle_location), 2)

    # handle non-commands
    updater.dispatcher.add_handler(MessageHandler(Filters.all, handle_unknown), 2)

    # log all errors
    updater.dispatcher.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT, SIGTERM or SIGABRT.
    # This should be used most of the time, since start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
