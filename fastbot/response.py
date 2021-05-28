from dataclasses import dataclass


@dataclass
class Response:
    content: str
    web_page_preview: bool = True
    notification: bool = True


@dataclass
class Text(Response):
    pass


@dataclass
class Markdown(Response):
    pass


@dataclass
class MarkdownV2(Response):
    pass

