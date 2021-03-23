import json
from dataclasses import dataclass

import requests

from api_wrappers.location import Location


@dataclass
class Forecast(Location):
    # inherits latitude and longitude
    name: str
    forecast: str


def weather_now():
    r = requests.get('https://api.data.gov.sg/v1/environment/2-hour-weather-forecast')
    area_metadata = json.loads(r.content).get('area_metadata', [])
    items = json.loads(r.content).get('items', [])
    if not items:
        return
    assert len(items[0]['forecasts']) == len(area_metadata)
    return json.loads(r.content)  # todo: merge metadata and items


def weather_today():
    r = requests.get('https://api.data.gov.sg/v1/environment/24-hour-weather-forecast')
    items = json.loads(r.content).get('items', [])
    if not items:
        return
    return items[0]


def weather_forecast():
    r = requests.get('https://api.data.gov.sg/v1/environment/4-day-weather-forecast')
    items = json.loads(r.content).get('items', [])
    if not items:
        return
    return items[0]


if __name__ == '__main__':
    print(json.dumps(weather_now(), indent=4))
    f = Forecast()
