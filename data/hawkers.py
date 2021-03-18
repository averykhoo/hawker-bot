from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from typing import Tuple


@dataclass
class Hawker:
    name: str  # NAME
    latitude: float  # WGS84 (converted from SVY21 via OneMap API because this is occasionally missing)
    longitude: float  # WGS84 (converted from SVY21 via OneMap API because this is occasionally missing)
    # landxaddresspoint: float  # SVY21 geodetic datum
    # landyaddresspoint: float  # SVY21 geodetic datum

    address_myenv: Optional[str]
    description_myenv: Optional[str]  # DESCRIPTION_MYENV

    # addresstype: Optional[str]  # 'I' or missing
    # addressunitnumber: Optional[str]  # missing
    # addressfloornumber: Optional[str]  # missing
    addressblockhousenumber: Optional[str]
    addressstreetname: Optional[str]
    addressbuildingname: Optional[str]  # located in this building
    addresspostalcode: Optional[int]  # 6 digits max

    region: Optional[str]  # REGION
    photourl: Optional[str]  # PHOTOURL
    no_of_food_stalls: int  # if missing, assume zero available
    no_of_market_stalls: int  # if missing, assume zero available
    status: str  # Existing, Existing (new), Proposed, Under Construction

    # rnr_status: Optional[str]  # repairs & redecoration (contains dates!)
    rnr_period: Optional[Tuple[datetime.date, datetime.date]]

    # est_original_completion_date: Optional[str]  # probably when it was built? parse as '%d/%m/%Y' or '%Y'
    est_original_completion_year: Optional[int]

    # approximate_gfa: Optional[float]  # gross floor area
    # awarded_date: str  # ??? parse as '%d/%m/%Y'
    # cleaningenddate: str  # use other API for this
    # cleaningstartdate: str  # use other API for this
    # fmel_upd_d: str  # something update date? parse as '%Y%m%d%H%M%S'
    # hup_completion_date: str  # related to Hawker Centres Upgrading Programme (HUP)
    # description: str  # related to Hawker Centres Upgrading Programme (HUP)
    # hyperlink: str  # missing
    # implementation_date: str  # ???
    # inc_crc: str  # 16 hexadecimal chars
    # info_on_co_locators: str  # nearby amenities? split by '/' to get a list
