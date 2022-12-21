import time
import warnings
from signal import SIGABRT
from signal import SIGINT
from signal import SIGTERM
from signal import signal
from typing import Callable
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from fastbot._telegram_api import CallbackContext
from fastbot._telegram_api import CommandHandler
from fastbot._telegram_api import Filters
from fastbot._telegram_api import InlineQueryHandler
from fastbot._telegram_api import MessageFilter
from fastbot._telegram_api import MessageHandler
from fastbot._telegram_api import Update
from fastbot._telegram_api import Updater
from fastbot.inline import InlineRoute
from fastbot.route import Endpoint
from fastbot.route import Route
from fastbot.router import Router

Callback = Callable[[Update, CallbackContext], None]


def chat_migration(update, context):
    """
    https://github.com/python-telegram-bot/python-telegram-bot/wiki/Storing-bot,-user-and-chat-related-data
    """

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
    # todo: support user preference storage
    # todo: support chat / group / channel storage
    # todo: use sqlmodel and sqlite
    # todo: support broadcasting
    # todo: User / Group / Chat / Channel class (maybe based off sqlmodel)
    # todo: don't store all the handlers, or at worse use a dict because there are going to be more

    _default_group = 10

    def __init__(self, api_key: str):
        # initialize python-telegram-bot with bot api key
        self._updater = Updater(api_key)
        self.user_id = int(api_key.partition(':')[0])

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

        # group created
        self._chat_created: Optional[Route] = None

        # self, other bot, or a user added to group
        self._new_chat_members: Optional[Route] = None

        # unrecognized message type handler
        self._unrecognized: Optional[Route] = None
        self._unrecognized_handler: Optional[MessageHandler] = None

        # error handler
        self._error: Optional[Route] = None

        # convenience mappings so we can add stuff directly
        self.keyword = self._router.keyword
        self.command = self._router.command
        self.regex = self._router.regex
        self.default = self._router.default

        # shutdown flag
        self.__shutdown_flag = None

    def add_message_handler(self,
                            callback: Callback,
                            message_filter: MessageFilter,
                            group: int = -1,
                            ) -> None:
        if group < 0:
            group = self._default_group
        if getattr(self, '_unrecognized_handler', None) is None:
            self._updater.dispatcher.add_handler(MessageHandler(message_filter, callback), group)
        else:
            assert self._unrecognized_handler is not None
            try:
                self._updater.dispatcher.remove_handler(self._unrecognized_handler, group)
            except KeyError:
                self._updater.dispatcher.add_handler(MessageHandler(message_filter, callback), group)
            else:
                self._updater.dispatcher.add_handler(MessageHandler(message_filter, callback), group)
                self._updater.dispatcher.add_handler(self._unrecognized_handler, group)

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

    def add_error_handler(self,
                          callback: Callback,
                          ) -> None:
        # noinspection PyTypeChecker
        self._updater.dispatcher.add_error_handler(callback)

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

    def chat_created(self, endpoint: Endpoint) -> Endpoint:
        assert self._chat_created is None
        self._chat_created = Route(endpoint)
        self.add_message_handler(self._chat_created.callback, Filters.status_update.chat_created)
        return endpoint

    def new_chat_members(self, endpoint: Endpoint) -> Endpoint:
        assert self._new_chat_members is None
        self._new_chat_members = Route(endpoint)
        self.add_message_handler(self._new_chat_members.callback, Filters.status_update.new_chat_members)
        return endpoint

    def unrecognized(self, endpoint: Endpoint) -> Endpoint:
        assert self._unrecognized is None
        self._unrecognized = Route(endpoint)
        self._unrecognized_handler = MessageHandler(Filters.all, self._unrecognized.callback)
        self._updater.dispatcher.add_handler(self._unrecognized_handler, self._default_group)
        return endpoint

    def inline(self, endpoint: Endpoint) -> Endpoint:
        assert self._inline is None
        self._inline = InlineRoute(endpoint)
        self.add_inline_handler(self._inline.callback)
        return endpoint

    def error(self, endpoint: Endpoint) -> Endpoint:
        # todo: log tracebacks
        # todo: provide a logger and just ask for a filename?
        assert self._error is None
        self._error = Route(endpoint)
        self.add_error_handler(self._error.callback)
        return endpoint

    def idle(self,
             stop_signals: Union[List, Tuple] = (SIGINT, SIGTERM, SIGABRT),
             function: Optional[Callable] = None,
             delay: Union[int, float] = 60 * 60,
             ) -> None:
        """
        Blocks until one of the signals are received and stops the updater.
        runs some function every delay seconds
        """
        for sig in stop_signals:
            # noinspection PyProtectedMember
            signal(sig, self._updater._signal_handler)

        self._updater.is_idle = True

        next_run = time.time() + delay
        while self._updater.is_idle:
            time.sleep(1)

            # run the idle function at the requested time intervals
            if time.time() >= next_run:
                if function:
                    try:
                        function()
                    except Exception as e:
                        warnings.warn(f'Error in idle function: {e}')
                next_run = time.time() + delay

            # shutdown code copied from Updater._signal_handler()
            if self.__shutdown_flag:
                self._updater.is_idle = False
                if self._updater.running:
                    if self._updater.persistence:
                        self._updater.dispatcher.update_persistence()
                        self._updater.persistence.flush()
                    self._updater.stop()

    def run_forever(self, function: Optional[Callable] = None, delay: Union[int, float] = 60 * 60) -> None:
        # todo: schedule cron jobs - use cronsim?
        # todo: utc offset for cron jobs (default None=local, otherwise timedelta)
        # todo: timer coalescing fudge factor

        # start the bot
        self.__shutdown_flag = False
        self._updater.start_polling()

        # run the bot until you press Ctrl-C or the process receives SIGINT, SIGTERM or SIGABRT.
        # this should be used most of the time,
        # since `start_polling()` is non-blocking and will stop the bot gracefully
        self.idle(function=function, delay=delay)

    def shutdown(self):
        self.__shutdown_flag = True
