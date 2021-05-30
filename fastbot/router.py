from dataclasses import dataclass
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
from fastbot.route import make_keyword_route


@dataclass
class Router:
    routes: List[Route]

    def handle_message(self, update: Update, context: CallbackContext):
        message = Message(update, context)
        if not message.text:
            return Match.NO_MATCH

        partial_match = None
        any_match = None
        for route in self.routes:
            match = route.match(message)
            if match == Match.FULL_MATCH:
                route.callback(message)
                return Match.FULL_MATCH
            elif match == Match.PREFIX_MATCH and partial_match is None:
                partial_match = route
            elif match == Match.SUBSTRING_MATCH and any_match is None:
                any_match = route

            if partial_match is not None:
                partial_match.callback(message)
                return Match.PREFIX_MATCH

            if any_match is not None:
                any_match.callback(message)
                return Match.SUBSTRING_MATCH

            return Match.NO_MATCH

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
