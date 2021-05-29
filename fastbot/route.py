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
