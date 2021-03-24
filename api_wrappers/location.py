import json
import logging
import math
import time
import warnings
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable
from typing import List

import requests
from geographiclib.geodesic import Geodesic

from api_wrappers.caching import cache_1m

# noinspection PyUnresolvedReferences
WGS84 = Geodesic.WGS84


@dataclass  # (unsafe_hash=True, frozen=True)
class Location:
    latitude: float
    longitude: float

    def __post_init__(self):
        if not isinstance(self.latitude, (int, float)):
            raise TypeError(self.latitude)
        if not (-90.0 <= self.latitude <= 90.0):
            raise ValueError(self.latitude)
        self.latitude = float(self.latitude)

        if not isinstance(self.longitude, (int, float)):
            raise TypeError(self.longitude)
        if not (-180.0 <= self.longitude <= 180.0):
            raise ValueError(self.longitude)
        self.longitude = float(self.longitude)

        # try to be smart
        # might regret this later
        if self.latitude == self.longitude == 0.0:
            warnings.warn('Location at (0.0, 0.0) might be NULL')

    def distance(self, other: 'Location') -> float:
        """
        from this point, how far away is the other point?
        uses vincenty formula

        :return: positive distance in meters
        """
        if not isinstance(other, Location):
            raise TypeError(other)
        return WGS84.Inverse(self.latitude, self.longitude, other.latitude, other.longitude)['s12']

    def direction(self, other: 'Location') -> float:
        """
        from this point, in what direction is the other point?
        NOTE: because the earth is an ellipsoid, due East is between 89.5° (North pole) and 90.5° (South pole)

        :return: ±180° degrees clockwise from North
        """
        if not isinstance(other, Location):
            raise TypeError(other)
        return WGS84.Inverse(self.latitude, self.longitude, other.latitude, other.longitude)['azi1']

    def nearest(self, others: Iterable['Location']) -> 'Location':
        """
        find the nearest among a bunch of other Locations
        """
        return min(others, key=lambda x: self.distance(x))

    def k_nearest(self, others: Iterable['Location'], k: int) -> List['Location']:
        """
        find the k-nearest among a bunch of other Locations
        if len(others) < k, throws an error

        assuming len(others) < 1000, it's not worth the code to use heapq
        """
        # sanity check
        if not isinstance(k, int):
            raise TypeError
        if k == 0:
            raise ValueError(k)

        # return all sorted if k is negative
        out = sorted(others, key=lambda x: self.distance(x))
        if k < 0:
            return out

        # otherwise return top k
        if len(out) < k:
            raise ValueError(others)
        return out[:k]

    def within_bounding_box(self, lat_1: float, lon_1: float, lat_2: float, lon_2: float) -> bool:
        # normalize bounding box
        if lat_2 < lat_1:
            lat_2, lat_1 = lat_1, lat_2
        if lon_2 < lon_1:
            lon_2, lon_1 = lon_1, lon_2

        return (lat_1 <= self.latitude <= lat_2) and (lon_1 <= self.longitude <= lon_2)

    def within_singapore(self) -> bool:
        """
        these magic numbers were created by clicking around the Singapore shape in Google Maps and rounding off
        similar to (but not based on) SVY21 bounds: 1.1200, 103.6200, 1.4600, 104.1600
        includes Tekong island, but does NOT include Pedra Branca or the tiny islands south of Semakau
        also includes a bit of Johor, but close enough

        a more correct solution would be to test if this point is in a polygon
        an appropriate polygon could be the Singapore shorelines or timezone boundary
        """
        return (1.2 <= self.latitude <= 1.5) and (103.6 <= self.longitude <= 104.1)


@dataclass
class OneMapResult(Location):
    address: str  # ADDRESS, usually f'{block_no} {road_name} {building} SINGAPORE {zipcode}' unless there are nulls
    block_no: str  # BLK_NO, eg 22B
    road_name: str  # ROAD_NAME
    building: str  # BUILDING
    zipcode: str  # POSTAL
    # latitude: float  # LATITUDE (inherited from Location)
    # longitude: float  # LONGITUDE (inherited from Location)
    svy21_x: float  # X
    svy21_y: float  # Y


@lru_cache
def convert_3414_to_4326(lat: float, lon: float):
    """
    EPSG:3414 (SVY21) -> EPSG:4326 (WGS84)
    """
    r = requests.get('https://developers.onemap.sg/commonapi/convert/3414to4326',
                     params={'X': lat,
                             'Y': lon,
                             })
    data = json.loads(r.content)
    return data['latitude'], data['longitude']


@lru_cache
def convert_4326_to_3414(lat: float, lon: float):
    """
    EPSG:4326 (WGS84) -> EPSG:3414 (SVY21)
    """
    r = requests.get('https://developers.onemap.sg/commonapi/convert/4326to3414',
                     params={'X': lat,
                             'Y': lon,
                             })
    data = json.loads(r.content)
    return data['latitude'], data['longitude']


def _haversine(loc_1: Location, loc_2: Location) -> float:
    """
    assumes spherical earth
    not the default distance because it's slightly less accurate
    it is faster, but then so is pythagoras on a flat earth model
    """
    earth_radius = 6371008.8  # meters

    dLat = math.radians(loc_2.latitude - loc_1.latitude)
    dLon = math.radians(loc_2.longitude - loc_1.longitude)
    loc_1.latitude = math.radians(loc_1.latitude)
    loc_2.latitude = math.radians(loc_2.latitude)

    a = math.sin(dLat / 2) ** 2 + math.cos(loc_1.latitude) * math.cos(loc_2.latitude) * math.sin(dLon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    return earth_radius * c


def _pythagoras(loc_1: Location, loc_2: Location):
    """
    assumes flat earth
    laughably inaccurate at high altitudes
    within singapore, gives basically the same output as haversine, and it's 3x faster
    """
    # earth_radius = 6371008.8  # meters
    return math.sqrt((loc_1.latitude - loc_2.latitude) ** 2 +
                     (loc_1.longitude - loc_2.longitude) ** 2
                     ) * 111195.08023353292  # 2 * math.pi * earth_radius / 360


@cache_1m
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
            results.append(OneMapResult(address=result['ADDRESS'],
                                        block_no=result['BLK_NO'],
                                        road_name=result['ROAD_NAME'],
                                        building=result['BUILDING'],
                                        zipcode=result['POSTAL'],
                                        latitude=float(result['LATITUDE']),
                                        longitude=float(result['LONGITUDE']),
                                        svy21_x=float(result['X']),
                                        svy21_y=float(result['Y']),
                                        ))

        # check number of pages and results
        total_pages = data.get('totalNumPages', page_num)
        assert page_num == data.get('pageNum', page_num), data
        if page_num == total_pages:
            assert len(results) == data['found'], data
        return results

    if __name__ == '__main__':
        # l1 = Location(-1.0, -1.0)
        # l2 = Location(0.5, 179.7)
        l1 = Location(1.2, 103.6)
        l2 = Location(1.5, 104.1)
        d = None

        # vincenty
        t = time.time()
        for _ in range(1000):
            d = l1.distance(l2)
        print(d, time.time() - t)

        # haversine
        t = time.time()
        for _ in range(1000):
            d = _haversine(l1, l2)
        print(d, time.time() - t)

        # pythagoras
        t = time.time()
        for _ in range(1000):
            d = _pythagoras(l1, l2)
        print(d, time.time() - t)
