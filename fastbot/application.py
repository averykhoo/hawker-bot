from typing import Callable
from typing import Optional

from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.ext import InlineQueryHandler
from telegram.ext import MessageFilter
from telegram.ext import MessageHandler
from telegram.ext import Updater

from fastbot.inline import InlineRoute
from fastbot.route import Endpoint
from fastbot.route import Route
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
        """
        todo: middleware? (eg. logging)
        """
        # initialize python-telegram-bot with bot api key
        self._updater = Updater(api_key)

        # migration handler
        self.add_message_handler(chat_migration, Filters.status_update.migrate)

        # logger
        self._logger: Optional[Route] = None

        # text handlers
        self._router = Router()
        self.add_message_handler(self._router.callback, Filters.text)

        # inline handler
        self._inline: Optional[InlineRoute] = None

        # location handler
        self._location: Optional[Route] = None

        # unrecognized message type handler
        self._unrecognized: Optional[Route] = None

        # error handler
        self._error: Optional[Route] = None

        # convenience mappings so we can add stuff directly
        self.keyword = self._router.keyword
        self.command = self._router.command
        self.regex = self._router.regex
        self.default = self._router.default

    def add_message_handler(self,
                            callback: Callback,
                            message_filter: MessageFilter,
                            group: int = 10,
                            ) -> None:
        self._updater.dispatcher.add_handler(MessageHandler(message_filter, callback), group)

    def logger(self, endpoint: Endpoint) -> Endpoint:
        assert self._logger is None
        self._logger = Route(endpoint)
        self.add_message_handler(self._logger.callback, Filters.all, 1)
        return endpoint

    def location(self, endpoint: Endpoint) -> Endpoint:
        assert self._location is None
        self._location = Route(endpoint)
        self.add_message_handler(self._location.callback, Filters.location)
        return endpoint

    def unrecognized(self, endpoint: Endpoint) -> Endpoint:
        assert self._unrecognized is None
        self._unrecognized = Route(endpoint)
        self.add_message_handler(self._unrecognized.callback, Filters.all)
        return endpoint

    def add_command_handler(self,
                            callback: Callback,
                            command: str,
                            group: int = 10,
                            ) -> None:
        self._updater.dispatcher.add_handler(CommandHandler(command, callback), group)

    def add_inline_handler(self,
                           callback: Callback,
                           group: int = 10,
                           ) -> None:
        self._updater.dispatcher.add_handler(InlineQueryHandler(callback), group)

    def inline(self, endpoint: Endpoint) -> Endpoint:
        assert self._inline is None
        self._inline = InlineRoute(endpoint)
        self.add_inline_handler(self._inline.callback)
        return endpoint

    def add_error_handler(self,
                          callback: Callback,
                          ) -> None:
        # noinspection PyTypeChecker
        self._updater.dispatcher.add_error_handler(callback)

    def error(self, endpoint: Endpoint) -> Endpoint:
        assert self._error is None
        self._error = Route(endpoint)
        self.add_error_handler(self._error.callback)
        return endpoint

    def run_forever(self):
        # Start the Bot
        self._updater.start_polling()

        # Run the bot until you press Ctrl-C or the process receives SIGINT, SIGTERM or SIGABRT.
        # This should be used most of the time, since start_polling() is non-blocking and will stop the bot gracefully.
        self._updater.idle()
