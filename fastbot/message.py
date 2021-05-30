import json
from dataclasses import dataclass
from typing import Optional

# noinspection PyPackageRequirements
from telegram import Update
# noinspection PyPackageRequirements
from telegram.ext import CallbackContext


@dataclass
class Message:
    update: Update
    context: CallbackContext
    prefix: Optional[str] = None

    def __post_init__(self):
        pass  # todo: parse command

    @property
    def text(self):
        return self.update.effective_message.text

    @property
    def argument(self):
        if self.prefix is not None:
            assert self.text.startswith(self.prefix)
            return self.text[len(self.prefix):].strip()

    @property
    def via_bot(self):
        return self.update.effective_message.via_bot

    def to_dict(self):
        return self.update.to_dict()

    def to_json(self):
        return json.dumps(self.update.to_dict())
