import datetime
import json
from pathlib import Path

import requests

data_path = Path(f'data/live-weather/data--{datetime.datetime.now().strftime("%Y-%m-%d--%H-%M-%S")}.jsonl')

if __name__ == '__main__':

    data_path.parent.mkdir(parents=True, exist_ok=True)
    assert not data_path.exists()

    start_date = datetime.date(2016, 5, 1)
    end_date = datetime.date.today()

    _date = start_date - datetime.timedelta(days=1)

    while _date < end_date:
        # increment date
        _date += datetime.timedelta(days=1)

        # get data
        e = None
        for _ in range(3):
            try:
                r = requests.get('https://api.data.gov.sg/v1/environment/air-temperature',
                                 params={'date': _date.strftime("%Y-%m-%d")})
                assert r.status_code == 200
                break
            except Exception as e:
                continue
        else:
            raise e
        data = r.json()

        # write data
        with data_path.open('a') as f:
            json.dump(data, f, ensure_ascii=True)
            f.write('\n')

        # check status
        assert data['api_info']['status'] == 'healthy'

        # parse metadata
        metadata = {station['id']: station for station in data['metadata']['stations']}

        # check data
        print(_date, len(data['items']))
        assert all(all(reading['station_id'] in metadata for reading in item['readings']) for item in data['items'])
        # print(data)
        # break
