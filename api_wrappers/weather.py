import datetime
import json
from dataclasses import dataclass
from pprint import pprint
from typing import Dict
from typing import List
from typing import Tuple

import requests

from api_wrappers.caching import cache_1m
from api_wrappers.location import Location

forecast_details = {  # http://www.weather.gov.sg/forecasting-2/#forecast_3
    # descriptors
    'Rain':              'Steady water droplets that fall from stratiform or layer clouds. '
                         'Tends to affect a wide area, and is more persistent than showers.',
    'Showers':           'Brief precipitation from cumuliform clouds. '
                         'Characterised by the sudden start and end of the precipitation. '
                         'Sometimes occur in spells, and usually localised over an area.',
    'Thundery showers':  'Precipitation from cumulonimbus clouds accompanied by thunder and lightning, '
                         'and sometimes strong wind gusts at the ground. '
                         'Under suitable conditions can produce waterspouts and/or hail.',
    'Fair':              'Generally sunny with few clouds in the sky. '
                         'No occurrence of rain or showers.',
    'Hazy':              'Suspension of particulate matter (e.g. dust, smoke particles) in the air, '
                         'causing reduced visibility.',
    'Partly Cloudy':     'Between 3 eighths and 4 eighths of the sky is covered by clouds. '
                         'It has the same connotation as “partly sunny”, which is a mix of sun and clouds.',
    'Cloudy':            'Between 5 eighths and 7 eighths of the sky is covered by clouds.',
    'Overcast':          'The whole sky is completely covered by cloud, giving dull, grey conditions.',

    # intensity
    'Light (or Slight)': 'Puddles are slow to form, and there is no or slow accumulation of water',
    'Moderate':          'Puddles form rapidly, and some spray visible over hard surfaces',
    'Heavy':             'Rain/showers falling in sheets with misty spray over hard surfaces. '
                         'Can cause flash floods.',

    # duration
    'Occasional':        'Rain or showers occurring at irregular, infrequent intervals.',
    'Intermittent':      'Rain occurring at irregular but frequent intervals',
    'Continuous':        'Rain without any break or with very short breaks',

    # distribution
    'One or two areas':  'Small, localised part of a Region of Singapore affected by rain/showers.',
    'Many areas':        'Large parts of more than two Regions of Singapore affected by rain/showers.',
    'Widespread:':       'Almost all parts or whole of Singapore affected by rain/showers.',

    # time
    'Early hours':       'MN to 4am',
    'Pre-dawn':          '4am to 6am',
    'Early morning':     '6am to 9am',
    'Late morning':      '9am to MD',
    'Morning':           '6am to MD',
    'Early afternoon':   'MD to 3pm',
    'Late afternoon':    '3pm to 6pm',
    'Afternoon':         'MD to 6pm',
    'Evening':           '6pm to 8pm',
    'Night':             '6pm to 6am',
}

region_metadata = {  # https://data.gov.sg/dataset/psi
    'Central': Location(1.35735, 103.82),
    'North':   Location(1.41803, 103.82),
    'South':   Location(1.29587, 103.82),
    'East':    Location(1.35735, 103.94),
    'West':    Location(1.35735, 103.70),
}


@dataclass
class Forecast(Location):
    # inherits latitude and longitude
    name: str
    forecast: str
    last_update: datetime.datetime
    time_start: datetime.datetime
    time_end: datetime.datetime

    def overlaps_time(self, timestamp):
        if not isinstance(timestamp, datetime.datetime):
            raise TypeError(timestamp)
        return self.time_start <= timestamp < self.time_end


@dataclass
class FourDayForecast:
    date: datetime.date
    forecast: str
    # relative_humidity: Tuple[int, int]
    # temperature: Tuple[int, int]
    # wind_direction: str
    # wind_speed: Tuple[int, int]
    # last_update: datetime.datetime


