from dataclasses import dataclass
from enum import Enum
from typing import Any
from typing import Callable
from typing import Generator
from typing import Iterable
from typing import List
from typing import Pattern
from typing import TypeVar
from typing import Union

from telegram import Update
from telegram.ext import CallbackContext

from fastbot.response import Response
# fastapi.types.DecoratedCallable: stricter type inference, guaranteeing same type signature for decorated function
from fastbot.utils import get_typed_signature

AnyResponse = Union[str, Response]
Callback = TypeVar('Callback', bound=Callable[..., Union[AnyResponse,
                                                         Iterable[AnyResponse],
                                                         Generator[AnyResponse, Any, None]]])


class Match(Enum):
    KEYWORD_FULLMATCH = 1
    COMMAND_FULLMATCH = 2
    REGEX_FULLMATCH = 3


@dataclass(frozen=True)
class RouteAPI:
    pattern: Pattern
    callback: Callback

    def match(self, update: Update, context: CallbackContext) -> Match:
        ...

    def handle(self, update: Update, context: CallbackContext) -> List[Response]:
        ...


#
# if isinstance(update, Update) and update.effective_message:
#     message = update.effective_message
#
#     if (
#             message.entities
#             and message.entities[0].type == MessageEntity.BOT_COMMAND
#             and message.entities[0].offset == 0
#             and message.text
#             and message.bot
#     ):
#         command = message.text[1 : message.entities[0].length]
#         args = message.text.split()[1:]
#         command_parts = command.split('@')
#         command_parts.append(message.bot.username)
#
#         if not (
#                 command_parts[0].lower() in self.command
#                 and command_parts[1].lower() == message.bot.username.lower()
#         ):
#             return None
#
#         filter_result = self.filters(update)
#         if filter_result:
#             return args, filter_result
#         return False
# return None


if __name__ == '__main__':
    def f(a: str, b: int, c: Update, d: CallbackContext, e: Callback) -> Response:
        pass


    print(get_typed_signature(f))
