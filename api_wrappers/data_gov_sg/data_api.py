import datetime
import logging
from typing import Dict
from typing import Optional
from typing import Sequence
from typing import Union
from uuid import UUID

import pandas as pd
import requests
import tabulate

from api_wrappers.data_gov_sg.datatypes import DataStoreResult
from api_wrappers.data_gov_sg.datatypes import Dataset
from api_wrappers.data_gov_sg.datatypes import Resource
from api_wrappers.data_gov_sg.datatypes import ResourceFormat


def get_resource(resource_id: Union[str, UUID]) -> Resource:
    """
    Return the metadata of a resource.

    :param resource_id: the id of the resource
    :return:
    """
    r = requests.get('https://data.gov.sg/api/action/resource_show',
                     params={
                         'id': resource_id,
                     })
    data = r.json()
    if not data['success']:
        raise IndexError(resource_id)
    return Resource.from_json(data['result'])


def get_dataset(dataset_id: Union[str, UUID]) -> Dataset:
    """
    Return the metadata of a dataset (package) and its resources

    :param dataset_id: the id or name of the dataset
    """
    r = requests.get('https://data.gov.sg/api/action/package_show',
                     params={
                         'id': dataset_id,
                     })
    data = r.json()
    if not data['success']:
        raise IndexError(dataset_id)
    return Dataset.from_json(data['result'])


def get_datastore(resource_id: Union[str, UUID],
                  offset: int = 0,
                  limit: Optional[int] = None,  # actual default is 100
                  filters: Optional[Dict[str, Union[bool, float, int, str]]] = None,
                  query: Optional[Union[str, Dict[str, Union[bool, float, int, str]]]] = None,
                  distinct: Optional[bool] = None,
                  plain: Optional[bool] = None,
                  language: Optional[str] = None,
                  fields: Optional[Sequence[str]] = None,
                  sort: Optional[str] = None,
                  ) -> DataStoreResult:
    """
    Search a DataStore resource.

    The datastore_search action allows you to search data in a resource.
    DataStore resources that belong to private CKAN resource can only be read by you
    if you have access to the CKAN resource and send the appropriate authorization.

    :param resource_id: id or alias of the resource to be searched against
    :param filters: matching conditions to select (e.g {"key1": "a", "key2": "b"})
    :param limit: maximum number of rows to return
    :param offset: offset this number of rows
    :param query: full text query.
                  If it's a string, it'll search on all fields on each row.
                  If it's a dictionary as {"key1": "a", "key2": "b"}, it'll search on each specific field
                  (default: None)
    :param distinct: return only distinct rows (default: False)
    :param plain: treat as plain text query,
                  as opposed to supporting the entire PostgreSQL full text search query language
                  https://www.postgresql.org/docs/9.1/static/datatype-textsearch.html#DATATYPE-TSQUERY
                  (default: True)
    :param language: language of the full text query (default: 'english')
    :param fields: fields to return (optional, default: all fields in original order)
    :param sort: comma separated field names with ordering
                 (e.g.: "fieldName1, fieldName2 desc")
                 (default: None)
    """
    params = {
        'resource_id': resource_id,
        'offset':      offset,
        'limit':       99999 if limit is None else limit,
    }

    # additional optional fields
    if filters is not None:
        params['filters'] = filters
    if query is not None:
        params['query'] = query
    if distinct is not None:
        params['distinct'] = distinct
    if plain is not None:
        params['plain'] = plain
    if language is not None:
        params['language'] = language
    if fields is not None:
        params['fields'] = fields
    if sort is not None:
        params['sort'] = sort

    r = requests.get('https://data.gov.sg/api/action/datastore_search',
                     params=params)
    if r.status_code != 200:
        raise IndexError(resource_id)
    data = r.json()
    if not data['success']:
        raise IndexError(resource_id)

    # there's more data to load
    if limit is None and data['result']['total'] > data['result']['limit']:
        params['limit'] = data['result']['total']
        r = requests.get('https://data.gov.sg/api/action/datastore_search',
                         params=params)
        data = r.json()

    # create a df
    return DataStoreResult.from_json(data['result'])


def get_dataset_df(dataset_id: Union[str, UUID]) -> pd.DataFrame:
    dataset = get_dataset(dataset_id)
    assert len(dataset.resources) == 1, [rsc.name for rsc in dataset.resources]
    assert dataset.resources[0].format == ResourceFormat.CSV, dataset.resources[0]
    logging.info(f'loading from dataset: {dataset.title}'
                 f' ({dataset.resources[0].last_modified + datetime.timedelta(hours=8)})')  # "convert" from UTC
    return get_datastore(dataset.resources[0].id).df


if __name__ == '__main__':
    dataset_listing_id = 'dba9594b-fb5c-41c5-bb7c-92860ee31aeb'

    df_dataset_listing = get_dataset_df(dataset_listing_id)
    print(tabulate.tabulate(df_dataset_listing.head(20), headers=df_dataset_listing.columns))
    df_dataset_listing.to_csv('dataset-listing.csv', index=False, encoding='utf8')

    # # contains broken unicode
    # dataset_listing = get_dataset(dataset_listing_id)
    # dataset_listing.resources[0].save('dataset-listing-2.csv')
