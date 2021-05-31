from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any
from typing import Callable
from typing import Generator
from typing import Iterable
from typing import List
from typing import Union

from telegram import Update


@dataclass
class Response(ABC):

    @abstractmethod
    def send_reply(self, update: Update):
        ...


@dataclass
class StringResponse(Response, ABC):
    content: str
    notification: bool = True
    web_page_preview: bool = True


@dataclass
class Text(StringResponse):
    def send_reply(self, update: Update):
        update.effective_message.reply_text(self.content,
                                            disable_notification=not self.notification,
                                            disable_web_page_preview=not self.web_page_preview,
                                            )


@dataclass
class Markdown(StringResponse):
    def send_reply(self, update: Update):
        update.effective_message.reply_markdown(self.content,
                                                disable_notification=not self.notification,
                                                disable_web_page_preview=not self.web_page_preview,
                                                )


@dataclass
class InlineResponse(Response, ABC):
    title: str
    content: str


@dataclass
class InlineMarkdownArticle(InlineResponse):

    def _reply(self, update: Update):
        message.update.inline_query.answer([
            InlineQueryResultVenue(
                id=str(uuid.uuid4()),
                latitude=hawker.latitude,
                longitude=hawker.longitude,
                title=hawker.name,
                address=hawker.address_myenv,
                input_message_content=InputTextMessageContent(hawker.to_markdown(),
                                                              parse_mode=ParseMode.MARKDOWN
                                                              ),
            ) for hawker in results[:5]
        ])


def normalize_responses(responses: Union[Response,
                                         Iterable[Response],
                                         Generator[Response, Any, None]],
                        default_response: Callable[[str], Response] = Text,
                        ) -> List[Response]:
    if isinstance(responses, Response):
        return [responses]
    elif isinstance(responses, str):
        return [default_response(responses)]
    elif isinstance(responses, (Iterable, Generator)):
        out = []
        for response in responses:
            if isinstance(response, Response):
                out.append(response)
            elif isinstance(response, str):
                return [default_response(response)]
            else:
                raise TypeError(response)
        return out
    else:
        raise TypeError(responses)
