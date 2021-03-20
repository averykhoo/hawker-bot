import datetime
import json
import logging
import sys
import warnings
from pathlib import Path

import pandas as pd
from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import Updater

from data.hawker_data import locate_zip
from hawkers import DateRange
from hawkers import Hawker

timestamp = datetime.datetime.now().strftime('%Y-%m-%d--%H-%M-%S')
log_path = Path(f'logs/hawker-bot--{timestamp}.log').resolve()
log_path.parent.mkdir(parents=True, exist_ok=True)

# setup logging format
log_formatter = logging.Formatter('%(asctime)s  '
                                  '%(levelname)-8s '
                                  '[%(name)s|%(processName)s|%(threadName)s|%(module)s|%(funcName)s]\t'
                                  '%(message)s')

# set global log level to DEBUG (most verbose possible)
logging.getLogger().setLevel(logging.DEBUG)

# create stderr handler at INFO
logging_stdout_handler = logging.StreamHandler(sys.stderr)
logging_stdout_handler.setFormatter(log_formatter)
logging_stdout_handler.setLevel(logging.INFO)
logging.getLogger().addHandler(logging_stdout_handler)

# create file handler at DEBUG
logging_file_handler = logging.FileHandler(log_path)
logging_file_handler.setFormatter(log_formatter)
logging_file_handler.setLevel(logging.INFO)  # set to DEBUG if there's enough disk space
logging.getLogger().addHandler(logging_file_handler)

ZIP_PREFIXES = {  # https://en.wikipedia.org/wiki/Postal_codes_in_Singapore#Postal_districts
    '01', '02', '03', '04', '05', '06',  # Raffles Place, Cecil, Marina, People's Park
    '07', '08',  # Anson, Tanjong Pagar
    '14', '15', '16',  # Bukit Merah, Queenstown, Tiong Bahru
    '09', '10',  # Telok Blangah, Harbourfront
    '11', '12', '13',  # Pasir Panjang, Hong Leong Garden, Clementi New Town
    '17',  # High Street, Beach Road (part)
    '18', '19',  # Middle Road, Golden Mile
    '20', '21',  # Little India, Farrer Park, Jalan Besar, Lavender
    '22', '23',  # Orchard, Cairnhill, River Valley
    '24', '25', '26', '27',  # Ardmore, Bukit Timah, Holland Road, Tanglin
    '28', '29', '30',  # Watten Estate, Novena, Thomson
    '31', '32', '33',  # Balestier, Toa Payoh, Serangoon
    '34', '35', '36', '37',  # Macpherson, Braddell, Potong Pasir, Bidadari
    '38', '39', '40', '41',  # Geylang, Eunos, Aljunied
    '42', '43', '44', '45',  # Katong, Joo Chiat, Amber Road
    '46', '47', '48',  # Bedok, Upper East Coast, Eastwood, Kew Drive
    '49', '50', '81',  # Loyang, Changi
    '51', '52',  # Simei, Tampines, Pasir Ris
    '53', '54', '55', '82',  # Serangoon Garden, Hougang, Punggol
    '56', '57',  # Bishan, Ang Mo Kio
    '58', '59',  # Upper Bukit Timah, Clementi Park, Ulu Pandan
    '60', '61', '62', '63', '64',  # Penjuru, Jurong, Pioneer, Tuas
    '65', '66', '67', '68',  # Hillview, Dairy Farm, Bukit Panjang, Choa Chu Kang
    '69', '70', '71',  # Lim Chu Kang, Tengah
    '72', '73',  # Kranji, Woodgrove, Woodlands
    '77', '78',  # Upper Thomson, Springleaf
    '75', '76',  # Yishun, Sembawang, Senoko
    '79', '80',  # Seletar
}


def _fix_zip(query, effective_message=None):
    if not query:
        if effective_message is not None:
            effective_message.reply_markdown('  \n'.join([
                'No zip code provided',
                '`/zip` usage example:',
                '`/zip 078881`',
            ]))
            logging.info('ZIPCODE_BLANK')
        return None

    if not query.isdigit():
        if effective_message is not None:
            effective_message.reply_markdown('  \n'.join([
                f'Invalid zip code provided: "{query}"',
                'Zip code must be digits 0-9',
                '`/zip` usage example:',
                '`/zip 078881`',
            ]))
            logging.info(f'ZIPCODE_NON_NUMERIC="{query}"')
        return None  # text

    # sanity check zip code
    zip_code = f'{int(query):06d}'
    if len(zip_code) > 6 or zip_code[:2] not in ZIP_PREFIXES:
        if effective_message is not None:
            effective_message.reply_markdown('  \n'.join([
                f'Zip code provided cannot possibly exist in Singapore: "{zip_code}"',
                '`/zip` usage example:',
                '`/zip 078881`',
            ]))
            logging.info(f'ZIPCODE_NON_EXISTENT="{query}"')
        return None  # invalid postal code

    return zip_code


