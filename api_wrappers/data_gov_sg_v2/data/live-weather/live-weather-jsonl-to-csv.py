import bz2
import csv

import orjson as json

if __name__ == '__main__':
    with open('data--2023-10-26--23-16-37.csv', 'w', newline='') as f2:
        c = csv.writer(f2)
        c.writerow(['station_id',
                    'station_name',
                    'station_latitude',
                    'station_longitude',
                    'temperature_degrees_c',
                    'timestamp',
                    ])

        with bz2.open('data--2023-10-26--23-16-37.jsonl.bz2') as f:  # total 2735 lines
            for i, line in enumerate(f):
                if (i + 1) % 100 == 0:
                    print(f'processing line {i + 1}')

                # load json
                data = json.loads(line)
                # assert all(station['id'] == station['device_id'] for station in data['metadata']['stations'])
                metadata = {station['id']: station for station in data['metadata']['stations']}

                # write csv rows
                for item in data['items']:
                    # timestamp = datetime.datetime.fromisoformat(item['timestamp'])
                    for reading in item['readings']:
                        c.writerow([
                            reading['station_id'],
                            metadata[reading['station_id']]['name'],
                            metadata[reading['station_id']]['location']['latitude'],
                            metadata[reading['station_id']]['location']['longitude'],
                            reading['value'],
                            item['timestamp'],
                        ])
                #         print(reading)
                #         reading['station_name'] = metadata[reading['station_id']]['name']
                #         reading['station_latitude'] = metadata[reading['station_id']]['location']['latitude']
                #         reading['station_longitude'] = metadata[reading['station_id']]['location']['longitude']
                #         reading['timestamp'] = timestamp
                #         print(reading)
                #         print(metadata[reading['station_id']])
                #         1 / 0
                # assert all(all(reading['station_id'] in metadata for reading in item['readings']) for item in data['items'])
