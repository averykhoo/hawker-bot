import re
from dataclasses import dataclass
from dataclasses import field
from re import Pattern
from typing import Callable
from typing import List

from telegram import Update
# noinspection PyPackageRequirements
from telegram.ext import CallbackContext

from fastbot.message import Message
from fastbot.route import Endpoint
from fastbot.route import Match
from fastbot.route import Route
from fastbot.route import make_command_route
from fastbot.route import make_keyword_route
from fastbot.route import make_regex_route


# noinspection PyPackageRequirements


@dataclass
class Router:
    __routes: List[Route] = field(default_factory=list, init=False)
    __default = None

    @property
    def routes(self):
        if self.__default is None:
            return self.__routes[:]
        else:
            return self.__routes + [self.__default]

    def match(self, message: Message) -> Match:
        if not message.text:
            return Match.NO_MATCH

        best_match = Match.NO_MATCH
        for route in self.__routes + [self.__default]:
            best_match = max(best_match, route.match(message))
            if best_match == Match.FULL_MATCH:
                return best_match

        return best_match

    def handle_message(self, message: Message):
        if not message.text:
            return Match.NO_MATCH

        partial_match = None
        any_match = None
        for route in self.__routes + [self.__default]:
            match = route.match(message)

            if match == Match.FULL_MATCH:
                route.handle_message(message)
                return Match.FULL_MATCH
            elif match == Match.PREFIX_MATCH and partial_match is None:
                partial_match = route
            elif match == Match.SUBSTRING_MATCH and any_match is None:
                any_match = route

        if partial_match is not None:
            partial_match.handle_message(message)
            return Match.PREFIX_MATCH

        if any_match is not None:
            any_match.handle_message(message)
            return Match.SUBSTRING_MATCH

        return Match.NO_MATCH

    def callback(self,
                 update: Update,
                 context: CallbackContext,
                 ) -> None:
        self.handle_message(Message(update, context))

    def keyword(self,
                word: str,
                /,
                *,
                case: bool = False,
                boundary: bool = True,
                full_match: bool = True,
                prefix_match: bool = False,
                substring_match: bool = False,
                ) -> Callable[[Endpoint], Endpoint]:
        assert isinstance(word, str)

        def decorator(endpoint: Endpoint):
            self.__routes.append(make_keyword_route(endpoint=endpoint,
                                                    keyword=word,
                                                    case=case,
                                                    boundary=boundary,
                                                    full_match=full_match,
                                                    prefix_match=prefix_match,
                                                    substring_match=substring_match,
                                                    ))
            return endpoint

        return decorator

    def command(self,
                cmd: str,
                /,
                *,
                case: bool = False,
                allow_backslash: bool = False,
                allow_noslash: bool = False,
                boundary: bool = True,
                full_match: bool = True,
                prefix_match: bool = False,
                substring_match: bool = False,
                ) -> Callable[[Endpoint], Endpoint]:
        assert isinstance(cmd, str)

        def decorator(endpoint: Endpoint):
            self.__routes.append(make_command_route(endpoint=endpoint,
                                                    command=cmd,
                                                    case=case,
                                                    allow_backslash=allow_backslash,
                                                    allow_noslash=allow_noslash,
                                                    boundary=boundary,
                                                    full_match=full_match,
                                                    prefix_match=prefix_match,
                                                    substring_match=substring_match,
                                                    ))
            return endpoint

        return decorator

    def regex(self,
              pattern: Pattern,
              /,
              *,
              full_match: bool = True,
              prefix_match: bool = False,
              substring_match: bool = False,
              ) -> Callable[[Endpoint], Endpoint]:
        assert isinstance(pattern, Pattern)

        def decorator(endpoint: Endpoint):
            self.__routes.append(make_regex_route(endpoint=endpoint,
                                                  pattern=pattern,
                                                  full_match=full_match,
                                                  prefix_match=prefix_match,
                                                  substring_match=substring_match))
            return endpoint

        return decorator

    def default(self, endpoint: Endpoint) -> Endpoint:
        # RE_COMMAND = re.compile(r'(?P<cmd>[/\\][a-zA-Z0-9_]{1,64})(?![a-zA-Z0-9_])')
        assert self.__default is None
        self.__default = make_regex_route(endpoint=endpoint,
                                          pattern=re.compile(r'(?P<command>[\s\S]+?)'),
                                          full_match=True,
                                          prefix_match=True,
                                          substring_match=True)
        return endpoint
