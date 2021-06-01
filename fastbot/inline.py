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

from telegram import InlineQueryResultArticle
from telegram import InlineQueryResultVenue
from telegram import InputTextMessageContent
from telegram import ParseMode
from telegram import Update
from telegram.ext import CallbackContext

from fastbot.route import Endpoint


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
class InlineRoute:
    endpoint: Endpoint

    def handle_message(self, message: InlineQuery) -> None:
        ret = self.endpoint(message)
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
