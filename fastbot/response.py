from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Generator
from typing import Iterable
from typing import List
from typing import Optional
from typing import Union

from fastbot._telegram_api import ChatAction
from fastbot._telegram_api import Update


@dataclass(frozen=True)
class Response(ABC):

    @abstractmethod
    def send_reply(self, update: Update):
        ...


@dataclass(frozen=True)
class TextResponse(Response, ABC):
    content: str
    notification: bool = True
    web_page_preview: bool = True
    quote: bool = False


@dataclass(frozen=True)
class Text(TextResponse):
    def send_reply(self, update: Update):
        update.effective_message.reply_text(self.content,
                                            disable_notification=not self.notification,
                                            disable_web_page_preview=not self.web_page_preview,
                                            quote=self.quote,
                                            )


@dataclass(frozen=True)
class Markdown(TextResponse):
    def send_reply(self, update: Update):
        update.effective_message.reply_markdown(self.content,
                                                disable_notification=not self.notification,
                                                disable_web_page_preview=not self.web_page_preview,
                                                quote=self.quote,
                                                )


@dataclass(frozen=True)
class BusyWait(Response):
    action: str = ChatAction.TYPING
    timeout: float = 10.0

    def send_reply(self, update: Update):
        update.effective_message.reply_chat_action(action=self.action,
                                                   timeout=self.timeout,
                                                   )


@dataclass(frozen=True)
class FileResponse(Response, ABC):
    path: Path
    caption: Optional[str] = None
    filename: Optional[str] = None
    notification: bool = True
    timeout_seconds: Union[int, float] = 20
    quote: bool = False

    def __post_init__(self):
        if not self.path.exists():
            raise FileNotFoundError(self.path)
        if not self.path.is_file():
            raise IsADirectoryError(self.path)
        if self.path.stat().st_size > 50 * 1000 * 1000:
            raise IOError(self.path)


@dataclass(frozen=True)
class Animation(FileResponse):
    def __post_init__(self):
        super().__post_init__()

        # check filetype
        if self.path.suffix.lower() != '.gif':
            raise ValueError(self.path)

    def send_reply(self, update: Update):
        with self.path.open('rb') as f:
            update.effective_message.reply_animation(animation=f,
                                                     caption=self.caption,
                                                     filename=self.filename,
                                                     disable_notification=not self.notification,
                                                     timeout=self.timeout_seconds,
                                                     quote=self.quote,
                                                     )


@dataclass(frozen=True)
class Document(FileResponse):
    def send_reply(self, update: Update):
        with self.path.open('rb') as f:
            update.effective_message.reply_document(document=f,
                                                    caption=self.caption,
                                                    filename=self.filename,
                                                    disable_notification=not self.notification,
                                                    timeout=self.timeout_seconds,
                                                    quote=self.quote,
                                                    )


def _normalize_response(response: Union[Response, str, Path]) -> Response:
    if isinstance(response, Response):
        return response
    if isinstance(response, str):
        return Text(response)
    if isinstance(response, Path):
        return Document(response)
    raise TypeError(response)


def normalize_responses(responses: Union[Response,
                                         Iterable[Response],
                                         Generator[Response, Any, None]],
                        ) -> List[Response]:
    if isinstance(responses, (Response, str, Path)):
        return [_normalize_response(responses)]
    elif isinstance(responses, (Iterable, Generator)):
        return list(map(_normalize_response, responses))
    else:
        raise TypeError(responses)
