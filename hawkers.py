import datetime
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from enum import auto
from enum import unique
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import pandas as pd
from geographiclib.constants import Constants
from geographiclib.geodesic import Geodesic

from nmd_bow import bow_ngram_movers_distance
from tokenizer import unicode_tokenize

WGS84 = Geodesic(Constants.WGS84_a, Constants.WGS84_f)


def text_similarity(text_1: str, text_2: str) -> float:
    return bow_ngram_movers_distance(bag_of_words_1=unicode_tokenize(text_1.lower(), words_only=True),
                                     bag_of_words_2=unicode_tokenize(text_2.lower(), words_only=True),
                                     invert=True,
                                     )


@dataclass(order=True)
class DateRange:
    start: datetime.date  # inclusive
    end: datetime.date  # inclusive

    def __post_init__(self):
        if isinstance(self.start, datetime.datetime):
            self.start = self.start.date()
        if not isinstance(self.start, datetime.date):
            raise TypeError(self.start)
        if isinstance(self.end, datetime.datetime):
            self.end = self.end.date()
        if not isinstance(self.end, datetime.date):
            raise TypeError(self.end)

    @property
    def dates(self):
        return [self.start + datetime.timedelta(days=x) for x in range((self.end - self.start).days + 1)]

    @property
    def month_name(self) -> str:
        today = datetime.date.today()
        if today.year == self.start.year and today.year == self.end.year:
            start = self.start.strftime('%b')
            end = self.end.strftime('%b')
        else:
            start = self.start.strftime('%b %Y').lstrip('0')
            end = self.end.strftime('%b %Y').lstrip('0')

        if start != end:
            return f'{start} - {end}'
        else:
            return start

    def __str__(self):
        if datetime.date.today().year == self.start.year:
            start = self.start.strftime('%d %b (%a)').lstrip('0')
        else:
            start = self.start.strftime('%d %b %Y (%a)').lstrip('0')
        if datetime.date.today().year == self.end.year:
            end = self.end.strftime('%d %b (%a)').lstrip('0')
        else:
            end = self.end.strftime('%d %b %Y (%a)').lstrip('0')

        if start != end:
            return f'{start} to {end}'
        else:
            return start


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

    cleaning_date_ranges: List[DateRange] = field(default_factory=list)

    other_works_period: Optional[DateRange] = None

    @staticmethod
    def from_row(dataframe_row):
        # handle nan
        for key, value in dataframe_row.items():
            if pd.isna(value):
                dataframe_row[key] = None

        return Hawker(name=dataframe_row['NAME'],
                      latitude=float(dataframe_row['point_lat']),
                      longitude=float(dataframe_row['point_lon']),
                      status=status_map[dataframe_row['STATUS']],
                      address_myenv=dataframe_row['ADDRESS_MYENV'],
                      description_myenv=dataframe_row['DESCRIPTION_MYENV'],
                      addressblockhousenumber=dataframe_row['ADDRESSBLOCKHOUSENUMBER'],
                      addressstreetname=dataframe_row['ADDRESSSTREETNAME'],
                      addressbuildingname=dataframe_row['ADDRESSBUILDINGNAME'],
                      addresspostalcode=dataframe_row['ADDRESSPOSTALCODE'],
                      region=dataframe_row['REGION'],
                      photourl=dataframe_row['PHOTOURL'],
                      no_of_food_stalls=int(dataframe_row['NO_OF_FOOD_STALLS'] or 0),
                      no_of_market_stalls=int(dataframe_row['NO_OF_MARKET_STALLS'] or 0),
                      rnr_status=dataframe_row['RNR_STATUS'],
                      est_original_completion_date=dataframe_row['EST_ORIGINAL_COMPLETION_DATE'],
                      )

    def add_cleaning_periods(self, dataframe_row):
        # handle nan
        for key, value in dataframe_row.items():
            if pd.isna(value):
                dataframe_row[key] = None

        for q in ['q1', 'q2', 'q3', 'q4']:
            try:
                start = datetime.datetime.strptime(dataframe_row[f'{q}_cleaningstartdate'], '%d/%m/%Y').date()
                end = datetime.datetime.strptime(dataframe_row[f'{q}_cleaningenddate'], '%d/%m/%Y').date()
                self.cleaning_date_ranges.append(DateRange(start, end))
            except ValueError:
                pass
            except TypeError:
                pass

        try:
            start = datetime.datetime.strptime(dataframe_row[f'other_works_startdate'], '%d/%m/%Y').date()
            end = datetime.datetime.strptime(dataframe_row[f'other_works_enddate'], '%d/%m/%Y').date()
            self.other_works_period = DateRange(start, end)
        except ValueError:
            pass
        except TypeError:
            pass

    @property
    def rnr_period(self) -> Optional[DateRange]:
        if self.rnr_status is None:
            return None

        if self.rnr_status.startswith('<R&R>'):
            _flag, start_date, _to, end_date = self.rnr_status.split()  # "<R&R> 01/11/2020 to 28/02/2021"
            return DateRange(datetime.datetime.strptime(start_date, '%d/%m/%Y').date(),
                             datetime.datetime.strptime(end_date, '%d/%m/%Y').date())

    @property
    def estimated_original_completion_date(self) -> Optional[datetime.date]:
        if self.est_original_completion_date is None:
            return None
        if len(self.est_original_completion_date) == 4:
            return datetime.datetime.strptime(f'31/12/{self.est_original_completion_date}', '%d/%m/%Y')
        else:
            return datetime.datetime.strptime(self.est_original_completion_date, '%d/%m/%Y')

    @property
    def estimated_original_completion_year(self) -> Optional[int]:
        if self.est_original_completion_date is None:
            return None
        year = self.est_original_completion_date[-4:]
        assert year.isdigit()
        return int(year)

    @property
    def closure_dates(self) -> List[datetime.date]:
        out = set()
        if self.rnr_period:
            out.update(self.rnr_period.dates)
        if self.other_works_period:
            out.update(self.other_works_period.dates)
        for date_range in self.cleaning_date_ranges:
            out.update(date_range.dates)
        return sorted(out)

    def closed_on_dates(self, *dates: Union[DateRange, datetime.date]):
        closed_dates = set(self.closure_dates)
        for date in dates:
            if isinstance(date, DateRange):
                for _date in date.dates:
                    if _date in closed_dates:
                        return True
                continue

            if isinstance(date, datetime.datetime):
                date = date.date()

            assert isinstance(date, datetime.date)
            if date in closed_dates:
                return True

        return False

    def distance_from(self, latitude: float, longitude: float) -> float:
        """
        uses vincenty algorithm
        slower than haversine, but more accurate
        """
        return WGS84.Inverse(latitude, longitude, self.latitude, self.longitude)['s12']

    def text_similarity(self, text: str) -> Tuple[float, float]:
        results = []
        for self_text in [self.name, self.description_myenv, self.address_myenv, self.addressbuildingname]:
            if self_text is not None:
                results.append(text_similarity(text, self_text))
        if not results:
            return 0.0, 0.0
        return max(results), sum(results)

    def to_markdown(self) -> str:
        # output markdown lines
        lines = []

        # photo and name
        if self.photourl:
            lines.append(f'[\u200B]({self.photourl})*{self.name}*')
        else:
            lines.append(f'*{self.name}*')

        # food stalls
        if self.no_of_food_stalls + self.no_of_food_stalls > 0:
            lines.append(f'_{self.no_of_food_stalls} food stalls, {self.no_of_market_stalls} market stalls_')

        # address
        address = self.address_myenv or f'{round(self.latitude, 5)}°N,{round(self.longitude, 5)}°E'
        lines.append(f'[{address}](https://www.google.com/maps/search/?api=1&query={self.latitude},{self.longitude})')

        # located in which building
        if self.addressbuildingname:
            lines.append(f'(located in {self.addressbuildingname})')

        # closure dates
        closed_dates = []
        for date_range in self.cleaning_date_ranges:
            closed_dates.append((date_range, f'{date_range.month_name} cleaning'))
        if self.rnr_period:
            closed_dates.append((self.rnr_period, f'{self.rnr_period.month_name} renovation'))
        if self.other_works_period and self.other_works_period != self.rnr_period:
            closed_dates.append((self.other_works_period, f'{self.other_works_period.month_name} repairs'))
        if closed_dates:
            closed_dates = sorted(closed_dates)
            for date_range, reason in closed_dates:
                lines.append(f'{reason}: {str(date_range)}')
        elif self.estimated_original_completion_date > datetime.datetime.today():
            if len(self.est_original_completion_date) == 4:
                lines.append(f'Opening in {self.est_original_completion_date}')
            else:
                lines.append(f'Opening on {self.estimated_original_completion_date.strftime("%d %b %Y")}')
        else:
            lines.append('No closure dates')

        # done, now join the lines into a single message
        return '  \n'.join(lines)


if __name__ == '__main__':
    hawkers = []
    df = pd.read_csv('data/hawker-centres/hawker-centres.csv')
    for i, row in df.iterrows():
        hawkers.append(Hawker.from_row(row))
        print(hawkers[-1])

    print()
    query = 'west coast'
    tmp = sorted(hawkers, key=lambda x: x.text_similarity(query), reverse=True)
    print(tmp[0].text_similarity(query), tmp[0])
    print(tmp[1].text_similarity(query), tmp[1])
    print(tmp[2].text_similarity(query), tmp[2])
    print(tmp[3].text_similarity(query), tmp[3])
    print(tmp[4].text_similarity(query), tmp[4])
    print(tmp[5].text_similarity(query), tmp[5])
