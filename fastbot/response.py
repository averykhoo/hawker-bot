from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any
from typing import Callable
from typing import Generator
from typing import Iterable
from typing import List
from typing import Union

# noinspection PyPackageRequirements
from telegram import Update


@dataclass(frozen=True)
class Response(ABC):
    content: str
    notification: bool = True
    web_page_preview: bool = True

    @abstractmethod
    def send_reply(self, update: Update):
        ...


@dataclass(frozen=True)
class Text(Response):
    def send_reply(self, update: Update):
        update.effective_message.reply_text(self.content,
                                            disable_notification=not self.notification,
                                            disable_web_page_preview=not self.web_page_preview,
                                            )


@dataclass(frozen=True)
class Markdown(Response):
    def send_reply(self, update: Update):
        update.effective_message.reply_markdown(self.content,
                                                disable_notification=not self.notification,
                                                disable_web_page_preview=not self.web_page_preview,
                                                )


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
