import re
from dataclasses import dataclass
from enum import IntEnum
from functools import wraps
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Generator
from typing import Iterable
from typing import List
from typing import Optional
from typing import Pattern
from typing import Set
from typing import TypeVar
from typing import Union

from fastbot._telegram_api import CallbackContext
from fastbot._telegram_api import Update
from fastbot.message import Message
from fastbot.response import AnyResponse
from fastbot.response import Response
from fastbot.response import normalize_response

# fastapi.types.DecoratedCallable: stricter type inference, guaranteeing same type signature for decorated function
Endpoint = TypeVar('Endpoint', bound=Callable[[Message], List[Response]])
LenientEndpoint = Callable[..., Union[None, AnyResponse, Iterable[AnyResponse], Generator[AnyResponse, Any, None]]]


def normalize_responses(responses: Union[None, AnyResponse, Iterable[AnyResponse], Generator[AnyResponse, Any, None]],
                        ) -> List[Response]:
    if responses is None:
        return []
    if isinstance(responses, (Response, str, Path)):
        return [normalize_response(responses)]
    elif isinstance(responses, (Iterable, Generator)):
        return list(map(normalize_response, responses))
    else:
        raise TypeError(responses)


def make_endpoint(func: LenientEndpoint,
                  ) -> Endpoint:
    """
    wrap a function to make it an endpoint
    """
    _converters = dict()
    # noinspection PyUnresolvedReferences
    for arg_name, arg_type in func.__annotations__.items():
        if arg_type == Message:
            _converters[arg_name] = lambda m: m
        elif arg_type == Update:
            _converters[arg_name] = lambda m: m.update
        elif arg_type == CallbackContext:
            _converters[arg_name] = lambda m: m.context
        else:
            raise TypeError(func)

    @wraps(func)
    def endpoint(message: Message) -> List[Response]:
        return normalize_responses(func(**{name: converter(message) for name, converter in _converters.items()}))

    return endpoint


class Match(IntEnum):
    FULL_MATCH = 3
    PREFIX_MATCH = 2
    SUBSTRING_MATCH = 1
    NO_MATCH = 0


@dataclass(frozen=True)
class Route:
    endpoint: Endpoint

    def handle_message(self, message: Message) -> None:
        ret = self.endpoint(message)
        if ret is not None:
            message.reply(normalize_responses(ret))

    def callback(self,
                 update: Update,
                 context: CallbackContext,
                 ) -> None:
        self.handle_message(Message(update, context))


@dataclass(frozen=True)
class RegexRoute(Route):
    pattern: Pattern
    allowed_matches: Set[Match]
    canonical_name: Optional[str] = None

    def match(self, message: Message) -> Match:
        match = self.pattern.search(message.text)
        if match is None:
            return Match.NO_MATCH

        if match.start() != 0:
            if Match.SUBSTRING_MATCH in self.allowed_matches:
                return Match.SUBSTRING_MATCH
            else:
                return Match.NO_MATCH

        if match.end() != len(message.text):
            if Match.PREFIX_MATCH in self.allowed_matches:
                return Match.PREFIX_MATCH
            else:
                return Match.NO_MATCH

        if Match.FULL_MATCH in self.allowed_matches:
            return Match.FULL_MATCH
        else:
            return Match.NO_MATCH

    def handle_message(self, message: Message) -> None:
        match = self.pattern.search(message.text)
        assert match is not None, (self.pattern, match)

        message.match = match
        message.command = self.canonical_name

        super().handle_message(message)

    def callback(self,
                 update: Update,
                 context: CallbackContext,
                 ) -> None:
        self.handle_message(Message(update, context))


def make_keyword_route(endpoint: LenientEndpoint,
                       keyword: str,
                       case: bool = False,
                       boundary: bool = True,
                       canonical_name: Optional[str] = None,
                       full_match: bool = True,
                       prefix_match: bool = False,
                       substring_match: bool = False,
                       ) -> RegexRoute:
    # case sensitivity
    flags = re.U
    if not case:
        flags |= re.I

    # boundary checking
    if boundary:
        pattern = re.compile(rf'(?:^|\b)(?P<command>{re.escape(keyword)})(?:\b|$)', flags=flags)
    else:
        pattern = re.compile(rf'(?P<command>{re.escape(keyword)})', flags=flags)

    # create route
    return make_regex_route(endpoint,
                            pattern,
                            canonical_name=canonical_name,
                            full_match=full_match,
                            prefix_match=prefix_match,
                            substring_match=substring_match,
                            )


def make_command_route(endpoint: LenientEndpoint,
                       command: str,
                       argument_pattern: Optional[Pattern] = None,
                       case: bool = False,
                       allow_backslash: bool = True,
                       allow_noslash: bool = False,
                       boundary: bool = True,
                       canonical_name: Optional[str] = None,
                       full_match: bool = True,
                       prefix_match: bool = True,
                       substring_match: bool = False,
                       ) -> RegexRoute:
    # case sensitivity
    flags = re.U
    if not case:
        flags |= re.I

    # check for slash
    slash = '/'
    if allow_backslash:
        slash = r'[/\\]'
    if allow_noslash:
        slash += '?'

    # argument pattern
    if argument_pattern is None:
        arg = ''
    elif boundary:
        arg = rf'(?:\s+(?P<argument>{argument_pattern.pattern}))?'
    else:
        arg = rf'(?:\s*(?P<argument>{argument_pattern.pattern}))?'

    # boundary checking
    if boundary:
        pattern = re.compile(rf'(?:^|\s)(?P<command>{slash}{re.escape(command)}){arg}(?:\b|$)', flags=flags)
    else:
        pattern = re.compile(rf'(?P<command>{slash}{re.escape(command)}){arg}', flags=flags)

    # create route
    return make_regex_route(endpoint,
                            pattern,
                            canonical_name=canonical_name,
                            full_match=full_match,
                            prefix_match=prefix_match,
                            substring_match=substring_match,
                            )


def make_regex_route(endpoint: LenientEndpoint,
                     pattern: Pattern,
                     canonical_name: Optional[str] = None,
                     full_match: bool = True,
                     prefix_match: bool = False,
                     substring_match: bool = False,
                     ) -> RegexRoute:
    # allow these matches only
    allowed_matches = set()
    if full_match:
        allowed_matches.add(Match.FULL_MATCH)
    if prefix_match:
        allowed_matches.add(Match.PREFIX_MATCH)
    if substring_match:
        allowed_matches.add(Match.SUBSTRING_MATCH)
    if not allowed_matches:
        raise ValueError('no matches allowed')

    # create route
    return RegexRoute(endpoint=make_endpoint(endpoint),
                      pattern=pattern,
                      allowed_matches=allowed_matches,
                      canonical_name=canonical_name,
                      )
