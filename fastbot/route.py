import inspect
import re
from dataclasses import dataclass
from dataclasses import field
from enum import IntEnum
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Dict
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
ResponseIterator = Union[None, AnyResponse, Iterable[AnyResponse], Generator[AnyResponse, Any, None]]
Endpoint = TypeVar('Endpoint', bound=Callable[..., ResponseIterator])
StrictEndpoint = TypeVar('StrictEndpoint', bound=Callable[[Message], List[Response]])


def normalize_responses(responses: ResponseIterator,
                        ) -> List[Response]:
    # todo: this should be an iterator
    # todo: this should handle errors and still send everything before the error
    # todo: retry on error?
    if responses is None:
        return []
    if isinstance(responses, (Response, str, Path)):
        return [normalize_response(responses)]
    elif isinstance(responses, (Iterable, Generator)):
        return list(map(normalize_response, responses))
    else:
        raise TypeError(responses)


class Match(IntEnum):
    FULL_MATCH = 3
    PREFIX_MATCH = 2
    SUBSTRING_MATCH = 1
    NO_MATCH = 0


@dataclass(frozen=True)
class Route:
    endpoint: Endpoint
    _message_converters: Dict[str, Callable] = field(default_factory=dict, init=False, repr=False, compare=False)

    def __post_init__(self):
        # get all argument names and types
        arg_names = list(inspect.signature(self.endpoint).parameters.keys())
        arg_types = {arg_name: arg_type
                     for arg_name, arg_type in self.endpoint.__annotations__.items()
                     if arg_name != 'return'}

        # inline function taking no input
        if len(arg_names) == 0:
            return

        # singleton untyped argument, assume Message
        if len(arg_types) == 0 and len(arg_names) == 1:
            self._message_converters[arg_names[0]] = lambda m: m
            return

        # can't predict what this function expects to receive
        if len(arg_types) != len(arg_names):
            print(arg_types)
            print(arg_names)
            raise TypeError(self.endpoint)

        # check type signature and convert message appropriately
        for arg_name, arg_type in arg_types.items():
            if arg_type == Message:
                self._message_converters[arg_name] = lambda m: m
            elif arg_type == Update:
                self._message_converters[arg_name] = lambda m: m.update
            elif arg_type == CallbackContext:
                self._message_converters[arg_name] = lambda m: m.context
            else:
                raise TypeError(self.endpoint)

    def strict_endpoint(self, message: Message) -> List[Response]:
        kwargs = {name: converter(message) for name, converter in self._message_converters.items()}
        return normalize_responses(self.endpoint(**kwargs))

    def handle_message(self, message: Message) -> None:
        ret = self.strict_endpoint(message)
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

        message.matched = match
        message.command = self.canonical_name

        super().handle_message(message)

    def callback(self,
                 update: Update,
                 context: CallbackContext,
                 ) -> None:
        self.handle_message(Message(update, context))


def make_keyword_route(endpoint: Endpoint,
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


def make_command_route(endpoint: Endpoint,
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


def make_regex_route(endpoint: Endpoint,
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
    return RegexRoute(endpoint=endpoint,
                      pattern=pattern,
                      allowed_matches=allowed_matches,
                      canonical_name=canonical_name,
                      )
