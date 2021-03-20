import math
import time

from geographiclib.geodesic import Geodesic

# noinspection PyUnresolvedReferences
WGS84 = Geodesic.WGS84


def vincenty(loc_1, loc_2):
    lat1, lon1 = loc_1
    lat2, lon2 = loc_2

    return WGS84.Inverse(lat1, lon1, lat2, lon2)['s12']


def haversine(loc_1, loc_2):
    lat1, lon1 = loc_1
    lat2, lon2 = loc_2
    earth_radius = 6371008.8  # meters

    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    a = math.sin(dLat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dLon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    return earth_radius * c


def pythagoras(loc_1, loc_2):
    lat1, lon1 = loc_1
    lat2, lon2 = loc_2
    earth_radius = 6371008.8  # meters

    return math.sqrt(abs(lat1 - lat2) ** 2 + abs(lon1 - lon2) ** 2) * 2 * math.pi * earth_radius / 360


if __name__ == '__main__':
    print(vincenty((0.0, 0.0), (0.0, 0.0)))
    print(haversine((0.0, 0.0), (0.0, 0.0)))
    print(pythagoras((0.0, 0.0), (0.0, 0.0)))
    print()
    print(vincenty((0.0, 0.0), (0.0, 1.0)))
    print(haversine((0.0, 0.0), (0.0, 1.0)))
    print(pythagoras((0.0, 0.0), (0.0, 1.0)))
    print()
    print(vincenty((0.0, 0.0), (1.0, 0.0)))
    print(haversine((0.0, 0.0), (1.0, 0.0)))
    print(pythagoras((0.0, 0.0), (1.0, 0.0)))
    print()
    print(vincenty((0.0, 0.0), (0.5, 179.5)))
    print(haversine((0.0, 0.0), (0.5, 179.5)))
    print(pythagoras((0.0, 0.0), (0.5, 179.5)))
    print()
    print(vincenty((0.0, 0.0), (0.5, 179.7)))
    print(haversine((0.0, 0.0), (0.5, 179.7)))
    print(pythagoras((0.0, 0.0), (0.5, 179.7)))
    print()

    t = time.time()
    for _ in range(1000):
        vincenty((0.0, 0.0), (0.5, 179.7))
    print(time.time() - t)
    t = time.time()
    for _ in range(1000):
        haversine((0.0, 0.0), (0.5, 179.7))
    print(time.time() - t)
    t = time.time()
    for _ in range(1000):
        pythagoras((0.0, 0.0), (0.5, 179.7))
    print(time.time() - t)

    loc_1 = (1.3726766091733784, 103.8276677318632)
    loc_2 = (0.9151692394764589, 104.4623321741962)
    print()
    print(vincenty(loc_1, loc_2))
    print(haversine(loc_1, loc_2))
    print(pythagoras(loc_1, loc_2))
