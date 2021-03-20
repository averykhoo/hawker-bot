from pprint import pprint

from data.hawker_data import locate_zip
from data.hawker_data import query_onemap

if __name__ == '__main__':
    pprint(query_onemap('078881'))
    pprint(locate_zip('078881'))