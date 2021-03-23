#   hawker-bot

##  setup
*   optionally, install [`geographiclib-cython-bindings`](https://pypi.org/project/geographiclib-cython-bindings/)
*   update command list via @BotFather `/setcommands` with contents of *setcommands.txt*
*   allow inline mode via @BotFather `/setinline`

##  todo
*   major refactoring
    *   better way to handle command aliases
        *   try to auto-generate *setcommands.txt*
        *   declarative, so it's possible to autocorrect missing slash
        *   specify number of expected arguments, so it's possible to auto-split and autocorrect multi-word commands
    *   split code into separate groups of handler functions
        *   group 1: debug log
        *   group 2: did you mean / autocorrect
            *   no starting / for command (eg. 'today', 'tomorrow', 'week', 'help', etc)
            *   missing space (eg. '/zip120726', '/onemapclementi')
        *   group 3: weather
            *   location
            *   today
            *   tomorrow
            *   week?
        *   group 4: hawker stuff
    *   provide an aliases file, then download *hawkercentre.kml* from onemap?
    *   hawker centre set
        *   find_by_text
        *   find_by_location
    *   data api
        *   onemap
            *   zip
            *   query
            *   hawkercentre.kml
        *   data gov
            *   check metadata for revision ID before updating?
            *   weather
            *   hawker centre closed dates
*   i18n via json file? how to handle string formatting?
*   improvements to messaging
    *   message queue per-user with auto-terminate if user sends new thing
    *   reply coalescing
    *   handle duplicate messages due to bot lag
    *   auto-handle telegram quotas by rate limiting message sending
    *   auto-handle message_too_long by breaking messages up into chunks < 4096 chars
*   support being in telegram groups
    *   eg. receiving all messages
    *   or only commands (private mode)
*   commands
    *   follow unfollow
    *   stop/exit/quit/mute 
    *   delete-all-data
    *   share deeplink to bot? (private/group)
    *   refresh: reload all resources
    *   ~~list all hawkers~~ (400 MESSAGE_TOO_LONG)
*   what is telegram context and how to use it
*   pull new data
    *   build internal data.gov
    *   build onemap query python api
    *   update app data on the fly
*   stats
*   follow
    *   specific hawker centers
    *   everyday or only on specific days or some kind of schedule
    *   manage follows
*   special handling for edited/deleted messages?
*   special handling for edited location (ongoing sharing)
    *   don't spam everything
    *   within radius (maybe always within radius?)
    *   needs in-mem cache or a user database for this to work, can't be stateless
*   fast api backend for tele bot frontend
*   cache all resources, eg. images
*   user database
    *   telegram username
    *   received messages
    *   locations
    *   messages
    *   files
    *   etc
    *   locale, timezone, language
    *   followed
        *   hawker centres
        *   update days
    *   is-deleted
*   format_distance_metric and format_distance_imperial
