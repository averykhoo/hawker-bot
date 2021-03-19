# import json
# import logging
#
# from telegram import Update
# from telegram.ext import CallbackContext
# from telegram.ext import CommandHandler
# from telegram.ext import Filters
# from telegram.ext import MessageHandler
# from telegram.ext import Updater
#
# # Enable logging
# logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#                     level=logging.INFO)
#
# logger = logging.getLogger(__name__)
#
#
# # Define a few command handlers.
# # These usually take the two arguments update and context.
# # Error handlers also receive the raised TelegramError object in error.
# def start(update: Update, context: CallbackContext):
#     """Send a message when the command /start is issued."""
#     assert isinstance(update, Update)
#     assert isinstance(context, CallbackContext)
#     update.message.reply_text('Hi!')
#
#
# def help(update: Update, context: CallbackContext):
#     """Send a message when the command /help is issued."""
#     update.message.reply_text('Help!')
#
#
# def echo(update: Update, context: CallbackContext):
#     """Echo the user message."""
#     logging.info(f'received: {update.message.text}')
#     if update.message.text == '/error':
#         raise RuntimeError('some error message here')
#     update.message.reply_text(update.message.text)
#
#
# def location(update: Update, context: CallbackContext):
#     if update.message is not None:
#         lines = [
#             f'longitude:              {update.message.location.longitude}',
#             f'latitude:               {update.message.location.latitude}',
#             f'horizontal_accuracy:    {update.message.location.horizontal_accuracy}',
#             f'live_period:            {update.message.location.live_period}',
#             f'heading:                {update.message.location.heading}',
#             f'proximity_alert_radius: {update.message.location.proximity_alert_radius}',
#         ]
#         update.message.reply_text('\n'.join(lines))
#     elif update.edited_message is not None:
#         lines = [
#             f'longitude:              {update.edited_message.location.longitude}',
#             f'latitude:               {update.edited_message.location.latitude}',
#             f'horizontal_accuracy:    {update.edited_message.location.horizontal_accuracy}',
#             f'live_period:            {update.edited_message.location.live_period}',
#             f'heading:                {update.edited_message.location.heading}',
#             f'proximity_alert_radius: {update.edited_message.location.proximity_alert_radius}',
#         ]
#         update.edited_message.reply_text('\n'.join(lines))
#     else:
#         print(update)
#
#
# def ignore(update: Update, context: CallbackContext):
#     print(context)
#     print(update)
#     update.message.reply_text('cannot handle this message type')
#
#
# def error(update: Update, context: CallbackContext):
#     """Log Errors caused by Updates."""
#     print(update)
#     print(context)
#     logger.warning(f'Update "{update}" caused error "{context.error}"')
#     raise context.error
#
#
# if __name__ == '__main__':
#     with open('secrets.json') as f:
#         secrets = json.load(f)
#
#     updater = Updater(secrets['echo_bot_token'])
#
#     # handle commands
#     updater.dispatcher.add_handler(CommandHandler("start", start))
#     updater.dispatcher.add_handler(CommandHandler("help", help))
#     updater.dispatcher.add_handler(CommandHandler("ignore", ignore))
#
#     # handle non-commands
#     updater.dispatcher.add_handler(MessageHandler(Filters.text, echo))
#     updater.dispatcher.add_handler(MessageHandler(Filters.location, location))
#     updater.dispatcher.add_handler(MessageHandler(Filters.all, ignore))
#
#     # log all errors
#     updater.dispatcher.add_error_handler(error)
#
#     # Start the Bot
#     updater.start_polling()
#
#     # Run the bot until you press Ctrl-C or the process receives SIGINT, SIGTERM or SIGABRT.
#     # This should be used most of the time, since start_polling() is non-blocking and will stop the bot gracefully.
#     updater.idle()
