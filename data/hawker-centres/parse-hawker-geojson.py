import json
from pathlib import Path

import pandas as pd

# Path setup
input_file = Path('hawker-centres-geojson.geojson')
output_file = Path('hawker-centres.csv')


def parse_geojson():
    if not input_file.exists():
        print(f"Error: {input_file} not found!")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    rows = []
    for feature in data.get('features', []):
        props = feature.get('properties', {})
        geom = feature.get('geometry', {})
        coords = geom.get('coordinates', [None, None])

        # Map new GeoJSON properties to the CSV columns expected by hawkers.py
        # Note: the bot logic relies on 'point_lat' and 'point_lon' for proximity
        row = {
            'NAME': props.get('NAME'),
            'ADDRESS_MYENV': props.get('ADDRESS_MYENV'),
            'DESCRIPTION_MYENV': props.get('DESCRIPTION'),  # Map to description
            'ADDRESSBLOCKHOUSENUMBER': props.get('ADDRESSBLOCKHOUSENUMBER'),
            'ADDRESSSTREETNAME': props.get('ADDRESSSTREETNAME'),
            'ADDRESSPOSTALCODE': props.get('ADDRESSPOSTALCODE'),
            'ADDRESSBUILDINGNAME': props.get('ADDRESSBUILDINGNAME'),
            'STATUS': props.get('STATUS'),
            'PHOTOURL': props.get('PHOTOURL'),
            'EST_ORIGINAL_COMPLETION_DATE': props.get('EST_ORIGINAL_COMPLETION_DATE'),
            'HUP_COMPLETION_DATE': props.get('HUP_COMPLETION_DATE'),

            # Map 'NUMBER_OF_COOKED_FOOD_STALLS' to 'NO_OF_FOOD_STALLS'
            'NO_OF_FOOD_STALLS': props.get('NUMBER_OF_COOKED_FOOD_STALLS', 0),

            # These columns are often used for mapping
            'LANDXADDRESSPOINT': props.get('LANDXADDRESSPOINT'),
            'LANDYADDRESSPOINT': props.get('LANDYADDRESSPOINT'),

            # WGS84 coordinates from the geometry object
            'point_lon': coords[0],
            'point_lat': coords[1],

            # Placeholder for columns that might be missing in new format but needed for init
            'NO_OF_MARKET_STALLS': 0,
            'RNR_STATUS': props.get('RNR_STATUS'),  # May be null
            'REGION': props.get('REGION'),
            'LATITUDE': coords[1],  # Duplicate for safety
            'LONGITUDE': coords[0]
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    # Clean up: Replace 'None' or empty strings in specific columns to prevent logic errors
    df['NO_OF_FOOD_STALLS'] = pd.to_numeric(df['NO_OF_FOOD_STALLS'], errors='coerce').fillna(0).astype(int)

    df.to_csv(output_file, index=False)
    print(f"Successfully converted {len(df)} hawker centres to {output_file}")


if __name__ == '__main__':
    parse_geojson()
