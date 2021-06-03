import datetime
import logging
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional
from typing import Tuple

import pandas as pd
import requests

from api_wrappers.data_gov_sg import RESOURCE_IDS
from api_wrappers.data_gov_sg import get_resource
from hawkers import Hawker


def no_ssl_verification():
    old_merge_environment_settings = requests.Session.merge_environment_settings
    opened_adapters = set()

    def merge_environment_settings(self, url, proxies, stream, verify, cert):
        # Verification happens only once per connection so we need to close
        # all the opened adapters once we're done. Otherwise, the effects of
        # verify=False persist beyond the end of this context manager.
        opened_adapters.add(self.get_adapter(url))

        settings = old_merge_environment_settings(self, url, proxies, stream, verify, cert)
        settings['verify'] = False

        return settings

    requests.Session.merge_environment_settings = merge_environment_settings

    # noinspection PyUnresolvedReferences
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)


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
    logging_file_handler = logging.FileHandler(log_path, encoding='utf8')
    logging_file_handler.setFormatter(log_formatter)
    logging_file_handler.setLevel(logging.DEBUG)  # set to INFO if there isn't enough disk space
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


RE_COMMAND = re.compile(r'(?P<command>[/\\][a-zA-Z0-9_]{1,64})(?![a-zA-Z0-9_])')


@lru_cache(maxsize=0xFF)
def get_command(query):
    m = RE_COMMAND.match(query)  # match starting from beginning of string
    if m is not None:
        return m.group('command')


@lru_cache(maxsize=0xFF)
def split_command(query: str,
                  command: Optional[str] = None,
                  ) -> Tuple[Optional[str], str]:
    query = query.strip()

    if command:
        command = command.casefold()
        if query.casefold().startswith(command):
            return query[:len(command)], query[len(command):].strip()
        if query.casefold().startswith(f'/{command}'):
            return query[:len(command) + 1], query[len(command) + 1:].strip()
        if query.casefold().startswith(f'\\{command}'):
            return query[:len(command) + 1], query[len(command) + 1:].strip()
        return None, query

    parts = query.split()
    if len(parts) == 0:
        return None, ''
    elif len(parts) == 1:
        return parts[0], ''
    else:
        return parts[0], query[len(parts[0]):].strip()


def load_template(template_name):
    path = Path(f'templates/{template_name}.md')
    if not path.exists():
        raise ValueError(template_name)
    with path.open(encoding='utf8') as f:
        return f.read().strip().replace('\n', '  \n')
