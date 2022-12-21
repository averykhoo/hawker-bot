# Hawker Centre Bot

A bot to find hawker centres and figure out when they are closed

## Usage: [@hawker_centre_bot](https://t.me/hawker_centre_bot) on Telegram

* `/start`
* Most useful features can be used from the commands menu
    * Several commands also work even without the `/` prefix, if you prefer to type
* Send a location or road name as plaintext to find nearby hawker centers
* Send a postal code to find nearby hawker centers
* Share your location to find nearby hawker centers
    * Not recommended to share continuously, you'll be spammed with hawker centers whenever you move

## To set up a copy of this bot

* `git pull`
* `pip install -r requirements.txt`
    * Optionally `pip install geographiclib-cython-bindings`
* Create *secrets.json* with appropriate entries (see [secrets.example.json](./secrets.example.json))
* Update command list via @BotFather `/setcommands` with contents of [setcommands.txt](./templates/setcommands.txt)
* Also update `/setdescription` with contents of [setdescription.txt](./templates/setdescription.txt)
* Allow inline mode via @BotFather `/setinline`