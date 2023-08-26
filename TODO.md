# todo list

* sort by walking distance instead of straight line distance
  * maybe min is straight line and max is straight line * sqrt(2) or * pi/2? 
  * clamping it should help avoid weird errors if the routing goes haywire
  * but then if you want to cross a river it's not wrong - maybe error percentage should decrease with distance?
* major refactoring
  * data api and datatypes
    * gracefully detect and handle api downtime
    * onemap
      * zip
      * query
      * hawkercentre.kml
    * data gov sg
      * check metadata for revision ID before updating?
      * weather
      * hawker centre closed dates
    * google maps api (free)
      * https://github.com/googlemaps/google-maps-services-python
      * https://developers.google.com/maps/gmp-get-started
      * ratings, geocoding, reverse geocoding, place_id
  * some kind of data handling that can be synced live from external sources
    * syncing allowed to fail for up to 1 week
    * cross-references need to be fuzzy because names and latlongs don't always match
  * better way to handle command aliases
    * try to auto-generate *setcommands.txt*
    * declarative, so it's possible to autocorrect missing slash
    * specify number of expected arguments, so it's possible to auto-split and autocorrect multi-word commands
  * split code into separate groups of handler functions
    * group 1: enrichment
      * fuzzy match command (aka. did you mean / autocorrect)
        *   [x] no starting / for command (eg. 'today', 'tomorrow', 'week', 'help', etc)
        * missing space (eg. '/zip120726', '/onemapclementi')
      * context from the previous query (only possible after user-db is set up)
      * detect region name (eg. ang mo kio, clementi)
        * detect mrt station name
    * group 2: logging
      *   [x] debug log the json message
      * stats collection
        * query types (inline, image, command, text, fuzzy command, location, video, audio, document, etc)
        * command frequency
          * include fuzzy commands
          * include invalid commands
        * most common hawker centres
    * group 3: filtering
      * via self
      * forwarded from self
      * sanity checks: blank, non-ascii, etc
    * group 4: weather
      * location
      * today
      * tomorrow
      * week?
    * group 5: hawker stuff
    * group 6: contextual additional processes
      * offer buttons for contextual followup queries
  * better structured `handle_text` (assuming it's non-blank, longer than 1 char, and not a command)
    * exact match
      * zipcode exact match
      * hawker exact name match
    * fuzzy
      * hawker fuzzy string match
      * zipcode regex match -> nearby hawkers
      * onemap search
  * provide a hawker aliases file, then download *hawkercentre.kml* from onemap?
    * as opposed to the current method of hardcoding in NEA's hawker list
  * hawker centre set
    * find_by_text
    * find_by_location
    * use a better data structure for nearby lookup
* multilingual handling
  * i18n via json file? how to handle string formatting?
  * https://data.gov.sg/dataset/train-station-chinese-names
    * https://en.wikipedia.org/wiki/List_of_Singapore_MRT_stations
  * any free translate api?
* improvements to messaging
  * message queue per-user with auto-terminate if user sends new thing
  * reply coalescing
  * handle duplicate messages due to bot lag
  * auto-handle telegram quotas by rate limiting message sending
  * auto-handle message_too_long by breaking messages up into chunks < 4096 chars
* support being in telegram groups
  * eg. receiving all messages
  * or only commands (private mode)
* commands
  * follow unfollow
  * stop/exit/quit/mute
  * delete-all-data
  * share deeplink to bot? (private/group)
  * refresh: reload all resources
  * ~~list all hawkers~~ (400 MESSAGE_TOO_LONG)
* what is telegram context and how to use it
* pull new data
  * build internal data.gov
  * build onemap query python api
  * update app data on the fly
* follow
  * specific hawker centers
  * everyday or only on specific days or some kind of schedule
  * manage follows
* special handling for edited/deleted messages?
* special handling for edited location (ongoing sharing)
  * don't spam everything
  * within radius (maybe always within radius?)
  * needs in-mem cache or a user database for this to work, can't be stateless
* fast api backend for tele bot frontend
* cache all resources, eg. images
* user database
  * telegram username
  * received messages
  * locations
  * messages
  * files
  * etc
  * locale, timezone, language
  * followed
    * hawker centres
    * update days
  * is-deleted
* weather
  * sanity check that dates are current (to detect if the api breaks again)
  * [UVI](https://data.gov.sg/dataset/ultraviolet-index-uvi)
  * https://data.gov.sg/dataset/realtime-weather-readings
  * [PSI](https://data.gov.sg/dataset/psi)
  * [PM2.5](https://data.gov.sg/dataset/pm2-5)
  * at location as optional argument
    * mrt station
    * grc / region / planning area name
  * where is it currently raining
    * rain area maps
      * maybe as gifs?
        * "Overlay an image on another image in Python -
          GeeksforGeeks" https://www-geeksforgeeks-org.cdn.ampproject.org/v/s/www.geeksforgeeks.org/overlay-an-image-on-another-image-in-python/amp/?amp_gsa=1&amp_js_v=a6&usqp=mq331AQKKAFQArABIIACAw%3D%3D#amp_tf=From%2
        * "Programmatically generate video or animated GIF in Python? - Stack
          Overflow" https://stackoverflow.com/questions/753190/programmatically-generate-video-or-animated-gif-in-python
        * or maybe use deep learning to predict future maps and alert ahead of time?
    * weather station data