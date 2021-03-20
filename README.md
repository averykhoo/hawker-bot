#   hawker-bot

##  usage
*   optionally, install [`geographiclib-cython-bindings`](https://pypi.org/project/geographiclib-cython-bindings/)

##  todo
*   inline mode (search)
*   message queue per-user with auto-terminate if user sends new thing
*   update command list via @BotFather `/setcommands`
*   auto-handle telegram quotas by rate limiting message sending
*   auto-handle message_too_long by breaking messages up into chunks < 4096 chars
*   support being in telegram groups
    *   eg. receiving all messages
    *   or only commands (private mode)
*   get user timezone
*   commands
    *   follow unfollow
    *   stop/exit/quit/mute 
    *   delete-all-data
    *   share deeplink to bot (private/group)
    *   refresh: reload all resources
    *   ~~list all hawkers~~ (400 MESSAGE_TOO_LONG)
*   filter out unconstructed hawkers or with no food stalls
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
*   
