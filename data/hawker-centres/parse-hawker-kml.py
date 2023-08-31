import pandas as pd
from bs4 import BeautifulSoup

# from https://beta.data.gov.sg/datasets/1445/resources/d_ccca3606c337a5c386b9c88dc0dd08b6/view
with open('HawkerCentresKML.kml', 'rb') as f:
    soup = BeautifulSoup(f.read(), 'lxml-xml')

items = []
for placemark in soup.find_all('Placemark'):
    data = placemark.find('ExtendedData')
    out = {
        'NAME':                         None,
        'LATITUDE':                     None,
        'LONGITUDE':                    None,
        'ADDRESS_MYENV':                None,
        'DESCRIPTION_MYENV':            None,
        'ADDRESSTYPE':                  None,
        'ADDRESSBLOCKHOUSENUMBER':      None,
        'ADDRESSFLOORNUMBER':           None,
        'ADDRESSUNITNUMBER':            None,
        'ADDRESSSTREETNAME':            None,
        'ADDRESSPOSTALCODE':            None,
        'ADDRESSBUILDINGNAME':          None,
        'REGION':                       None,
        'PHOTOURL':                     None,
        'STATUS':                       None,
        'RNR_STATUS':                   None,

        'APPROXIMATE_GFA':              None,
        'AWARDED_DATE':                 None,
        'CLEANINGENDDATE':              None,
        'CLEANINGSTARTDATE':            None,
        'DESCRIPTION':                  None,
        'EST_ORIGINAL_COMPLETION_DATE': None,
        'FMEL_UPD_D':                   None,
        'HUP_COMPLETION_DATE':          None,
        'HYPERLINK':                    None,
        'IMPLEMENTATION_DATE':          None,
        'INC_CRC':                      None,
        'INFO_ON_CO_LOCATORS':          None,
        'LANDXADDRESSPOINT':            None,
        'LANDYADDRESSPOINT':            None,
        'NO_OF_FOOD_STALLS':            None,
        'NO_OF_MARKET_STALLS':          None,
    }
    for _data in data.find_all('SimpleData'):
        if _data['name'] in out:
            out[_data['name']] = _data.text
    for point in placemark.find_all('Point'):
        lon, lat, alt = point.text.strip().split(',')
        assert alt == '0.0'
        out['point_lat'] = lat
        out['point_lon'] = lon
    items.append(out)

df = pd.DataFrame(items)

df.to_csv('hawker-centres.csv', index=False)
