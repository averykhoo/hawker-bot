import datetime
import logging
import re
from pathlib import Path
from typing import Tuple

import pandas as pd
import requests

from api_wrappers.data_gov_sg.datatypes import ResourceFormat
from api_wrappers.data_gov_sg_v2.datatypes import DatasetMetadata


def get_dataset_df(dataset_id: str) -> Tuple[str, datetime.datetime, pd.DataFrame]:
    assert re.fullmatch(r'd_[0-9a-f]{32}', dataset_id)

    # get metadata
    r = requests.get(f'https://api-production.data.gov.sg/v2/public/api/datasets/{dataset_id}/metadata',
                     verify=False)
    metadata = DatasetMetadata.from_json(r.json()['data'])
    assert metadata.format is ResourceFormat.CSV

    # get data
    r = requests.get(f'https://data.gov.sg/api/action/datastore_search',
                     params={'resource_id': dataset_id, 'limit': 9999},
                     verify=False)
    df = pd.DataFrame(r.json()['result']['records'])
    df.drop('_id', axis=1, inplace=True)

    # backup data
    safe_name = re.sub(r'[^a-z0-9]+', '-', metadata.name.casefold()).strip('-')
    safe_date = metadata.last_updated_at.strftime('%Y-%m-%d--%H-%M-%S')
    backup_path = Path('data') / safe_name / f'{safe_name}--{safe_date}.csv'
    if not backup_path.exists():
        logging.info(f'backing up to {backup_path}')
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(backup_path, index=False)

    return metadata.name, metadata.last_updated_at, df
