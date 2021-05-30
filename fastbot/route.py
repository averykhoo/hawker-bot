import re
from dataclasses import dataclass
from enum import Enum
from typing import Any
from typing import Callable
from typing import Generator
from typing import Iterable
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


class Match(Enum):
    FULL_MATCH = 1
    PREFIX_MATCH = 2
    SUBSTRING_MATCH = 3
    NO_MATCH = 4


@dataclass(frozen=True)
class Route:
    pattern: Pattern
    endpoint: Endpoint
    allowed_matches: Set[Match]

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

    def callback(self, message: Message) -> None:
        match = self.pattern.search(message.text)
        assert match is not None, self.pattern
        assert len(match.groups()) > 0, match
        assert len(match.groupdict()) > 0, match
        assert 'command' in match.groupdict(), match

        message.prefix = match.groupdict('command')

        ret = self.endpoint(message)

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


def _make_keyword_route(endpoint: Endpoint,
                        word: str,
                        case: bool = False,
                        substring_match: bool = False,
                        boundary: bool = True,
                        ) -> Route:
    # case sensitivity
    flags = re.U
    if not case:
        flags |= re.I

    # substring match: respect boundaries
    if substring_match:
        allowed_matches = {Match.FULL_MATCH, Match.PREFIX_MATCH, Match.SUBSTRING_MATCH}
    else:
        allowed_matches = {Match.FULL_MATCH}

    # boundary checking
    if boundary:
        pattern = re.compile(rf'(?P<command>(?:^|\b){re.escape(word)}(?:\b|$))', flags=flags)
    else:
        pattern = re.compile(rf'(?P<command>{re.escape(word)})', flags=flags)

    # create route
    return Route(pattern, endpoint, allowed_matches)


def _make_command_route(endpoint: Endpoint,
                        word: str,
                        case: bool = False,
                        allow_backslash: bool = False,
                        allow_noslash: bool = False,
                        boundary: bool = True,
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

    # allow prefix matches only
    allowed_matches = {Match.FULL_MATCH, Match.PREFIX_MATCH}

    # boundary checking
    if boundary:
        pattern = re.compile(rf'(?P<command>(?:^|\s){slash}{re.escape(word)}(?:\b|$))', flags=flags)
    else:
        pattern = re.compile(rf'(?P<command>{slash}{re.escape(word)})', flags=flags)

    # create route
    return Route(pattern, endpoint, allowed_matches)


def _make_regex_route(endpoint: Endpoint,
                      pattern: Pattern,
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
    return Route(pattern, endpoint, allowed_matches)


def keyword(arg,
            /,
            *,
            case: bool = False,
            substring_match: bool = False,
            boundary: bool = True,
            ) -> Union[Endpoint, Callable[[Endpoint], Endpoint]]:
    # check if this is a decorator initialization
    if isinstance(arg, str):
        def decorator(endpoint: Endpoint):
            _make_keyword_route(endpoint=endpoint,
                                word=arg,
                                case=case,
                                substring_match=substring_match,
                                boundary=boundary)
            return endpoint

        return decorator

    # nope, this is being called as a decorator
    assert isinstance(arg, Callable)
    _make_keyword_route(endpoint=arg,
                        word=arg.__name__,  # take function name as keyword
                        case=case,
                        substring_match=substring_match,
                        boundary=boundary)
    return arg
