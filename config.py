import json

BOT_USERNAMES = {
    'hawker_centre_bot',  # prod
    'hawker_center_bot',  # dev
}

with open('secrets.json') as f:
    SECRETS = json.load(f)
