import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from pprint import pprint
from typing import List
from typing import Optional

import requests

from api_wrappers.caching import cache_1m
from api_wrappers.location import Location


@dataclass
class OneMapResult(Location):
    block_no: str  # BLK_NO, eg 22B
    road_name: str  # ROAD_NAME
    building_name: str  # BUILDING
    zipcode: str  # POSTAL
    # latitude: float  # LATITUDE (inherited from Location)
    # longitude: float  # LONGITUDE (inherited from Location)
    svy21_x: float  # X
    svy21_y: float  # Y

    _address: Optional[str] = None  # ADDRESS

    @property
    def address(self):
        # usually f'{block_no} {road_name} {building} SINGAPORE {zipcode}' unless there are nulls
        if self._address is not None:
            return self._address

        if self.building_name.lower() not in {'null', 'nil', 'na', '-', ''}:
            return f'{self.block_no} {self.road_name} {self.building_name} SINGAPORE {self.zipcode}'
        else:
            return f'{self.block_no} {self.road_name} SINGAPORE {self.zipcode}'


@cache_1m
def onemap_search(query) -> List[OneMapResult]:
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
        data = dict()

        # run query
        for retry_attempt in range(3):
            # noinspection PyBroadException
            try:
                r = requests.get('https://developers.onemap.sg/commonapi/search',
                                 params={'searchVal':      query,
                                         'returnGeom':     'Y',
                                         'getAddrDetails': 'Y',
                                         'pageNum':        page_num,
                                         })
                data = json.loads(r.content)
                break

            except Exception:
                if retry_attempt == 2:
                    raise

        # catch error
        if 'error' in data:
            logging.warning(f'QUERY_ONEMAP_ERROR={query} PAGE_NUM={page_num}')
            return results

        # append to results
        for result in data.get('results', []):
            results.append(OneMapResult(block_no=result['BLK_NO'],
                                        road_name=result['ROAD_NAME'],
                                        building_name=result['BUILDING'],
                                        zipcode=result['POSTAL'],
                                        latitude=float(result['LATITUDE']),
                                        longitude=float(result['LONGITUDE']),
                                        svy21_x=float(result['X']),
                                        svy21_y=float(result['Y']),
                                        _address=result['ADDRESS'],
                                        ))

        # check number of pages and results
        total_pages = data.get('totalNumPages', page_num)
        assert page_num == data.get('pageNum', page_num), data
        if page_num == total_pages:
            assert len(results) == data['found'], data
        return results


@cache_1m
def onemap_token() -> str:
    with open('../secrets.json') as f:
        secrets = json.load(f)
    r = requests.post('https://developers.onemap.sg/privateapi/auth/post/getToken',
                      json={
                          'email':    secrets['onemap_email'],
                          'password': secrets['onemap_password'],
                      })
    data = json.loads(r.content)
    logging.info(f'ONEMAP_TOKEN="{data["access_token"]}" '
                 f'EXPIRY={data["expiry_timestamp"]} '
                 f'EMAIL="{secrets["onemap_email"]}"')
    return data['access_token']


@cache_1m
def onemap_reverse_geocode(lat, lon, buffer) -> List[OneMapResult]:
    r = requests.get('https://developers.onemap.sg/privateapi/commonsvc/revgeocode',
                     params={'location':      f'{lat},{lon}',
                             'token':         onemap_token(),
                             'buffer':        buffer,
                             'addressType':   'All',
                             'otherFeatures': 'Y',
                             })
    data = json.loads(r.content)
    return [OneMapResult(block_no=result['BLOCK'],
                         road_name=result['ROAD'],
                         building_name=result['BUILDINGNAME'],
                         zipcode=result['POSTALCODE'],
                         latitude=float(result['LATITUDE']),
                         longitude=float(result['LONGITUDE']),
                         svy21_x=float(result['XCOORD']),
                         svy21_y=float(result['YCOORD']),
                         ) for result in data['GeocodeInfo']]


@lru_cache
def onemap_convert(lat: float, lon: float, input_epsg: int, output_epsg: int):
    supported = {
        3414,  # EPSG:3414 (SVY21)
        3857,  # EPSG:3857 (Google Web Mercator)
        4326,  # EPSG:4326 (WGS84)
    }
    assert input_epsg in supported
    assert output_epsg in supported

    # pass-through
    if input_epsg == output_epsg:
        return lat, lon

    # query
    r = requests.get(f'https://developers.onemap.sg/commonapi/convert/{input_epsg}to{output_epsg}',
                     params={'X': lat,
                             'Y': lon,
                             })
    data = json.loads(r.content)
    return data['latitude'], data['longitude']


if __name__ == '__main__':
    pprint(onemap_reverse_geocode(1.3038648897327096, 103.76421005561127, 500))
