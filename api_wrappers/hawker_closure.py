import logging

import pandas as pd

from api_wrappers.data_gov_sg.data_api import get_dataset
from api_wrappers.data_gov_sg.data_api import get_datastore
from api_wrappers.data_gov_sg.data_api import get_resource
from api_wrappers.data_gov_sg.datatypes import ResourceFormat

DATASET_IDS = {
    'Dates of Hawker Centres Closure':
        'f28a763e-2320-4969-b249-c23f21c33ffc',  # CSV

    'Hawker Centres':
        'aeaf4704-5be1-4b33-993d-c70d8dcc943e',  # KML and GeoJSON

    'Eating Establishments':
        '208edaa0-0e58-468a-b0ae-b47dd37cf923',  # KML

    'List of Government Markets Hawker Centres':
        'b6083025-58a6-41a4-8066-c51a3282218f',  # CSV

    'List of NEA Licensed Eating Establishments with Grades, Demerit Points and Suspension History':
        '012e8dc8-631f-433c-aaa2-a9e975dc2ce4',  # CSV
}


def get_dataset_df(dataset_id: str) -> pd.DataFrame:
    dataset = get_dataset(dataset_id)
    assert len(dataset.resources) == 1
    assert dataset.resources[0].format == ResourceFormat.CSV
    logging.info(f'loading from dataset: {dataset.title} ({dataset.resources[0].last_modified})')
    return get_datastore(dataset.resources[0].id).df


if __name__ == '__main__':
    print(get_resource('34f86c3e-a90c-4de9-a69f-afc86b7f31b6'))
    print(get_dataset('012e8dc8-631f-433c-aaa2-a9e975dc2ce4').resources[0])
