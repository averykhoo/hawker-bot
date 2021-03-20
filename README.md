#   hawker-bot

##  usage
*   optionally, install [`geographiclib-cython-bindings`](https://pypi.org/project/geographiclib-cython-bindings/)

##  todo
*   auto-handle telegram quotas by rate limiting message sending
*   support being in telegram groups
    *   eg. receiving all messages
    *   or only commands (private mode)
*   command list
*   inline mode (search)
*   get user timezone
*   commands
    *   closed: search only closed soon
    *   zip: search nearby geocoded zip codes
    *   follow unfollow
    *   stop/exit/quit/mute 
    *   delete-all-data
    *   share deeplink to bot (private/group)
    *   about bot, link to git
    *   refresh: reload all resources
    *   list all hawkers
*   filter out unconstructed hawkers or with no food stalls
*   what is telegram context and how to use it
*   pull new data
    *   build internal data.gov
    *   build onemap query python api
    *   update app data on the fly
*   logging
*   stats
*   prod and staging tokens
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
