from dataclasses import dataclass
from enum import Enum
from typing import Any
from typing import Callable
from typing import Generator
from typing import Iterable
from typing import Pattern
from typing import TypeVar
from typing import Union

from telegram import Update
from telegram.ext import CallbackContext

from fastbot.message import Message
from fastbot.response import Response
from fastbot.response import Text
from fastbot.utils import get_typed_signature

# fastapi.types.DecoratedCallable: stricter type inference, guaranteeing same type signature for decorated function
AnyResponse = Union[str, Response]
Endpoint = TypeVar('Endpoint', bound=Callable[[Message], Union[AnyResponse,
                                                               Iterable[AnyResponse],
                                                               Generator[AnyResponse, Any, None]]])


class Match(Enum):
    KEYWORD_FULLMATCH = 1
    COMMAND_FULLMATCH = 2
    REGEX_FULLMATCH = 3


@dataclass(frozen=True)
class Route:
    pattern: Pattern
    endpoint: Endpoint

    def match(self, update: Update, context: CallbackContext) -> Match:
        raise NotImplementedError

    def callback(self, update: Update, context: CallbackContext) -> None:
        message = Message(update, context)
        ret = self.endpoint(message)

        if isinstance(ret, Response):
            responses = [ret]
        elif isinstance(ret, str):
            responses = [Text(ret)]
        elif isinstance(ret, (Iterable, Generator)):
            responses = []
            for response in ret:
                if isinstance(response, Response):
                    responses.append(response)
                elif isinstance(response, str):
                    responses.append(Text(response))
                else:
                    raise TypeError(response)
        else:
            raise TypeError(ret)

        for response in responses:
            response.send(update)


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
    def f(a: str, b: int, c: Update, d: CallbackContext, e: Endpoint) -> Response:
        pass


    print(get_typed_signature(f))
