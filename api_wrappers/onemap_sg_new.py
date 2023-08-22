import logging
import time
from dataclasses import dataclass
from typing import Optional

import requests


@dataclass
class OneMapAPI:
    email: str
    password: str

    _token: Optional[str] = None
    _token_expiry: int = 0

    @property
    def token(self):
        current_time = time.time()
        if not self._token or self._token_expiry < current_time:
            r = requests.post('https://www.onemap.gov.sg/api/auth/post/getToken',
                              json={'email':    self.email,
                                    'password': self.password},
                              verify=False)
            assert r.status_code == 200
            self._token = r.json()['access_token']
            self._token_expiry = int(r.json()['expiry_timestamp'])
        return self._token

    def onemap_search(self, query, result_limit=25):
        """
        Each page of json response is restricted to a maximum of 10 results.
        Parameter       Type    Optional    Description
        searchVal       String  Required    Keywords entered by user that is used to filter out the results.
        returnGeom      {Y/N}   Required    Checks if user wants to return the geometry.
        getAddrDetails  {Y/N}   Required    Checks if user wants to return address details for a point.
        pageNum         Int     Optional    Specifies the page to retrieve your search results from.

        :param query:
        :return:
        """
        query = query.strip()
        if not query:
            logging.info('QUERY_ONEMAP_BLANK')
            return []

        results = []
        page_num = 0
        total_pages = 1
        while page_num < total_pages:
            page_num += 1
            data = dict()

            # run query
            for retry_attempt in range(3):
                # noinspection PyBroadException
                try:
                    r = requests.get('https://developers.onemap.sg/commonapi/search',
                                     params={'searchVal':      query,
                                             'returnGeom':     'Y',
                                             'getAddrDetails': 'Y',
                                             'pageNum':        page_num},
                                     verify=False,
                                     headers={'authorization': f'Bearer {self.token}'})
                    data = r.json()
                    break

                except Exception:
                    if retry_attempt == 2:
                        raise

            # catch error
            if 'error' in data:
                logging.warning(f'QUERY_ONEMAP_ERROR={query} PAGE_NUM={page_num}')
                return results
                # return _reorder_onemap_results(query, results)[:result_limit]

            # append to results
            for result in data.get('results', []):
                results.append(dict(block_no=result['BLK_NO'].strip(),
                                    road_name=result['ROAD_NAME'].strip(),
                                    building_name=result['BUILDING'].strip() or result['ADDRESS'].strip(),
                                    zipcode=result['POSTAL'].strip(),
                                    latitude=float(result['LATITUDE']),
                                    longitude=float(result['LONGITUDE']),
                                    svy21_x=float(result['X']),
                                    svy21_y=float(result['Y']),
                                    _address=result['ADDRESS'].strip(),
                                    ))

            # check number of pages and results
            total_pages = data.get('totalNumPages', page_num)
            assert page_num == data.get('pageNum', page_num), data
            if page_num == total_pages:
                assert len(results) == data['found'], data

            # if we have enough results, stop querying
            if len(results) >= result_limit:
                break

        return results
        # return _reorder_onemap_results(query, results)[:result_limit]


if __name__ == '__main__':
    test = OneMapAPI('averykhoo@gmail.com', 'xxxxx')
    print(test.onemap_search('toa payoh mrt'))
    print(test.onemap_search('200640'))
    print(test.onemap_search('kranji camp'))
    print(test.onemap_search('maxwell road'))
    print(test.onemap_search('vivocity'))
