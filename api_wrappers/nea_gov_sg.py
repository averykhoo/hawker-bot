import datetime
from pprint import pprint
from typing import Dict
from typing import List
from typing import Tuple

import dateutil.parser
import requests

from api_wrappers.caching import cache_1m
from api_wrappers.data_gov_sg_v2.weather import Forecast
from api_wrappers.data_gov_sg_v2.weather import FourDayForecast
from api_wrappers.data_gov_sg_v2.weather import region_metadata

# unix_timestamp = 1633356000  # increments in 300 seconds
unix_timestamp = 0  # this field seems to be ignored entirely
nea_urls = {
    f'https://www.nea.gov.sg/api/WeatherForecast/forecast24hrnowcast2hrs/{unix_timestamp}',
    f'https://www.nea.gov.sg/api/Weather24hrs/GetData/{unix_timestamp}',
    f'https://www.nea.gov.sg/api/Weather4DayOutlook/GetData/{unix_timestamp}',
    f'https://www.nea.gov.sg/api/Warning/GetAllWarning/{unix_timestamp}',
    f'https://www.nea.gov.sg/api/RainArea/GetRecentData/{unix_timestamp}',
    f'https://www.nea.gov.sg/api/ultraviolet/getall/{unix_timestamp}',
    f'https://www.nea.gov.sg/api/HeavyRainWarning/GetData/{unix_timestamp}',
}
weather_abbreviations = {
    'BR': 'Mist',
    'CL': 'Cloudy',
    'DR': 'Drizzle',
    'FA': 'Fair (Day)',
    'FG': 'Fog',
    'FN': 'Fair (Night)',
    'FW': 'Fair & Warm',
    'HG': 'Heavy Thundery Showers with Gusty Winds',
    'HR': 'Heavy Rain',
    'HS': 'Heavy Showers',
    'HT': 'Heavy Thundery Showers',
    'HZ': 'Hazy',
    'LH': 'Slightly Hazy',
    'LR': 'Light Rain',
    'LS': 'Light Showers',
    'OC': 'Overcast',
    'PC': 'Partly Cloudy (Day)',
    'PN': 'Partly Cloudy (Night)',
    'PS': 'Passing Showers',
    'RA': 'Moderate Rain',
    'SH': 'Showers',
    'SK': 'Strong Winds, Showers',
    'SN': 'Snow',
    'SR': 'Strong Winds, Rain',
    'SS': 'Snow Showers',
    'SU': 'Sunny',
    'SW': 'Strong Winds',
    'TL': 'Thundery Showers',
    'WC': 'Windy, Cloudy',
    'WD': 'Windy',
    'WF': 'Windy, Fair',
    'WR': 'Windy, Rain',
    'WS': 'Windy, Showers',
}

forecast_timings = {
    '6 am':   datetime.time(hour=6),
    'midday': datetime.time(hour=12),
    '6 pm':   datetime.time(hour=18),
}

zone_rename = {
    'Wxeast':    'East',
    'Wxwest':    'West',
    'Wxnorth':   'North',
    'Wxsouth':   'South',
    'Wxcentral': 'Central',
}


@cache_1m
def weather_2h() -> List[Forecast]:
    r = requests.get('https://www.nea.gov.sg/api/WeatherForecast/forecast24hrnowcast2hrs/0', verify=False)
    data = r.json()

    # timestamp
    forecast_timestamp_date = dateutil.parser.parse(data['Channel2HrForecast']['Item']['ForecastIssue']['Date']).date()
    forecast_timestamp_time = dateutil.parser.parse(data['Channel2HrForecast']['Item']['ForecastIssue']['Time']).time()
    forecast_timestamp = datetime.datetime.combine(forecast_timestamp_date, forecast_timestamp_time)

    # forecast
    return [Forecast(latitude=float(area_forecast['Lat']),
                     longitude=float(area_forecast['Lon']),
                     name=area_forecast['Name'],
                     forecast=weather_abbreviations.get(area_forecast['Forecast'], area_forecast['Forecast']),
                     last_update=forecast_timestamp,
                     time_start=forecast_timestamp,
                     time_end=forecast_timestamp + datetime.timedelta(hours=2),
                     ) for area_forecast in data['Channel2HrForecast']['Item']['WeatherForecast']['Area']]


@cache_1m
def weather_24h() -> List[Forecast]:
    r = requests.get('https://www.nea.gov.sg/api/WeatherForecast/forecast24hrnowcast2hrs/0', verify=False)
    data = r.json()
    out = []

    # timestamp
    forecast_timestamp_date = dateutil.parser.parse(data['Channel24HrForecast']['Main']['ForecastIssue']['Date']).date()
    forecast_timestamp_time = dateutil.parser.parse(data['Channel24HrForecast']['Main']['ForecastIssue']['Time']).time()
    forecast_timestamp = datetime.datetime.combine(forecast_timestamp_date, forecast_timestamp_time)

    # forecast
    for period_forecast in data['Channel24HrForecast']['Forecasts']:
        start_str, sep, end_str = period_forecast['TimePeriod'].lower().partition(' to ')
        assert sep is not None

        for time_str in forecast_timings:
            if time_str in start_str:
                start_time = forecast_timings[time_str]
                start_str = start_str.replace(time_str, '').strip()
                break
        else:
            raise RuntimeError(start_str)

        for time_str in forecast_timings:
            if time_str in end_str:
                end_time = forecast_timings[time_str]
                end_str = end_str.replace(time_str, '').strip()
                break
        else:
            raise RuntimeError(start_str)

        assert len(end_str) > 0
        end_date = dateutil.parser.parse(end_str).date()
        start_date = dateutil.parser.parse(start_str).date() if start_str else end_date

        start_timestamp = datetime.datetime.combine(start_date, start_time)
        end_timestamp = datetime.datetime.combine(end_date, end_time)

        for zone, zone_name in zone_rename.items():
            loc = region_metadata[zone_name]
            out.append(Forecast(latitude=loc.latitude,
                                longitude=loc.longitude,
                                name=zone_name,
                                forecast=weather_abbreviations.get(period_forecast[zone],
                                                                   period_forecast[zone]),
                                last_update=forecast_timestamp,
                                time_start=start_timestamp,
                                time_end=end_timestamp,
                                ))
    return out


@cache_1m
def weather_4d() -> List[FourDayForecast]:
    # build a lookup table for which days we're likely to see as the FIRST DAY in the forecast
    day_lookup = dict()
    today = datetime.date.today()
    for delta in [-4, -3, -2, -1, 0, 1]:  # list(range(-4, 2))
        date = today + datetime.timedelta(days=delta)
        day = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'][int(date.strftime('%w'))]
        day_lookup[day] = date

    r = requests.get('https://www.nea.gov.sg/api/Weather4DayOutlook/GetData/0', verify=False)
    data = r.json()
    first_date = day_lookup[data[0]['day']]
    out = []

    # forecast
    for idx, daily_forecast in enumerate(data):
        out.append(FourDayForecast(date=first_date + datetime.timedelta(days=idx),
                                   forecast=daily_forecast['forecast'],
                                   ))
    return out


@cache_1m
def weather_24h_grouped() -> Dict[Tuple[datetime.datetime, datetime.datetime], List[Forecast]]:
    out = dict()
    for forecast in weather_24h():
        out.setdefault((forecast.time_start, forecast.time_end), []).append(forecast)
    return out


if __name__ == '__main__':
    # get_forecasts()
    pprint(weather_2h())
    pprint(weather_24h())
    pprint(weather_24h_grouped())
    pprint(weather_4d())
