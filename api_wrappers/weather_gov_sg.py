import datetime
import json
from dataclasses import dataclass
from pprint import pprint
from typing import Optional

import requests

from api_wrappers.location import Location


@dataclass
class WeatherStationReading(Location):
    # latitude and longitude inherited from Location
    name: str
    id: str

    measurement_timestamp: Optional[datetime.datetime] = None  # recorded_date
    rain_mm: Optional[float] = None  # rain_mm
    relative_humidity: Optional[float] = None  # relative_humidity
    temperature_celcius: Optional[float] = None  # temp_celcius
    wind_direction: Optional[int] = None  # wind_direction (degrees?)
    wind_speed_knots: Optional[float] = None  # wind_speed_knots
    wind_speed_kpr: Optional[float] = None  # wind_speed_kpr

    visibility_km: Optional[int] = None  # visKM
    visibility_timestamp: Optional[datetime.datetime] = None  # visTime

    @property
    def is_blank(self):
        self_properties = [
            self.measurement_timestamp,
            self.rain_mm,
            self.relative_humidity,
            self.temperature_celcius,
            self.wind_direction,
            self.wind_speed_knots,
            self.wind_speed_kpr,
            self.visibility_km,
            self.visibility_timestamp,
        ]

        return all(elem is None for elem in self_properties)


def get_img():
    r = requests.get('http://www.weather.gov.sg/mobile/json/rest-get-latest-observation-for-all-locs.json')
    data = json.loads(r.content)

    rainfall_img_url = data['data']['rainfall_img_url']
    r = requests.get('http://www.weather.gov.sg/files/isohyet/isohyetmidnight.png')

    temperature_img_url = data['data']['temp_img_url']
    r = requests.get('http://www.weather.gov.sg/files/isotherm/isotherm.png')


def _parse_recorded_date(timestamp):
    return datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')


def _parse_visibility_timestamp(timestamp):
    return datetime.datetime.combine(datetime.datetime.today(),
                                     datetime.datetime.strptime(timestamp, '%I.%M %p').time())


def get_weather_readings():
    r = requests.get('http://www.weather.gov.sg/mobile/json/rest-get-all-climate-stations.json')
    data = json.loads(r.content)
    locations = dict()
    for location in data['data']:
        print(location)
        locations[location['id']] = WeatherStationReading(name=location['name'],
                                                          id=location['id'],
                                                          latitude=float(location['lat']),
                                                          longitude=float(location['long']),
                                                          )
    r = requests.get('http://www.weather.gov.sg/mobile/json/rest-get-latest-observation-for-all-locs.json')
    data = json.loads(r.content)
    for station_id, readings in data['data']['station'].items():
        if 'recorded_date' in readings:
            locations[station_id].measurement_timestamp = _parse_recorded_date(readings['recorded_date'])
        if 'rain_mm' in readings:
            locations[station_id].rain_mm = float(readings['rain_mm'])
        if 'relative_humidity' in readings:
            locations[station_id].relative_humidity = float(readings['relative_humidity'])
        if 'temp_celcius' in readings:
            locations[station_id].temperature_celcius = float(readings['temp_celcius'])
        if 'wind_direction' in readings:
            locations[station_id].wind_direction = int(readings['wind_direction'])
        if 'wind_speed_knots' in readings:
            locations[station_id].wind_speed_knots = float(readings['wind_speed_knots'])
        if 'wind_speed_kpr' in readings:
            locations[station_id].wind_speed_kpr = float(readings['wind_speed_kpr'])
        if 'visKM' in readings:
            locations[station_id].visibility_km = float(readings['visKM'])
        if 'visTime' in readings:
            locations[station_id].visibility_timestamp = _parse_visibility_timestamp(readings['visTime'])

    return [station for station in locations.values() if not station.is_blank]


if __name__ == '__main__':
    pprint(get_weather_readings())
