import datetime
import json
import logging
import re
import sys
from functools import lru_cache
from pathlib import Path
from pprint import pprint
from typing import Optional
from typing import Tuple

import pandas as pd
import requests

from data.hawker_data import RESOURCE_IDS
from data.hawker_data import get_resource
from hawkers import Hawker


def setup_logging(app_name) -> logging.Logger:
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d--%H-%M-%S')
    log_path = Path(f'logs/{app_name}--{timestamp}.log').resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # setup logging format
    log_formatter = logging.Formatter('%(asctime)s  '
                                      '%(levelname)-8s '
                                      '[%(name)s|%(processName)s|%(threadName)s|%(module)s|%(funcName)s]\t'
                                      '%(message)s')

    # set global log level to DEBUG (most verbose possible)
    logging.getLogger().setLevel(logging.DEBUG)

    # create stderr handler at INFO
    logging_stdout_handler = logging.StreamHandler(sys.stderr)
    logging_stdout_handler.setFormatter(log_formatter)
    logging_stdout_handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(logging_stdout_handler)

    # create file handler at DEBUG
    logging_file_handler = logging.FileHandler(log_path)
    logging_file_handler.setFormatter(log_formatter)
    logging_file_handler.setLevel(logging.INFO)  # set to DEBUG if there's enough disk space (there isn't)
    logging.getLogger().addHandler(logging_file_handler)

    return logging.getLogger()


def load_hawker_data():
    hawkers = []
    df = pd.read_csv('data/hawker-centres/hawker-centres.csv')
    for i, row in df.iterrows():
        hawkers.append(Hawker.from_row(row))

    # # filter to useful hawker centers
    # hawkers = [hawker for hawker in hawkers if hawker.no_of_food_stalls > 0]

    # df = pd.read_csv('data/dates-of-hawker-centres-closure/dates-of-hawker-centres-closure--2021-03-18--22-52-07.csv')
    df = get_resource(RESOURCE_IDS['Dates of Hawker Centres Closure'])
    for i, row in df.iterrows():
        for hawker in hawkers:
            # name exact match
            if hawker.name == row['name']:
                hawker.add_cleaning_periods(row)
                break

            # geoloc within 1 meter
            elif (abs(hawker.latitude - float(row['latitude_hc'])) ** 2 +
                  abs(hawker.longitude - float(row['longitude_hc'])) ** 2) ** 0.5 < 9e-06:
                logging.info(f'matched by location: {hawker.name}, {row["name"]}')
                hawker.add_cleaning_periods(row)
                break

            # geoloc within 1 meter (alternative latlong)
            elif hawker.latitude_hc and hawker.longitude_hc and \
                    (abs(hawker.latitude_hc - float(row['latitude_hc'])) ** 2 +
                     abs(hawker.longitude_hc - float(row['longitude_hc'])) ** 2) ** 0.5 < 9e-06:
                logging.info(f'matched by location_hc: {hawker.name}, {row["name"]}')
                hawker.add_cleaning_periods(row)
                break

            # address exact match
            elif hawker.address_myenv == row['address_myenv']:
                logging.info(f'matched by address: {hawker.name}, {row["name"]}')
                hawker.add_cleaning_periods(row)
                break

        # no match
        else:
            logging.warning(f'could not find {row["name"]}')

    return hawkers


