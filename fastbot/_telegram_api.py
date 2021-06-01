"""
stuff all the python-telegram-bot imports in one file
because `telegram` doesn't match the package name, so the linter thinks it's an undeclared dependency
and I don't want to have to deal with tagging every single import with a noinspection flag
"""

# noinspection PyPackageRequirements
import telegram.ext

InlineQueryResultArticle = telegram.InlineQueryResultArticle
InlineQueryResultVenue = telegram.InlineQueryResultVenue
InputTextMessageContent = telegram.InputTextMessageContent
ParseMode = telegram.ParseMode
Update = telegram.Update

CallbackContext = telegram.ext.CallbackContext
CommandHandler = telegram.ext.CommandHandler
Filters = telegram.ext.Filters
InlineQueryHandler = telegram.ext.InlineQueryHandler
MessageFilter = telegram.ext.MessageFilter
MessageHandler = telegram.ext.MessageHandler
Updater = telegram.ext.Updater
