from typing import Callable

from telegram.ext import Updater

from fastbot.route import Callback


class FastBot:
    def __init__(self, api_key: str):
        self.bot_updater = Updater(api_key)

        self.middleware = []  # usually logging?

        self.keyword_handlers = dict()
        self.command_handlers = dict()  # including start deep links
        self.regex_handlers = []

        self.message_handler = None
        self.inline_handler = None

        self.error_handler = None

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
                ) -> Callable[[Callback], Callback]:
        # we don't need functools.wraps because we're not actually wrapping the function
        def decorator(endpoint: Callback) -> Callback:
            self.add_command(command, endpoint)
            return endpoint

        return decorator


if __name__ == '__main__':
    fb = FastBot('asd')


    @fb.command('a')
    def func():
        return 1
