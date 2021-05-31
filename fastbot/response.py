from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass

from fastbot.message import Message


@dataclass
class Response(ABC):
    content: str
    notification: bool = True
    web_page_preview: bool = True

    @abstractmethod
    def send(self, message: Message):
        ...


@dataclass
class Text(Response):
    def send(self, message: Message):
        message.update.effective_message.reply_text(self.content,
                                                    disable_notification=not self.notification,
                                                    disable_web_page_preview=not self.web_page_preview,
                                                    )


@dataclass
class Markdown(Response):
    def send(self, message: Message):
        message.update.effective_message.reply_markdown(self.content,
                                                        disable_notification=not self.notification,
                                                        disable_web_page_preview=not self.web_page_preview,
                                                        )
