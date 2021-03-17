import datetime
import json
from pathlib import Path
from pprint import pprint

import pandas as pd
import requests
from tabulate import tabulate

RESOURCE_IDS = {
    'Dates of Hawker Centres Closure':
        'b80cb643-a732-480d-86b5-e03957bc82aa',
    'List of Government Markets Hawker Centres':
        '8f6bba57-19fc-4f36-8dcf-c0bda382364d',
    'List of NEA Licensed Eating Establishments with Grades, Demerit Points and Suspension History':
        '34f86c3e-a90c-4de9-a69f-afc86b7f31b6'
}

if __name__ == '__main__':
    resource_name = 'Dates of Hawker Centres Closure'
    r = requests.get('https://data.gov.sg/api/action/datastore_search',
                     params={
                         'resource_id': RESOURCE_IDS[resource_name],
                         'limit':       1,
                     })
    data = json.loads(r.content)
    pprint(data)

    r = requests.get('https://data.gov.sg/api/action/datastore_search',
                     params={
                         'resource_id': RESOURCE_IDS[resource_name],
                         'limit':       data['result']['total'],
                     })
    data = json.loads(r.content)
    df = pd.DataFrame(data['result']['records'])
    df = df.sort_values(by='_id')
    df = df[[field['id'] for field in data['result']['fields']]]
    print(tabulate(df, headers=df.columns))
    safe_name = '-'.join(''.join(char if char.isalpha() else ' ' for char in resource_name.lower()).split())
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d--%H-%M-%S')
    path = Path(f'data/{safe_name}/{safe_name}--{timestamp}.csv')
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