ZIP_PREFIXES = {  # https://en.wikipedia.org/wiki/Postal_codes_in_Singapore#Postal_districts
    '01', '02', '03', '04', '05', '06',  # Raffles Place, Cecil, Marina, People's Park
    '07', '08',  # Anson, Tanjong Pagar
    '14', '15', '16',  # Bukit Merah, Queenstown, Tiong Bahru
    '09', '10',  # Telok Blangah, Harbourfront
    '11', '12', '13',  # Pasir Panjang, Hong Leong Garden, Clementi New Town
    '17',  # High Street, Beach Road (part)
    '18', '19',  # Middle Road, Golden Mile
    '20', '21',  # Little India, Farrer Park, Jalan Besar, Lavender
    '22', '23',  # Orchard, Cairnhill, River Valley
    '24', '25', '26', '27',  # Ardmore, Bukit Timah, Holland Road, Tanglin
    '28', '29', '30',  # Watten Estate, Novena, Thomson
    '31', '32', '33',  # Balestier, Toa Payoh, Serangoon
    '34', '35', '36', '37',  # Macpherson, Braddell, Potong Pasir, Bidadari
    '38', '39', '40', '41',  # Geylang, Eunos, Aljunied
    '42', '43', '44', '45',  # Katong, Joo Chiat, Amber Road
    '46', '47', '48',  # Bedok, Upper East Coast, Eastwood, Kew Drive
    '49', '50', '81',  # Loyang, Changi
    '51', '52',  # Simei, Tampines, Pasir Ris
    '53', '54', '55', '82',  # Serangoon Garden, Hougang, Punggol
    '56', '57',  # Bishan, Ang Mo Kio
    '58', '59',  # Upper Bukit Timah, Clementi Park, Ulu Pandan
    '60', '61', '62', '63', '64',  # Penjuru, Jurong, Pioneer, Tuas
    '65', '66', '67', '68',  # Hillview, Dairy Farm, Bukit Panjang, Choa Chu Kang
    '69', '70', '71',  # Lim Chu Kang, Tengah
    '72', '73',  # Kranji, Woodgrove, Woodlands
    '77', '78',  # Upper Thomson, Springleaf
    '75', '76',  # Yishun, Sembawang, Senoko
    '79', '80',  # Seletar
}


class InvalidZip(ValueError):
    pass


class ZipBlank(InvalidZip):
    pass


class ZipNonNumeric(InvalidZip):
    pass


class ZipNonExistent(InvalidZip):
    pass


@lru_cache
def fix_zip(query):
    query = query.strip()

    if not query:
        logging.info('ZIPCODE_BLANK')
        raise ZipBlank()

    if not query.isdigit():
        logging.info(f'ZIPCODE_NON_NUMERIC="{query}"')
        raise ZipNonNumeric()

    # sanity check zip code
    zip_code = f'{int(query):06d}'
    if len(zip_code) > 6 or zip_code[:2] not in ZIP_PREFIXES:
        logging.info(f'ZIPCODE_NON_EXISTENT="{zip_code}"')
        raise ZipNonExistent()

    return zip_code


RE_COMMAND = re.compile(r'(/[a-zA-Z0-9_]{1,64})(?![a-zA-Z0-9_])')


@lru_cache
def get_command(query):
    m = RE_COMMAND.match(query)
    if m is not None:
        return m.group()


@lru_cache
def query_onemap(query):
    query = query.strip()
    if not query:
        logging.info('QUERY_ONEMAP_BLANK')
        return []

    results = []
    page_num = 0
    total_pages = 1
    while page_num < total_pages:
        page_num += 1

        # run query
        r = requests.get('https://developers.onemap.sg/commonapi/search',
                         params={'searchVal':      query,
                                 'returnGeom':     'Y',
                                 'getAddrDetails': 'Y',
                                 'pageNum':        page_num,
                                 })
        data = json.loads(r.content)

        # catch error
        if 'error' in data:
            logging.warning(f'QUERY_ONEMAP_ERROR={query} PAGE_NUM={page_num}')
            return results

        # append to results
        results.extend(data.get('results', []))
        total_pages = data.get('totalNumPages', page_num)
        assert page_num == data.get('pageNum', page_num), data
        if page_num == total_pages:
            assert len(results) == data['found'], data
    return results


@lru_cache
def locate_zip(zip_code: str) -> Optional[Tuple[float, float, str]]:
    zip_code = fix_zip(zip_code)

    # query zip code and return coordinates of first matching result
    for result in query_onemap(zip_code):
        if result['POSTAL'] == zip_code:
            return float(result['LATITUDE']), float(result['LONGITUDE']), result['ADDRESS']


@lru_cache
def convert(lat: float, lon: float):
    """
    3414(SVY21) to 4326(WGS84)
    """
    r = requests.get('https://developers.onemap.sg/commonapi/convert/3414to4326',
                     params={'X': lat,
                             'Y': lon,
                             })
    data = json.loads(r.content)
    return data['latitude'], data['longitude']


def weather_now():
    r = requests.get('https://api.data.gov.sg/v1/environment/2-hour-weather-forecast')
    area_metadata = json.loads(r.content).get('area_metadata', [])
    items = json.loads(r.content).get('items', [])
    if not items:
        return
    return area_metadata, items[0]  # todo: merge metadata and items


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
    # pprint(query_onemap('Punggol Town Hub Hawker Centre'))
    # pprint(convert(39318.07, 32112.26))
    pprint(weather_today())
    pprint(weather_forecast())
