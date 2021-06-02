import logging

import config
import utils
from fastbot import FastBot
from fastbot import Message
from fastbot import Text

# set up logging appropriately
utils.setup_logging(app_name='hawker-bot-dev-redirect')

# # disable SSL verification
# utils.no_ssl_verification()

# create bot
bot = FastBot(config.SECRETS['hawker_center_bot_token (dev)'])


@bot.logger
def log_message(message: Message):
    logging.info(f'MESSAGE_JSON={message.to_json()}')


@bot.unrecognized
@bot.default
def redirect(_: Message):
    return Text('Please use @hawker_centre_bot', notification=False)


@bot.error
def error(message: Message):
    logging.warning(f'ERROR="{message.context.error}" MESSAGE_JSON={message.to_json()}')
    # raise message.context.error


if __name__ == '__main__':
    bot.run_forever()