@cache_1m
def weather_2h() -> List[Forecast]:
    fmt = '%Y-%m-%dT%H:%M:%S+08:00'
    r = requests.get('https://api.data.gov.sg/v1/environment/2-hour-weather-forecast')
    data = json.loads(r.content)
    tmp = {item['area']: item['forecast'] for item in data['items'][0]['forecasts']}
    return [Forecast(latitude=item['label_location']['latitude'],
                     longitude=item['label_location']['longitude'],
                     name=item['name'],
                     forecast=tmp[item['name']],
                     last_update=datetime.datetime.strptime(data['items'][0]['update_timestamp'], fmt),
                     time_start=datetime.datetime.strptime(data['items'][0]['valid_period']['start'], fmt),
                     time_end=datetime.datetime.strptime(data['items'][0]['valid_period']['end'], fmt),
                     ) for item in data['area_metadata']]


@cache_1m
def weather_24h() -> List[Forecast]:
    fmt = '%Y-%m-%dT%H:%M:%S+08:00'
    r = requests.get('https://api.data.gov.sg/v1/environment/24-hour-weather-forecast')
    data = json.loads(r.content)
    return [Forecast(latitude=region_metadata[region_name.title()].latitude,
                     longitude=region_metadata[region_name.title()].longitude,
                     name=region_name.title(),
                     forecast=region_forecast,
                     last_update=datetime.datetime.strptime(data['items'][0]['update_timestamp'], fmt),
                     time_start=datetime.datetime.strptime(period['time']['start'], fmt),
                     time_end=datetime.datetime.strptime(period['time']['end'], fmt),
                     ) for period in data['items'][0]['periods']
            for region_name, region_forecast in period['regions'].items()]


@cache_1m
def weather_24h_grouped() -> Dict[Tuple[datetime.datetime, datetime.datetime], List[Forecast]]:
    out = dict()
    for forecast in weather_24h():
        out.setdefault((forecast.time_start, forecast.time_end), []).append(forecast)
    return out


def weather_4d() -> List[FourDayForecast]:
    fmt = '%Y-%m-%dT%H:%M:%S+08:00'
    out = []
    r = requests.get('https://api.data.gov.sg/v1/environment/24-hour-weather-forecast')
    data = json.loads(r.content)
    out.append(FourDayForecast(date=datetime.datetime.strptime(data['items'][0]['timestamp'], fmt).date(),
                               forecast=data['items'][0]['general']['forecast'].rstrip('.'),
                               # relative_humidity=(data['items'][0]['general']['relative_humidity']['low'],
                               #                    data['items'][0]['general']['relative_humidity']['high']),
                               # temperature=(data['items'][0]['general']['temperature']['low'],
                               #              data['items'][0]['general']['temperature']['high']),
                               # wind_direction=data['items'][0]['general']['wind']['direction'],
                               # wind_speed=(data['items'][0]['general']['wind']['speed']['low'],
                               #             data['items'][0]['general']['wind']['speed']['high']),
                               # last_update=data['items'][0]['general']['forecast'],
                               ))
    r = requests.get('https://api.data.gov.sg/v1/environment/4-day-weather-forecast')
    data = json.loads(r.content)
    for forecast in data['items'][0]['forecasts']:
        out.append(FourDayForecast(date=datetime.datetime.strptime(forecast['date'], '%Y-%m-%d').date(),
                                   forecast=forecast['forecast'].rstrip('.'),
                                   # relative_humidity=(forecast['relative_humidity']['low'],
                                   #                    forecast['relative_humidity']['high']),
                                   # temperature=(forecast['temperature']['low'],
                                   #              forecast['temperature']['high']),
                                   # wind_direction=forecast['wind']['direction'],
                                   # wind_speed=(forecast['wind']['speed']['low'],
                                   #             forecast['wind']['speed']['high']),
                                   # last_update=forecast['forecast'],
                                   ))

    return out


if __name__ == '__main__':
    pprint(weather_2h())
    pprint(weather_24h())
    pprint(weather_4d())
