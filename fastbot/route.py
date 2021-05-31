import re
from dataclasses import dataclass
from enum import IntEnum
from typing import Any
from typing import Callable
from typing import Generator
from typing import Iterable
from typing import Optional
from typing import Pattern
from typing import Set
from typing import TypeVar
from typing import Union

from fastbot.message import Message
from fastbot.response import Response
from fastbot.response import Text

# fastapi.types.DecoratedCallable: stricter type inference, guaranteeing same type signature for decorated function
AnyResponse = Union[str, Response]
Endpoint = TypeVar('Endpoint', bound=Callable[[Message], Union[AnyResponse,
                                                               Iterable[AnyResponse],
                                                               Generator[AnyResponse, Any, None]]])


class Match(IntEnum):
    FULL_MATCH = 3
    PREFIX_MATCH = 2
    SUBSTRING_MATCH = 1
    NO_MATCH = 0


@dataclass(frozen=True)
class Route:
    pattern: Pattern
    endpoint: Endpoint
    allowed_matches: Set[Match]
    canonical_name: Optional[str] = None

    def __post_init__(self):
        print(self)

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
        # assert len(match.groups()) > 0, (self.pattern, match)
        # assert len(match.groupdict()) > 0, (self.pattern, match)
        # assert 'command' in match.groupdict(), (self.pattern, match)

        message.match = match
        message.command = self.canonical_name

        ret = self.endpoint(message)
        if ret is not None:
            if isinstance(ret, Response):
                responses = [ret]
            elif isinstance(ret, str):
                responses = [Text(ret)]
            elif isinstance(ret, (Iterable, Generator)):
                responses = []
                for response in ret:
                    if isinstance(response, Response):
                        responses.append(response)
                    elif isinstance(response, str):
                        responses.append(Text(response))
                    else:
                        raise TypeError(response)
            else:
                raise TypeError(ret)

            for response in responses:
                response.send(message)


def make_keyword_route(endpoint: Endpoint,
                       keyword: str,
                       case: bool = False,
                       boundary: bool = True,
                       canonical_name: Optional[str] = None,
                       full_match: bool = True,
                       prefix_match: bool = False,
                       substring_match: bool = False,
                       ) -> Route:
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
                       allow_backslash: bool = False,
                       allow_noslash: bool = False,
                       boundary: bool = True,
                       canonical_name: Optional[str] = None,
                       full_match: bool = True,
                       prefix_match: bool = True,
                       substring_match: bool = False,
                       ) -> Route:
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
                     ) -> Route:
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
    return Route(pattern=pattern,
                 endpoint=endpoint,
                 allowed_matches=allowed_matches,
                 canonical_name=canonical_name,
                 )
