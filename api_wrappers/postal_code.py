import logging
import re
from functools import lru_cache
from pprint import pprint
from typing import Optional

from api_wrappers.onemap_sg import OneMapResult
from api_wrappers.onemap_sg import onemap_search

RE_ZIPCODE = re.compile(r'(?:(?:code|S(G|ingapore)?)\s{0,5})?(?P<zip>\d{6})', flags=re.I | re.U)


class InvalidZip(ValueError):
    pass


class ZipBlank(InvalidZip):
    pass


class ZipNonNumeric(InvalidZip):
    pass


class ZipNonExistent(InvalidZip):
    pass


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


@lru_cache
def fix_zipcode(query: str) -> str:
    query = query.strip()

    # if we can matched this, we know can parse it as a zipcode
    # /zip code 123456
    # /zip 123456
    # /zip S123456
    # /zip SG123456
    # /zip Singapore 123456
    m = RE_ZIPCODE.fullmatch(query)
    if m:
        query = m.group('zip')

    # error for blank input
    elif not query:
        logging.info('ZIPCODE_BLANK')
        raise ZipBlank()

    # error for non-numeric input
    elif not query.isdigit():
        logging.info(f'ZIPCODE_NON_NUMERIC="{query}"')
        raise ZipNonNumeric()

    # sanity check zip code
    zip_code = f'{int(query):06d}'
    if len(zip_code) > 6 or zip_code[:2] not in ZIP_PREFIXES:
        logging.info(f'ZIPCODE_NON_EXISTENT="{zip_code}"')
        raise ZipNonExistent()

    return zip_code


def locate_zipcode(zipcode: str) -> Optional[OneMapResult]:
    """
    `query_onemap` is already cached
    """
    zipcode = fix_zipcode(zipcode)

    # query zip code and return coordinates of first matching result
    for result in onemap_search(zipcode):
        if result.zipcode == zipcode:
            return result


if __name__ == '__main__':
    pprint(locate_zipcode('120725'))
