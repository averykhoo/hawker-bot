import datetime
import logging
import re
from pathlib import Path
from typing import Tuple

import pandas as pd
import requests

from api_wrappers.data_gov_sg.data_api import get_datastore
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
    # todo: ths has yet to be migrated to v2 api
    # see: https://guide.data.gov.sg/developers/api-v1
    df = pd.DataFrame(get_datastore(dataset_id).records)
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


if __name__ == '__main__':
    # List of Government Markets Hawker Centres
    # print(get_datastore('d_68a42f09f350881996d83f9cd73ab02f'))
    # print(get_dataset_df('d_68a42f09f350881996d83f9cd73ab02f'))

    # Historical Daily Weather
    # 2009-01-01 to 2017-11-30
    # print(get_dataset_df('d_03bb2eb67ad645d0188342fa74ad7066'))

    # Air Temperature across Singapore
    # 2016-05-05 to today
    # r = requests.get('https://api.data.gov.sg/v1/environment/air-temperature?date=2016-05-05')
    # print(r.json())

    # Hawker Centres
    # dead
    # print(get_datastore('d_ccca3606c337a5c386b9c88dc0dd08b6'))
    # print(requests.get('https://api-production.data.gov.sg/v2/public/api/datasets/'
    #                    'd_ccca3606c337a5c386b9c88dc0dd08b6'
    #                    '/metadata').json())
    print(get_datastore('d_4a086da0a5553be1d89383cd90d07ecd'))
    print(requests.get('https://api-production.data.gov.sg/v2/public/api/datasets/'
                       'd_4a086da0a5553be1d89383cd90d07ecd'
                       '/metadata').json())
    # these probably don't work anymore, link expires in less than 24h
    url_kml = 'https://s3.ap-southeast-1.amazonaws.com/blobs.data.gov.sg/d_ccca3606c337a5c386b9c88dc0dd08b6.kml?AWSAccessKeyId=ASIAU7LWPY2WOCJIORZ3&Expires=1697812477&Signature=oSztpFw7FduItPtl1HYOHOdnMVw%3D&X-Amzn-Trace-Id=Root%3D1-653281ed-697d8c223b2b62ba150bc085%3BParent%3D40a859c547ae304d%3BSampled%3D1%3BLineage%3D80cb18ff%3A0&response-content-disposition=attachment%3B%20filename%3D%22HawkerCentresKML.kml%22&x-amz-security-token=IQoJb3JpZ2luX2VjEL7%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaDmFwLXNvdXRoZWFzdC0xIkcwRQIgZs4hG3TZxSIS4X1RQx5nWy2a0H2tTSxoBKbbZRdsXiwCIQDhkqcgamPM%2Br6pRCWP5YDaSaNhQgg5zr7rrCteCFfwsCqxAwjX%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAQaDDM0MjIzNTI2ODc4MCIMhjMi%2B%2FrTPlXTN51EKoUDotoMsX7fTgL4uQbs7vS3vNzOiaIBQn6wezcAkHY6ken6j76vkIDdWimEh52hJVnaOqax9pOFItYB5bCAg16N0AvrPg4NP0xROcKSzDj4MFAb1Z4yO8%2FbJW2uHPVSkz6yRuf7k2nX0LyGIB0KMiIrx%2BKauH3dYg%2FfQeo5u760RpYH42O5R3UbDGhdJc3HqLlESLNwlgAd0uNHgoMVnBy8fned5uOo1x4Fa5UZA%2BIwaeZkWz2LdU68kd0GDcYpJZHmBPDP8e4qXCFV73d%2Fe4Tv3z6EFOns93uhK4eMuGR265GaX%2FTyVS%2BulKQrEQ8msMKy0EGBKcNn%2BemIwCW9Xwwo%2BOcYOJuur5TH1LuLAsQCoJ6B%2F7sLTkyBgpfiF%2FTgGUU1JVMNkRXRdBLeJA0nbZYALxwZrmEM9rZb%2B%2B%2BKDwH7ZhRK18RpMbyhV%2B8A6IrO2jFF5rlzwekFMLT4lHznih8jLCeOZXhH1hbIkRlkOZGvnq7sRdRIj8a9%2FDcaTRu198Rq6k3QxyQwqILKqQY6nQF09d454x3ZAqxOOdtRINVlVVoyJLngO%2BmzLQ%2FuVT2IYxDZeaa2Z4I%2BJM1W4rYMLvLbeKl4Wmq%2FQDU%2BLBHV9T1vxcxsC01Y86a5kG6Jad9UFBA%2FCy6D4yqTYfeziS18ru%2Bu5TxrVhampfY%2B9P04MjBMfhgNWyk7IM4pdn4u3ZrTvCB%2BbJ5Kg5mOMlsMKKGZ0NrziYrN9EmCW7y1IfHg'
    url_geojson = 'https://s3.ap-southeast-1.amazonaws.com/blobs.data.gov.sg/d_4a086da0a5553be1d89383cd90d07ecd.geojson?AWSAccessKeyId=ASIAU7LWPY2WH4SLO647&Expires=1697812479&Signature=Lr6B%2FklMktIj4Fz0GnF6ZSvDeP0%3D&X-Amzn-Trace-Id=Root%3D1-653281ed-11488f114fadac647611b9b9%3BParent%3D58029b86407023da%3BSampled%3D1%3BLineage%3D80cb18ff%3A0&response-content-disposition=attachment%3B%20filename%3D%22HawkerCentresGEOJSON.geojson%22&x-amz-security-token=IQoJb3JpZ2luX2VjEL7%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaDmFwLXNvdXRoZWFzdC0xIkcwRQIhAMvIlw%2FLALnwWNy9nbYynb0UCovK3HwlT3bzHH2IF7txAiBev0X0VN90HtMf4KglS7Aaxz99r9u3igMZeClOht1B6iqxAwjX%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAQaDDM0MjIzNTI2ODc4MCIMQzkfQQVKPH9tnYr7KoUDNQwziS52G59w5FxmSpQbBYXOhjqv%2BtLog%2BqaAqZOWpJKRCICi02gfA8I0S44bN3R7N0RaDRZinLRIn9vWdD%2FGvx5CDivvK%2BEw6x6%2F%2FCmWklAZDAu%2Fg76bQUJFynBzdXvR6BDUXsuKazA4hQoeJDfMoHHtLm8b9z3BPxiFBQzOv6qCm7qJQ%2B%2BwFjLB3H6PnL1u0CQa8uqpldCyMdZ762l8lXAkRQA2DH%2FrKFWm9Io7nL3StN%2BRK4e4rTQIkxSJSKyOc2%2BhJLXjolF8k92O2pMmwL2M0hPjUFGQ5W2p4%2F68KfIpbGLQVsWQsDPvNhdFyCcaxleSW55x2ohTi6TdS505aDgXX89kj1du8EFLZmg%2ByXmooELVNkeSoH0CPFu3Ozkv6FrK%2Fub2SfDfnx9Z7K6h17nUqO0Rm6kyXEepuqjwUdezALjnDFCyIeOEhv3hPBR1yWy4%2BPC3brxEWKTcf%2BBUCJwfuG4rQockDmikoHzMVqqecA79qL%2FZWIs66uWOuc5adidKKIw7YPKqQY6nQFBXeG%2FUdjGdvv%2FzoGtGq0kbT35r3SP%2B6n5uNHQz7IFw3cdWKhh7QWd2oJ9cN2p6JAiz2yG%2BN9LOZhz67KqL%2FwS%2FZPk9pHy9TMc9yn05mzkgJKpdk77sXG5zX40QrEj2553aSWQV1f8%2BFlvOt7xO5Dwa%2F7XhN2dUV6LI2zJq4ElxgFM7h5q4ChYjnl5hmWo3AeubR7ZqoOXIdrWYLzN'
