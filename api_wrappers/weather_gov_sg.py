import datetime
import json
from dataclasses import dataclass
from io import BytesIO
from typing import List
from typing import Optional
from typing import Tuple

import requests
from PIL import Image

from api_wrappers.location import Location

intensityColors = [
    '#40FFFD',
    '#3BEEEC',
    '#32D0D2',
    '#2CB9BD',
    '#229698',
    '#1C827D',
    '#1B8742',
    '#229F44',
    '#27B240',
    '#2CC53B',
    '#30D43E',
    '#38EF46',
    '#3BFB49',
    '#59FA61',
    '#FEFB63',
    '#FDFA53',
    '#FDEB50',
    '#FDD74A',
    '#FCC344',
    '#FAB03F',
    '#FAA23D',
    '#FB8938',
    '#FB7133',
    '#F94C2D',
    '#F9282A',
    '#DD1423',
    '#BE0F1D',
    '#B21867',
    '#D028A6',
    '#F93DF5',
]
def get_warning():
    r=requests.get('http://www.weather.gov.sg/mobile/rest-mobile-app-warning/')


def haze_pm25_hourly():
    # from https://www-haze-gov-sg-admin.cwp.sg/assets/scripts/data.js
    # staging version https://www-haze-gov-sg-admin.cwp-stg.sg/assets/scripts/data.js
    # unix timestamp 5 mins
    # 1616915100 == Sun Mar 28 2021 15:05:00 GMT+0800 == 07:05:00 GMT+0000
    url=f'https://www-haze-gov-sg-admin.cwp.sg/api/airquality/jsondata/1616915100'

def get_radar_3rd_party():
    # https://github.com/cheeaun/rainshot
    # https://rainshot.checkweather.sg
    # https://rainshot.now.sh
    pass

def get_drain_water_levels():
    r=requests.get('https://s3-ap-southeast-1.amazonaws.com/myenv2/water_level_card.json')

