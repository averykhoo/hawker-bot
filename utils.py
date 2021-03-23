import datetime
import logging
import re
import sys
from functools import lru_cache
from pathlib import Path

import pandas as pd

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


RE_COMMAND = re.compile(r'(/[a-zA-Z0-9_]{1,64})(?![a-zA-Z0-9_])')


@lru_cache
def get_command(query):
    m = RE_COMMAND.match(query)
    if m is not None:
        return m.group()
