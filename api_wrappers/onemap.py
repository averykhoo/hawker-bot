import json
import logging

import requests

from api_wrappers.caching import cache_1h


@cache_1h
def query_onemap(query):
    query = query.strip()
    if not query:
        logging.info('QUERY_ONEMAP_BLANK')
        return []

    results = []
    page_num = 0
    total_pages = 1
    while page_num < total_pages:
        page_num += 1

        # run query
        r = requests.get('https://developers.onemap.sg/commonapi/search',
                         params={'searchVal':      query,
                                 'returnGeom':     'Y',
                                 'getAddrDetails': 'Y',
                                 'pageNum':        page_num,
                                 })
        data = json.loads(r.content)

        # catch error
        if 'error' in data:
            logging.warning(f'QUERY_ONEMAP_ERROR={query} PAGE_NUM={page_num}')
            return results

        # append to results
        results.extend(data.get('results', []))
        total_pages = data.get('totalNumPages', page_num)
        assert page_num == data.get('pageNum', page_num), data
        if page_num == total_pages:
            assert len(results) == data['found'], data
    return results
