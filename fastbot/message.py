import json
from dataclasses import dataclass
from re import Match
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

# noinspection PyPackageRequirements
from telegram import Update
# noinspection PyPackageRequirements
from telegram.ext import CallbackContext

from fastbot.response import Response


@dataclass
class Message:
    update: Update
    context: CallbackContext
    match: Optional[Match] = None  # matched command string
    command: Optional[str] = None  # canonical command name

    @property
    def text(self) -> str:
        return self.update.effective_message.text.strip()

    @property
    def argument(self) -> Optional[str]:
        if self.match is not None:
            assert len(self.match.groups()) > 0, (self.text, self.match)
            assert len(self.match.groupdict()) > 0, (self.text, self.match)

            if 'argument' in self.match.groupdict():
                return self.match.group('argument')

            assert 'command' in self.match.groupdict(), (self.text, self.match)
            for group_idx, group_text in enumerate(self.match.groups()):
                if group_text == self.match.group('command'):
                    start_pos, end_pos = self.match.span(group_idx + 1)  # group 0 is the full match
                    return self.text[end_pos:].strip()

    @property
    def via_bot(self):
        return self.update.effective_message.via_bot

    def to_dict(self) -> Dict[str, Any]:
        if self.update is None:
            return {}
        else:
            return self.update.to_dict()

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def reply(self, responses: List[Response]):
        for response in responses:
            response.send_reply(self.update)
