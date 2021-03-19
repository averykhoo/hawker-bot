import datetime
import json
import logging

import pandas as pd
from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import Updater

# Enable logging
from hawkers import DateRange
from hawkers import Hawker

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


def _search(query, effective_message):
    """
    Send a message when the command /help is issued.
    """
    query = effective_message.text.strip()

    if not query:
        effective_message.reply_text('no search query received')
        return

    if query.isdigit():
        for hawker in hawkers:
            if hawker.addresspostalcode == int(query):
                effective_message.reply_text(f'Displaying zip code match for "{query}"')
                effective_message.reply_markdown(hawker.to_markdown())
                return

    effective_message.reply_text(f'Displaying top 5 results for "{query}"')
    results = sorted(hawkers, key=lambda x: x.text_similarity(query), reverse=True)
    print(query)
    for hawker in results[:5]:
        print(hawker.text_similarity(query), hawker.name)
        effective_message.reply_markdown(hawker.to_markdown())


def _closed(date, effective_message, date_name):
    lines = [f'Closed {date_name}:']

    for hawker in hawkers:
        if hawker.closed_on_dates(date):
            lines.append(f'{len(lines)}.  {hawker.name}')
            continue

    effective_message.reply_markdown('  \n'.join(lines))


def cmd_start(update: Update, context: CallbackContext):
    """
    Send a message when the command /start is issued.
    """
    assert isinstance(update, Update)
    assert isinstance(context, CallbackContext)
    update.effective_message.reply_text('Hi!')


def cmd_help(update: Update, context: CallbackContext):
    """
    Send a message when the command /help is issued.
    """
    update.effective_message.reply_markdown('  \n'.join([
        '*Usage:*',
        '/START start using the bot (you\'ve already done this)',
        '/HELP this command',
        '/TODAY list hawker centers closed today',
        '/TOMORROW list hawker centers closed tomorrow',
        '/WEEK list hawker centers closed this week',
        '/NEXTWEEK list hawker centers closed next week',
        'sending a text message will return matching hawker centers',
        'sending a location will return nearby hawker centers',
    ]))


def cmd_search(update: Update, context: CallbackContext):
    """
    Send a message when the command /help is issued.
    """
    expected_cmd = '/search'
    query = update.effective_message.text
    assert query.lower().startswith(expected_cmd)
    query = query[len(expected_cmd):].strip()

    _search(query, update.effective_message)


def cmd_share(update: Update, context: CallbackContext):
    """
    Send a message when the command /help is issued.
    """
    update.effective_message.reply_markdown('[HawkerBot](t.me/hawker_centre_bot)')


def cmd_today(update: Update, context: CallbackContext):
    _closed(datetime.date.today(), update.effective_message, 'today')


def cmd_tomorrow(update: Update, context: CallbackContext):
    _closed(datetime.date.today() + datetime.timedelta(days=1), update.effective_message, 'tomorrow')


def cmd_this_week(update: Update, context: CallbackContext):
    today = datetime.date.today()
    week_start = today - datetime.timedelta(days=today.weekday())
    week_end = week_start + datetime.timedelta(days=6)
    _closed(DateRange(week_start, week_end), update.effective_message, 'this week')


def cmd_next_week(update: Update, context: CallbackContext):
    today = datetime.date.today()
    next_week_start = today + datetime.timedelta(days=7) - datetime.timedelta(days=today.weekday())
    next_week_end = next_week_start + datetime.timedelta(days=6)
    next_week = DateRange(next_week_start, next_week_end)
    _closed(DateRange(next_week_start, next_week_end), update.effective_message, '_next_ week')


def handle_text(update: Update, context: CallbackContext):
    """
    Send a message when the command /help is issued.
    """
    query = update.effective_message.text.strip()
    _search(query, update.effective_message)


def location(update: Update, context: CallbackContext):
    update.effective_message.reply_text(f'Displaying nearest 5 results to your location')

    lat = update.effective_message.location.latitude
    lon = update.effective_message.location.longitude

    print(lat, lon)
    results = sorted(hawkers, key=lambda x: x.distance_from(lat, lon))
    for result in results[:5]:
        print(result.distance_from(lat, lon), result.name)
        text = f'{int(result.distance_from(lat, lon))} meters away:  \n' + result.to_markdown()
        update.effective_message.reply_markdown(text)


def ignore(update: Update, context: CallbackContext):
    print(context)
    print(update)
    update.effective_message.reply_text('cannot handle this message type')


def error(update: Update, context: CallbackContext):
    """
    Log Errors caused by Updates.
    """
    print(update)
    print(context)
    logger.warning(f'Update "{update}" caused error "{context.error}"')
    raise context.error


def print_msg(update: Update, context: CallbackContext):
    print(update)


if __name__ == '__main__':
    hawkers = []
    df = pd.read_csv('data/hawker-centres/hawker-centres.csv')
    for i, row in df.iterrows():
        hawkers.append(Hawker.from_row(row))

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

    updater = Updater(secrets['hawker_centre_bot_token'])

    # handle commands
    updater.dispatcher.add_handler(CommandHandler('start', cmd_start))
    updater.dispatcher.add_handler(CommandHandler('help', cmd_help))
    updater.dispatcher.add_handler(CommandHandler('share', cmd_share))

    # by date
    updater.dispatcher.add_handler(CommandHandler('today', cmd_today))
    updater.dispatcher.add_handler(CommandHandler('tomorrow', cmd_tomorrow))
    updater.dispatcher.add_handler(CommandHandler('week', cmd_this_week))
    updater.dispatcher.add_handler(CommandHandler('this', cmd_this_week))
    updater.dispatcher.add_handler(CommandHandler('thisweek', cmd_this_week))
    updater.dispatcher.add_handler(CommandHandler('this_week', cmd_this_week))
    updater.dispatcher.add_handler(CommandHandler('next', cmd_next_week))
    updater.dispatcher.add_handler(CommandHandler('nextweek', cmd_next_week))
    updater.dispatcher.add_handler(CommandHandler('next_week', cmd_next_week))

    # by name / zip code
    updater.dispatcher.add_handler(CommandHandler('search', cmd_search))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, handle_text))

    # by location
    updater.dispatcher.add_handler(MessageHandler(Filters.location, location))

    # handle non-commands
    updater.dispatcher.add_handler(MessageHandler(Filters.all, ignore))
    updater.dispatcher.add_handler(MessageHandler(Filters.all, print_msg), 2)

    # log all errors
    updater.dispatcher.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT, SIGTERM or SIGABRT.
    # This should be used most of the time, since start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
