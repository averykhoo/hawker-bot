import json
from dataclasses import dataclass
from re import Match
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from fastbot._telegram_api import CallbackContext
from fastbot._telegram_api import Update
from fastbot.response import Response


@dataclass
class Message:
    update: Update
    context: CallbackContext
    matched: Optional[Match] = None  # matched command string
    command: Optional[str] = None  # canonical command name

    @property
    def text(self) -> str:
        return self.update.effective_message.text.strip()

    @property
    def argument(self) -> Optional[str]:
        if self.matched is not None:
            assert len(self.matched.groups()) > 0, (self.text, self.matched)
            assert len(self.matched.groupdict()) > 0, (self.text, self.matched)

            if 'argument' in self.matched.groupdict():
                return self.matched.group('argument')

            assert 'command' in self.matched.groupdict(), (self.text, self.matched)
            for group_idx, group_text in enumerate(self.matched.groups()):
                if group_text == self.matched.group('command'):
                    start_pos, end_pos = self.matched.span(group_idx + 1)  # group 0 is the full matched
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
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def reply(self, responses: List[Response]):
        for response in responses:
            response.send_reply(self.update)
