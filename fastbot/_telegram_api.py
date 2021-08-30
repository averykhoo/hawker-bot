"""
stuff all the python-telegram-bot imports in one file
because `telegram` doesn't matched the package name, so the linter thinks it's an undeclared dependency
and I don't want to have to deal with tagging every single import with a noinspection flag
so I'll just leave them all here and ignore the linter warnings for this file
"""
from telegram import ChatAction
from telegram import InlineQueryResultArticle
from telegram import InlineQueryResultVenue
from telegram import InputTextMessageContent
from telegram import ParseMode
from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.ext import InlineQueryHandler
from telegram.ext import MessageFilter
from telegram.ext import MessageHandler
from telegram.ext import Updater

__all__ = (
    'CallbackContext',
    'ChatAction',
    'CommandHandler',
    'Filters',
    'InlineQueryHandler',
    'InlineQueryResultArticle',
    'InlineQueryResultVenue',
    'InputTextMessageContent',
    'MessageFilter',
    'MessageHandler',
    'ParseMode',
    'Update',
    'Updater',
)