def _search(query, effective_message, threshold=0.6):
    if not query:
        effective_message.reply_text('no search query received')
        logging.info('QUERY_BLANK')
        return

    # try exact match for zip code
    zip_code = _fix_zip(query)
    if zip_code:
        results = [hawker for hawker in hawkers if hawker.addresspostalcode == int(zip_code)]
        if results:
            effective_message.reply_text(f'Displaying zip code match for "{zip_code}"')
            for result in results:
                logging.info(f'QUERY_MATCHED_ZIP="{query}" ZIPCODE={zip_code} RESULT="{result.name}"')
                effective_message.reply_markdown(result.to_markdown())
            return

    results = sorted([(hawker, hawker.text_similarity(query)) for hawker in hawkers], key=lambda x: x[1], reverse=True)
    results = [result for result in results if result[1] > (threshold, 0)]  # filter out bad matches
    if results:
        effective_message.reply_text(f'Displaying top {min(5, len(results))} results for "{query}"')
        for hawker, score in results[:5]:
            logging.info(f'QUERY="{query}" SIMILARITY={hawker.text_similarity(query)} RESULT="{hawker.name}"')
            effective_message.reply_markdown(hawker.to_markdown())

    else:
        logging.info(f'QUERY_NO_RESULTS="{query}"')
        effective_message.reply_text(f'Zero results found for "{query}"')


def _closed(date, effective_message, date_name):
    lines = [f'Closed {date_name}:']

    for hawker in sorted(hawkers, key=lambda x: x.name):
        if hawker.closed_on_dates(date):
            logging.info(f'CLOSED="{date_name}" DATE="{date}" RESULT="{hawker.name}"')
            lines.append(f'{len(lines)}.  {hawker.name}')
            continue

    effective_message.reply_markdown('  \n'.join(lines))


def _nearby(lat, lon, effective_message):
    assert isinstance(lat, float), lat
    assert isinstance(lon, float), lon
    results = sorted([(hawker, hawker.distance_from(lat, lon)) for hawker in hawkers], key=lambda x: x[1])
    for result, distance in results[:5]:
        logging.info(f'LAT={lat} LON={lon} DISTANCE={distance} RESULT="{result.name}"')
        text = f'{round(distance)} meters away:  \n' + result.to_markdown()
        effective_message.reply_markdown(text)


def cmd_start(update: Update, context: CallbackContext):
    update.effective_message.reply_text('Hi!')
    update.effective_message.reply_markdown('  \n'.join([
        '*Usage:*',
        '/HELP list all commands',
        '/TODAY list hawker centers closed today',
        '/TOMORROW list hawker centers closed tomorrow',
        '/WEEK list hawker centers closed this week',
        '/NEXTWEEK list hawker centers closed next week',
        '/ZIP <zipcode> list hawker centers near a zipcode',
        'sending a text message will return matching hawker centers',
        'sending a location will return nearby hawker centers',
    ]))


def cmd_help(update: Update, context: CallbackContext):
    assert isinstance(update, Update)
    assert isinstance(context, CallbackContext)
    update.effective_message.reply_markdown('  \n'.join([
        '*Usage:*',
        "/START start using the bot (you've already done this)",
        '/HELP list all commands (this command)',
        '/TODAY list hawker centers closed today',
        '/TOMORROW list hawker centers closed tomorrow',
        '/WEEK list hawker centers closed this week',
        '/NEXTWEEK list hawker centers closed next week',
        '/ZIP <zipcode> list hawker centers near a zipcode',
        'sending a text message will return matching hawker centers',
        'sending a location will return nearby hawker centers',
    ]))


def cmd_search(update: Update, context: CallbackContext):
    expected_cmd = '/search'
    query = update.effective_message.text
    assert query.lower().startswith(expected_cmd)
    query = query[len(expected_cmd):].strip()

    _search(query, update.effective_message)


