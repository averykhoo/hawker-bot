from dataclasses import dataclass
from dataclasses import field
from re import Pattern
from typing import Callable
from typing import List
# noinspection PyPackageRequirements
from typing import Union

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


@dataclass
class Router:
    routes: List[Route] = field(default_factory=list, init=False)

    def match(self, message: Message) -> Match:
        if not message.text:
            return Match.NO_MATCH

        best_match = Match.NO_MATCH
        for route in self.routes:
            best_match = max(best_match, route.match(message))
            if best_match == Match.FULL_MATCH:
                return best_match

        return best_match

    def handle_message(self, message: Message):
        if not message.text:
            return Match.NO_MATCH

        partial_match = None
        any_match = None
        for route in self.routes:
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
                arg: Union[str, Callable],
                /,
                *,
                case: bool = False,
                substring_match: bool = False,
                boundary: bool = True,
                ) -> Union[Endpoint, Callable[[Endpoint], Endpoint]]:

        # check if this is a decorator initialization
        if isinstance(arg, str):
            def decorator(endpoint: Endpoint):
                self.routes.append(make_keyword_route(endpoint=endpoint,
                                                      word=arg,
                                                      case=case,
                                                      substring_match=substring_match,
                                                      boundary=boundary))
                return endpoint

            return decorator

        # nope, this is being called as a decorator
        assert isinstance(arg, Callable)
        self.routes.append(make_keyword_route(endpoint=arg,
                                              word=arg.__name__,  # take function name as keyword
                                              case=case,
                                              substring_match=substring_match,
                                              boundary=boundary))
        return arg

    def command(self,
                arg: Union[str, Callable],
                /,
                *,
                case: bool = False,
                allow_backslash: bool = False,
                allow_noslash: bool = False,
                boundary: bool = True,
                ) -> Union[Endpoint, Callable[[Endpoint], Endpoint]]:

        # check if this is a decorator initialization
        if isinstance(arg, str):
            def decorator(endpoint: Endpoint):
                self.routes.append(make_command_route(endpoint=endpoint,
                                                      word=arg,
                                                      case=case,
                                                      allow_backslash=allow_backslash,
                                                      allow_noslash=allow_noslash,
                                                      boundary=boundary))
                return endpoint

            return decorator

        # nope, this is being called as a decorator
        assert isinstance(arg, Callable)
        self.routes.append(make_command_route(endpoint=arg,
                                              word=arg.__name__,  # take function name as keyword
                                              case=case,
                                              allow_backslash=allow_backslash,
                                              allow_noslash=allow_noslash,
                                              boundary=boundary))
        return arg

    def regex(self,
              pattern: Pattern,
              /,
              *,
              full_match: bool = True,
              prefix_match: bool = False,
              substring_match: bool = False,
              ) -> Union[Endpoint, Callable[[Endpoint], Endpoint]]:

        # this MUST a decorator initialization
        assert isinstance(pattern, Pattern)

        def decorator(endpoint: Endpoint):
            self.routes.append(make_regex_route(endpoint=endpoint,
                                                pattern=pattern,
                                                full_match=full_match,
                                                prefix_match=prefix_match,
                                                substring_match=substring_match))
            return endpoint

        return decorator
