from typing import Callable

from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.ext import InlineQueryHandler
from telegram.ext import MessageFilter
from telegram.ext import MessageHandler
from telegram.ext import Updater

from fastbot.router import Router

Callback = Callable[[Update, CallbackContext], None]


def chat_migration(update, context):
    m = update.message
    dp = context.dispatcher  # available since version 12.4

    # Get old and new chat ids
    old_id = m.migrate_from_chat_id or m.chat_id
    new_id = m.migrate_to_chat_id or m.chat_id

    # transfer data, if old data is still present
    if old_id in dp.chat_data:
        dp.chat_data[new_id].update(dp.chat_data.get(old_id))
        del dp.chat_data[old_id]


class FastBot:
    def __init__(self, api_key: str):
        self.bot_updater = Updater(api_key)
        self.add_message_handler(chat_migration, Filters.status_update.migrate)

        self.middleware = []  # usually logging?

        self.router = Router()
        self.add_message_handler(self.router.callback, Filters.text)

    def add_inline_handler(self,
                           callback: Callback,
                           group: int = 10,
                           ) -> None:
        self.bot_updater.dispatcher.add_handler(InlineQueryHandler(callback), group)

    def add_message_handler(self,
                            callback: Callback,
                            message_filter: MessageFilter = Filters.all,
                            group: int = 10,
                            ) -> None:
        self.bot_updater.dispatcher.add_handler(MessageHandler(message_filter, callback), group)

    def add_command_handler(self,
                            callback: Callback,
                            command: str,
                            group: int = 10,
                            ) -> None:
        self.bot_updater.dispatcher.add_handler(CommandHandler(command, callback), group)

    def add_error_handler(self,
                          callback: Callback,
                          ) -> None:
        # noinspection PyTypeChecker
        self.bot_updater.dispatcher.add_error_handler(callback)

    def run_forever(self):
        # Start the Bot
        self.bot_updater.start_polling()

        # Run the bot until you press Ctrl-C or the process receives SIGINT, SIGTERM or SIGABRT.
        # This should be used most of the time, since start_polling() is non-blocking and will stop the bot gracefully.
        self.bot_updater.idle()