def cmd_share(update: Update, context: CallbackContext):
    update.effective_message.reply_markdown('[HawkerBot](https://t.me/hawker_centre_bot)')


def cmd_about(update: Update, context: CallbackContext):
    update.effective_message.reply_markdown('  \n'.join([
        '[HawkerBot](https://t.me/hawker_centre_bot)',
        'Github: [averykhoo/hawker-bot](https://github.com/averykhoo/hawker-bot)',
    ]))


def cmd_zip(update: Update, context: CallbackContext):
    expected_cmd = '/zip'
    query = update.effective_message.text
    assert query.lower().startswith(expected_cmd)
    query = query[len(expected_cmd):].strip()

    zip_code = _fix_zip(query, update.effective_message)
    if not zip_code:
        return None

    loc = locate_zip(zip_code)
    if not loc:
        logging.info(f'ZIPCODE_NOT_FOUND={zip_code}')
        update.effective_message.reply_markdown('  \n'.join([
            f'Zip code not found: "{zip_code}"',
        ]))
        return None  # invalid postal code

    # found!
    lat, lon, address = loc
    update.effective_message.reply_text(f'Displaying nearest 5 results to "{address}"')
    logging.info(f'ZIPCODE={zip_code} LAT={lat} LON={lon} ADDRESS="{address}"')
    _nearby(lat, lon, update.effective_message)


def cmd_today(update: Update, context: CallbackContext):
    _closed(datetime.date.today(), update.effective_message, 'today')


def cmd_tomorrow(update: Update, context: CallbackContext):
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


def handle_text(update: Update, context: CallbackContext):
    query = update.effective_message.text.strip()
    _search(query, update.effective_message)


def location(update: Update, context: CallbackContext):
    lat = update.effective_message.location.latitude
    lon = update.effective_message.location.longitude
    update.effective_message.reply_text(f'Displaying nearest 5 results to your location')
    _nearby(lat, lon, update.effective_message)


def ignore(update: Update, context: CallbackContext):
    logging.warning('INVALID_MESSAGE_TYPE')
    warnings.warn(f'{update}')
    update.effective_message.reply_text('Unable to handle this message type')


def error(update: Update, context: CallbackContext):
    """
    Log Errors caused by Updates.
    """
    logging.warning(f'ERROR="{context.error}"')
    warnings.warn(f'{update}')
    raise context.error


def log_message(update: Update, context: CallbackContext):
    logging.debug(f'MESSAGE_JSON={json.dumps(update.to_dict())}')


if __name__ == '__main__':
    hawkers = []
    df = pd.read_csv('data/hawker-centres/hawker-centres.csv')
    for i, row in df.iterrows():
        hawkers.append(Hawker.from_row(row))

    # # filter to useful hawker centers
    # hawkers = [hawker for hawker in hawkers if hawker.no_of_food_stalls > 0]

    df = pd.read_csv('data/dates-of-hawker-centres-closure/dates-of-hawker-centres-closure--2021-03-18--22-52-07.csv')
    for i, row in df.iterrows():
        for hawker in hawkers:
            if hawker.name == row['name']:
                hawker.add_cleaning_periods(row)
                break
        else:
            logging.warning(f'could not find {row["name"]}')

    with open('secrets.json') as f:
        secrets = json.load(f)

    updater = Updater(secrets['hawker_bot_token'])

    # log message
    updater.dispatcher.add_handler(MessageHandler(Filters.all, log_message), 1)

    # handle commands
    updater.dispatcher.add_handler(CommandHandler('start', cmd_start), 2)
    updater.dispatcher.add_handler(CommandHandler('help', cmd_help), 2)
    updater.dispatcher.add_handler(CommandHandler('share', cmd_share), 2)
    updater.dispatcher.add_handler(CommandHandler('about', cmd_about), 2)

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
    updater.dispatcher.add_handler(CommandHandler('zip', cmd_zip), 2)
    updater.dispatcher.add_handler(MessageHandler(Filters.text, handle_text), 2)

    # by location
    updater.dispatcher.add_handler(MessageHandler(Filters.location, location), 2)

    # handle non-commands
    updater.dispatcher.add_handler(MessageHandler(Filters.all, ignore), 2)

    # log all errors
    updater.dispatcher.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT, SIGTERM or SIGABRT.
    # This should be used most of the time, since start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
