import json
import logging
from dataclasses import dataclass
from pprint import pprint

import requests

from api_wrappers.caching import cache_1h
from api_wrappers.location import Location


@dataclass
class OneMapResult(Location):
    address: str  # ADDRESS, seems to be f'{block_no} {road_name} {building} SINGAPORE {zipcode}'
    block_no: str  # BLK_NO, eg 22B
    road_name: str  # ROAD_NAME
    building: str  # BUILDING
    zipcode: str  # POSTAL
    latitude: float  # LATITUDE
    longitude: float  # LONGITUDE
    svy21_x: float  # X
    svy21_y: float  # Y


@cache_1h
def query_onemap(query):
    """
    Each page of json response is restricted to a maximum of 10 results.
    Parameter       Type    Optional    Description
    searchVal       String  Required    Keywords entered by user that is used to filter out the results.
    returnGeom      {Y/N}   Required    Checks if user wants to return the geometry.
    getAddrDetails  {Y/N}   Required    Checks if user wants to return address details for a point.
    pageNum         Int     Optional    Specifies the page to retrieve your search results from.

    :param query:
    :return:
    """
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


if __name__ == '__main__':
    pprint(query_onemap(' 780E Woodlands'))
