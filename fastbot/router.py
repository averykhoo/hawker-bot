from dataclasses import dataclass
from typing import List

# noinspection PyPackageRequirements
from telegram import Update
# noinspection PyPackageRequirements
from telegram.ext import CallbackContext

from fastbot.message import Message
from fastbot.route import Match
from fastbot.route import Route


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
