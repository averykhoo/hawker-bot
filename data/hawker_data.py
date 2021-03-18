import json
from pprint import pprint

import pandas as pd
import requests

RESOURCE_IDS = {
    'Dates of Hawker Centres Closure':
        'b80cb643-a732-480d-86b5-e03957bc82aa',
    'List of Government Markets Hawker Centres':
        '8f6bba57-19fc-4f36-8dcf-c0bda382364d',
    'List of NEA Licensed Eating Establishments with Grades, Demerit Points and Suspension History':
        '34f86c3e-a90c-4de9-a69f-afc86b7f31b6'
}


def query_onemap(query):
    results = []
    page_num = 0
    total_pages = 1
    while page_num < total_pages:
        page_num += 1
        r = requests.get('https://developers.onemap.sg/commonapi/search',
                         params={'searchVal':      query,
                                 'returnGeom':     'Y',
                                 'getAddrDetails': 'Y',
                                 'pageNum':        page_num,
                                 })
        data = json.loads(r.content)
        results.extend(data['results'])
        total_pages = data['totalNumPages']
        assert page_num == data['pageNum']
        if page_num == total_pages:
            assert len(results) == data['found']
    return results


def convert(lat: float, lon: float):
    """
    3414(SVY21) to 4326(WGS84)
    """
    r = requests.get('https://developers.onemap.sg/commonapi/convert/3414to4326',
                     params={'X': lat,
                             'Y': lon,
                             })
    data = json.loads(r.content)
    return data['latitude'], data['longitude']


def get_resource(resource_id: str):
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
    pprint(query_onemap('Punggol Town Hub Hawker Centre'))
    pprint(convert(35955.52, 43336.13))

    # for resource_name, resource_id in RESOURCE_IDS.items():
    #     df = get_resource(resource_id)
    #     print(tabulate(df, headers=df.columns))
    #
    #     safe_name = '-'.join(''.join(char if char.isalpha() else ' ' for char in resource_name.lower()).split())
    #     timestamp = datetime.datetime.now().strftime('%Y-%m-%d--%H-%M-%S')
    #     path = Path(f'{safe_name}/{safe_name}--{timestamp}.csv')
    #     path.parent.mkdir(parents=True, exist_ok=True)
    #     df.to_csv(path, index=False)
