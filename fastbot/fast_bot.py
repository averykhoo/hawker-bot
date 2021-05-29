from typing import Callable
from typing import Union

from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.ext import MessageFilter
from telegram.ext import MessageHandler
from telegram.ext import Updater

from fastbot.route import Endpoint
from fastbot.route import Route

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

        self.keyword_handlers = dict()
        self.command_handlers = dict()  # including start deep links
        self.regex_handlers = []

        self.message_handler = None
        self.inline_handler = None

        self.error_handler = None

    def add_message_handler(self,
                            callback: Union[Route, Callback],
                            message_filter: MessageFilter = Filters.all,
                            group: int = 10,
                            ) -> None:
        self.bot_updater.dispatcher.add_handler(MessageHandler(message_filter, callback), group)

    def add_command_handler(self,
                            command: str,
                            callback: Union[Route, Callback],
                            group: int = 10,
                            ) -> None:
        self.bot_updater.dispatcher.add_handler(CommandHandler(command, callback), group)

    def run_forever(self):
        # Start the Bot
        self.bot_updater.start_polling()

        # Run the bot until you press Ctrl-C or the process receives SIGINT, SIGTERM or SIGABRT.
        # This should be used most of the time, since start_polling() is non-blocking and will stop the bot gracefully.
        self.bot_updater.idle()

    def add_command(self, command, endpoint):
        # check for duplicates
        if command in self.command_handlers:
            raise KeyError(command)

        # do something
        print(command, endpoint.__name__)

    def command(self,
                command: str,
                /, *,
                allow_backslash: bool = True,
                ) -> Callable[[Endpoint], Endpoint]:
        # we don't need functools.wraps because we're not actually wrapping the function
        def decorator(endpoint: Endpoint) -> Endpoint:
            self.add_command(command, endpoint)
            return endpoint

        return decorator


if __name__ == '__main__':
    fb = FastBot('asd')


    @fb.command('a')
    def func():
        return 1
