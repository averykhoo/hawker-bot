import inspect
import json
import uuid
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any
from typing import Dict
from typing import Generator
from typing import Iterable
from typing import List

from fastbot._telegram_api import CallbackContext
from fastbot._telegram_api import InlineQueryResultArticle
from fastbot._telegram_api import InlineQueryResultVenue
from fastbot._telegram_api import InputTextMessageContent
from fastbot._telegram_api import ParseMode
from fastbot._telegram_api import Update
from fastbot.route import Route


@dataclass(frozen=True)
class InlineResponse(ABC):
    title: str
    content: str

    @property
    def markdown_content(self):
        return InputTextMessageContent(self.content, parse_mode=ParseMode.MARKDOWN)

    @abstractmethod
    def create_reply(self):
        ...


@dataclass(frozen=True)
class InlineArticle(InlineResponse):

    def create_reply(self):
        return InlineQueryResultArticle(id=str(uuid.uuid4()),
                                        title=self.title,
                                        input_message_content=self.markdown_content,
                                        )


@dataclass(frozen=True)
class InlineVenue(InlineResponse):
    latitude: float
    longitude: float
    address: str

    def create_reply(self):
        return InlineQueryResultVenue(id=str(uuid.uuid4()),
                                      latitude=self.latitude,
                                      longitude=self.longitude,
                                      title=self.title,
                                      address=self.address,
                                      input_message_content=self.markdown_content,
                                      )


@dataclass
class InlineQuery:
    update: Update
    context: CallbackContext

    @property
    def text(self) -> str:
        return self.update.inline_query.query.strip()

    def to_dict(self) -> Dict[str, Any]:
        return self.update.to_dict()

    def to_json(self) -> str:
        return json.dumps(self.update.to_dict())

    def reply(self, responses: List[InlineResponse]):
        self.update.inline_query.answer([response.create_reply() for response in responses])


@dataclass(frozen=True)
class InlineRoute(Route):

    def __post_init__(self):
        # get all argument names
        arg_names = list(inspect.signature(self.endpoint).parameters.keys())
        arg_types = {arg_name: arg_type
                     for arg_name, arg_type in self.endpoint.__annotations__.items()
                     if arg_name != 'return'}

        # inline function taking no input is useless
        if len(arg_names) == 0:
            raise TypeError(self.endpoint)

        # singleton untyped argument, assume InlineQuery
        if len(arg_types) == 0 and len(arg_names) == 1:
            self._message_converters[arg_names[0]] = lambda m: m
            return

        # can't predict what this function expects to receive
        if len(arg_types) != len(arg_names):
            raise TypeError(self.endpoint)

        # check type signature and convert message appropriately
        for arg_name, arg_type in arg_types.items():
            if arg_type == InlineQuery:
                self._message_converters[arg_name] = lambda m: m
            elif arg_type == Update:
                self._message_converters[arg_name] = lambda m: m.update
            elif arg_type == CallbackContext:
                self._message_converters[arg_name] = lambda m: m.context
            elif arg_type == str:
                self._message_converters[arg_name] = lambda m: m.text
            else:
                raise TypeError(self.endpoint)

    def strict_endpoint(self, message: InlineQuery) -> List[InlineResponse]:
        kwargs = {name: converter(message) for name, converter in self._message_converters.items()}
        ret = self.endpoint(**kwargs)
        if ret is None:
            return []
        else:
            return list(ret)

    def handle_message(self, message: InlineQuery) -> None:
        ret = self.strict_endpoint(message)
        if ret is None:
            pass
        elif isinstance(ret, InlineResponse):
            message.reply([ret])
        elif isinstance(ret, (Iterable, Generator)):
            responses = []
            for response in ret:
                if not isinstance(response, InlineResponse):
                    raise TypeError(response)
                responses.append(response)
            message.reply(responses)
        else:
            raise TypeError(ret)

    def callback(self,
                 update: Update,
                 context: CallbackContext,
                 ) -> None:
        self.handle_message(InlineQuery(update, context))
