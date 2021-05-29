from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass

from telegram import Update


@dataclass
class Response(ABC):
    content: str
    web_page_preview: bool = True
    notification: bool = True

    @abstractmethod
    def send(self, update: Update):
        ...


@dataclass
class Text(Response):
    def send(self, update: Update):
        update.effective_message.reply_text(self.content,
                                            disable_notification=not self.notification,
                                            disable_web_page_preview=not self.web_page_preview,
                                            )


@dataclass
class Markdown(Response):
    def send(self, update: Update):
        update.effective_message.reply_markdown(self.content,
                                                disable_notification=not self.notification,
                                                disable_web_page_preview=not self.web_page_preview,
                                                )
