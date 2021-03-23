import json
import warnings
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable
from typing import List

import requests
from geographiclib.geodesic import Geodesic

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
        out = sorted(others, key=lambda x: self.distance(x))
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
class Address(Location):
    # inherits latitude and longitude
    address: str


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
