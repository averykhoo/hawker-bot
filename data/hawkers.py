import datetime
from dataclasses import dataclass
from enum import Enum
from enum import auto
from enum import unique
from typing import Optional


@dataclass
class DateRange:
    start: datetime.date  # inclusive
    end: datetime.date  # inclusive

    @property
    def dates(self):
        return [self.start + datetime.timedelta(days=x) for x in range((self.end - self.start).days + 1)]


@unique
class Status(Enum):
    EXISTING = auto()
    UNDER_CONSTRUCTION = auto()
    PROPOSED = auto()


status_map = {
    'Existing':           Status.EXISTING,
    'Existing (new)':     Status.EXISTING,  # whatever
    'Proposed':           Status.UNDER_CONSTRUCTION,
    'Under Construction': Status.PROPOSED,
}


@dataclass
class Hawker:
    name: str  # NAME
    status: Status
    latitude: float  # WGS84 (use point_lat because the LATITUDE value is sometimes missing)
    longitude: float  # WGS84 (use point_lon because the LONGITUDE value is sometimes missing)
    # landxaddresspoint: float  # SVY21 geodetic datum
    # landyaddresspoint: float  # SVY21 geodetic datum

    address_myenv: Optional[str] = None
    description_myenv: Optional[str] = None  # DESCRIPTION_MYENV

    # addresstype: Optional[str] = None  # 'I' or missing
    # addressunitnumber: Optional[str] = None  # missing
    # addressfloornumber: Optional[str] = None  # missing
    addressblockhousenumber: Optional[str] = None
    addressstreetname: Optional[str] = None
    addressbuildingname: Optional[str] = None  # located in this building
    addresspostalcode: Optional[int] = None  # 6 digits max

    region: Optional[str] = None  # REGION
    photourl: Optional[str] = None  # PHOTOURL

    no_of_food_stalls: int = 0  # if missing, assume zero available
    no_of_market_stalls: int = 0  # if missing, assume zero available
    rnr_status: Optional[str] = None  # repairs & redecoration (contains dates!)
    est_original_completion_date: Optional[str] = None  # probably when it was built? parse as '%d/%m/%Y' or '%Y'

    # ignored stuff
    # approximate_gfa: float  # gross floor area
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

    @property
    def rnr_period(self) -> Optional[DateRange]:
        if self.rnr_status is None:
            return None

        if self.rnr_status.startswith('<R&R>'):
            _flag, start_date, _to, end_date = self.rnr_status.split()  # "<R&R> 01/11/2020 to 28/02/2021"
            return DateRange(datetime.datetime.strptime(start_date, '%d/%m/%Y').date(),
                             datetime.datetime.strptime(end_date, '%d/%m/%Y').date())

    @property
    def est_original_completion_year(self) -> Optional[int]:
        if self.est_original_completion_date is None:
            return None
        year = self.est_original_completion_date[-4:]
        assert year.isdigit()
        return int(year)
