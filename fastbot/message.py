import json
from dataclasses import dataclass
from typing import Any
from typing import Dict
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

    @property
    def text(self) -> str:
        return self.update.effective_message.text.strip()

    @property
    def argument(self) -> Optional[str]:
        if self.prefix is not None:
            assert self.text.startswith(self.prefix)
            return self.text[len(self.prefix):].strip()

    @property
    def via_bot(self):
        return self.update.effective_message.via_bot

    def to_dict(self) -> Dict[str, Any]:
        return self.update.to_dict()

    def to_json(self) -> str:
        return json.dumps(self.update.to_dict())
