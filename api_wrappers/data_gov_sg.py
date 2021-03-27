import json
import logging
from pprint import pprint

import pandas as pd
import requests

RESOURCE_IDS = {
    'Dates of Hawker Centres Closure':
        'b80cb643-a732-480d-86b5-e03957bc82aa',

    'List of Government Markets Hawker Centres':
        '8f6bba57-19fc-4f36-8dcf-c0bda382364d',

    'List of NEA Licensed Eating Establishments with Grades, Demerit Points and Suspension History':
        '34f86c3e-a90c-4de9-a69f-afc86b7f31b6',

    'Hawker Centres (KML)':
        'c2e33097-4f46-4ef5-91db-64eef290ca85',

    'Eating Establishments (KML)':
        'e2ed0eff-4cac-4acc-8de3-8c954361158f'

}


def get_metadata(resource_id):
    r = requests.get(f'https://data.gov.sg/api/action/resource_show?id={resource_id}')
    data = json.loads(r.content)
    return data['result']


def get_resource(resource_id: str):
    logging.info(f'loading {resource_id}')
    limit = 99999  # just for starters
    r = requests.get('https://data.gov.sg/api/action/datastore_search',
                     params={
                         'resource_id': resource_id,
                         'limit':       limit,
                     })
    data = json.loads(r.content)
    if data['result']['total'] > limit:
        limit = data['result']['total']
        r = requests.get('https://data.gov.sg/api/action/datastore_search',
                         params={
                             'resource_id': resource_id,
                             'limit':       limit,
                         })
        data = json.loads(r.content)
    df = pd.DataFrame(data['result']['records'])
    df = df.sort_values(by='_id')
    df = df[[field['id'] for field in data['result']['fields']]]
    return df


if __name__ == '__main__':

    for resource_name, resource_id in RESOURCE_IDS.items():
        print(resource_name)
        pprint(get_metadata(resource_id))
        # df = get_resource(resource_id)
        # print(tabulate(df, headers=df.columns))
        #
        # safe_name = '-'.join(''.join(char if char.isalpha() else ' ' for char in resource_name.lower()).split())
        # timestamp = datetime.datetime.now().strftime('%Y-%m-%d--%H-%M-%S')
        # path = Path(f'../data/{safe_name}/{safe_name}--{timestamp}.csv')
        # path.parent.mkdir(parents=True, exist_ok=True)
        # df.to_csv(path, index=False)