def get_radar_70km() -> List[List[Tuple[int, int, int, int]]]:
    # https://medium.com/@cheeaun/building-check-weather-sg-3e5fbf1cbe43
    """
    function calculatePosition(basemapImg,latitude,longitude){
    /* var map_latitude_top = 1.490735;
    var map_longitude_left = 103.568691;
    var map_latitude_bottom = 1.177710;
    var map_longitude_right = 104.134487; */
    var map_latitude_top = 1.4572;
    var map_longitude_left = 103.565;
    var map_latitude_bottom = 1.1450;
    var map_longitude_right = 104.130;
    var width_calibration = 20720;
    var height_calibration = 246;
    var zoom_level_height = 200;
    var zoom_level_width = 200;
    var imgWidth = basemapImg.width;
    var imgHeight = basemapImg.height;
    var scale = imgWidth/100;

    Finally I end up using these values:
    Lower latitude = 1.156°
    Upper latitude = 1.475°
    Lower longitude = 103.565°
    Upper longitude = 104.130°
    :return:
    """
    timestamp = datetime.datetime.now()
    timestamp = timestamp.replace(minute=(timestamp.minute // 5) * 5,  # round to 5 mins
                                  second=0,
                                  microsecond=0,
                                  ) + datetime.timedelta(minutes=5)
    for _ in range(5):
        timestamp_str = timestamp.strftime('%Y%m%d%H%M')
        url = 'http://www.weather.gov.sg/wp-content/themes/wiptheme/assets/img/SG-coastline.png'
        url = f'http://www.weather.gov.sg/files/rainarea/50km/v2/dpsri_70km_{timestamp_str}0000dBR.dpsri.png'
        r = requests.get(url)
        if r.status_code == 200:
            break
        else:
            timestamp -= datetime.timedelta(minutes=5)
    else:
        raise RuntimeError()

    # read PNG bytes
    im = Image.open(BytesIO(r.content))
    pixel_access = im.load()
    print(im.size)  # width (x-axis), height (reversed y-axis); ie. (0, 0) is top left
    print(pixel_access[0, 0])  # Get the RGBA Value of the a pixel of an image

    return [[pixel_access[x, y]  # (r,g,b,a) where a=255
             for y in range(im.size[1]) if pixel_access[x, y][-1]]
            for x in range(im.size[1])]


def get_radar_240km() -> List[List[Tuple[int, int, int, int]]]:
    timestamp = datetime.datetime.now()
    timestamp = timestamp.replace(minute=(timestamp.minute // 15) * 15,  # round to 5 mins
                                  second=0,
                                  microsecond=0,
                                  ) + datetime.timedelta(minutes=15)
    for _ in range(5):
        timestamp_str = timestamp.strftime('%Y%m%d%H%M')
        print(timestamp_str)
        url = f'http://www.weather.gov.sg/files/rainarea/240km/dpsri_240km_{timestamp_str}0000dBR.dpsri.png'
        r = requests.get(url)
        if r.status_code == 200:
            break
        else:
            timestamp -= datetime.timedelta(minutes=15)
    else:
        raise RuntimeError()

    # read PNG bytes
    im = Image.open(BytesIO(r.content))
    pixel_access = im.load()
    print(im.size)  # width (x-axis), height (reversed y-axis); ie. (0, 0) is top left
    print(pixel_access[0, 0])  # Get the RGBA Value of the a pixel of an image
    im.show()
    # return [[pixel_access[x, y]  # (r,g,b,a) where a=255
    #          for y in range(im.size[1]) if pixel_access[x, y][-1]]
    #         for x in range(im.size[1])]


def get_radar_480km() -> List[List[Tuple[int, int, int, int]]]:
    timestamp = datetime.datetime.now()
    timestamp = timestamp.replace(minute=(timestamp.minute // 30) * 30,  # round to 5 mins
                                  second=0,
                                  microsecond=0,
                                  ) + datetime.timedelta(minutes=30)
    for _ in range(5):
        timestamp_str = timestamp.strftime('%Y%m%d%H%M')
        print(timestamp_str)
        url = f'http://www.weather.gov.sg/files/rainarea/480km/dpsri_480km_{timestamp_str}0000dBR.dpsri.png'
        r = requests.get(url)
        if r.status_code == 200:
            break
        else:
            timestamp -= datetime.timedelta(minutes=30)
    else:
        raise RuntimeError()

    # read PNG bytes
    im = Image.open(BytesIO(r.content))
    pixel_access = im.load()
    print(im.size)  # width (x-axis), height (reversed y-axis); ie. (0, 0) is top left
    print(pixel_access[0, 0])  # Get the RGBA Value of the a pixel of an image
    im.show()
    # return [[pixel_access[x, y]  # (r,g,b,a) where a=255
    #          for y in range(im.size[1]) if pixel_access[x, y][-1]]
    #         for x in range(im.size[1])]


@dataclass
class WeatherStation(Location):
    # latitude and longitude inherited from Location
    name: str
    id: str


@dataclass
class WeatherStationRainGauge(WeatherStation):
    # latitude, longitude, name, id inherited from WeatherStation
    measurement_timestamp: Optional[datetime.datetime] = None  # recorded_date
    rain_mm: Optional[float] = None  # rain_mm


@dataclass
class WeatherStationTemperature(WeatherStation):
    # latitude, longitude, name, id inherited from WeatherStation
    measurement_timestamp: Optional[datetime.datetime] = None  # recorded_date
    temperature_celcius: Optional[float] = None  # temp_celcius


@dataclass
class WeatherStationHumidity(WeatherStation):
    # latitude, longitude, name, id inherited from WeatherStation
    measurement_timestamp: Optional[datetime.datetime] = None  # recorded_date
    relative_humidity: Optional[float] = None  # relative_humidity


@dataclass
class WeatherStationWind(WeatherStation):
    # latitude, longitude, name, id inherited from WeatherStation
    measurement_timestamp: Optional[datetime.datetime] = None  # recorded_date
    wind_direction: Optional[int] = None  # wind_direction (degrees?)
    wind_speed_knots: Optional[float] = None  # wind_speed_knots
    wind_speed_kpr: Optional[float] = None  # wind_speed_kpr


@dataclass
class WeatherStationVisibility(WeatherStation):
    # latitude, longitude, name, id inherited from WeatherStation
    visibility_km: Optional[int] = None  # visKM
    visibility_timestamp: Optional[datetime.datetime] = None  # visTime


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
        locations[location['id']] = WeatherStation(name=location['name'],
                                                   id=location['id'],
                                                   latitude=float(location['lat']),
                                                   longitude=float(location['long']),
                                                   )

    out = []
    r = requests.get('n')
    data = json.loads(r.content)
    for station_id, readings in data['data']['station'].items():
        weather_station = locations[station_id]
        if 'rain_mm' in readings:
            out.append(WeatherStationRainGauge(latitude=weather_station.latitude,
                                               longitude=weather_station.longitude,
                                               name=weather_station.name,
                                               id=weather_station.id,
                                               measurement_timestamp=_parse_recorded_date(readings['recorded_date']),
                                               rain_mm=float(readings['rain_mm']),
                                               ))
        if 'temp_celcius' in readings:
            out.append(WeatherStationTemperature(latitude=weather_station.latitude,
                                                 longitude=weather_station.longitude,
                                                 name=weather_station.name,
                                                 id=weather_station.id,
                                                 measurement_timestamp=_parse_recorded_date(readings['recorded_date']),
                                                 temperature_celcius=float(readings['temp_celcius']),
                                                 ))
        if 'relative_humidity' in readings:
            out.append(WeatherStationHumidity(latitude=weather_station.latitude,
                                              longitude=weather_station.longitude,
                                              name=weather_station.name,
                                              id=weather_station.id,
                                              measurement_timestamp=_parse_recorded_date(readings['recorded_date']),
                                              relative_humidity=float(readings['relative_humidity']),
                                              ))
        if 'wind_direction' in readings:
            out.append(WeatherStationWind(latitude=weather_station.latitude,
                                          longitude=weather_station.longitude,
                                          name=weather_station.name,
                                          id=weather_station.id,
                                          measurement_timestamp=_parse_recorded_date(readings['recorded_date']),
                                          wind_speed_knots=float(readings['wind_speed_knots']),
                                          wind_speed_kpr=float(readings['wind_speed_kpr']),
                                          wind_direction=int(readings['wind_direction']),
                                          ))
        if 'visKM' in readings:
            out.append(WeatherStationVisibility(latitude=weather_station.latitude,
                                                longitude=weather_station.longitude,
                                                name=weather_station.name,
                                                id=weather_station.id,
                                                visibility_km=int(readings['visKM']),
                                                visibility_timestamp=_parse_visibility_timestamp(readings['visTime']),
                                                ))

    return [station for station in locations.values() if not station.is_blank]


if __name__ == '__main__':
    # pprint(get_weather_readings())

    # print(get_radar_70km())
    get_radar_240km()
    get_radar_480km()
