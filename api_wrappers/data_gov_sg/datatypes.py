import datetime
import os
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional
from typing import Union
from uuid import UUID

import pandas as pd
import requests


class ResourceFormat(Enum):
    CSV = 'CSV'
    PDF = 'PDF'
    KML = 'KML'
    SHP = 'SHP'
    API = 'API'
    GEO = 'GeoJSON'  # undocumented


@dataclass
class Resource:
    id: UUID
    dataset_id: UUID
    revision_id: UUID

    name: str
    format: ResourceFormat
    description: str
    url: str
    url_type: Optional[str]  # {'s3', None}

    created: datetime.datetime
    last_modified: datetime.datetime
    coverage_start: Optional[datetime.date]
    coverage_end: Optional[datetime.date]

    @classmethod
    def from_json(cls, json_obj):
        return Resource(id=UUID(json_obj['id']),
                        dataset_id=UUID(json_obj['package_id']),
                        revision_id=UUID(json_obj['revision_id']),
                        name=json_obj['name'],
                        format=ResourceFormat(json_obj['format']),
                        description=json_obj['description'],
                        url=json_obj['url'],
                        url_type=json_obj['url_type'],
                        created=datetime.datetime.fromisoformat(json_obj['created']),
                        last_modified=datetime.datetime.fromisoformat(json_obj['last_modified']),
                        coverage_start=datetime.date.fromisoformat(json_obj['coverage_start'])
                        if 'coverage_start' in json_obj else None,
                        coverage_end=datetime.date.fromisoformat(json_obj['coverage_end'])
                        if 'coverage_end' in json_obj else None,
                        )

    def save(self, path: Union[str, os.PathLike, Path]):
        # check not exists
        path = Path(path).resolve()
        if path.is_dir():
            raise IsADirectoryError(path)
        if path.exists():
            raise FileExistsError(path)

        # get file
        r = requests.get(self.url, verify=False)
        if r.status_code != 200:
            raise RuntimeError(self.url)

        # save file
        with path.open('wb') as f:
            f.write(r.content)

        return path


@dataclass
class Organization:
    id: UUID
    revision_id: UUID

    name: str
    title: str
    description: str

    created: datetime.datetime

    @classmethod
    def from_json(cls, json_obj):
        return Organization(id=UUID(json_obj['id']),
                            revision_id=UUID(json_obj['revision_id']),
                            name=json_obj['name'],
                            title=json_obj['title'],
                            description=json_obj['description'],
                            created=datetime.datetime.fromisoformat(json_obj['created']),
                            )


@dataclass
class Dataset:
    id: UUID
    owner_org_id: UUID

    name: str
    title: str
    resources: List[Resource]
    organization: Organization

    metadata_created: datetime.datetime
    metadata_modified: datetime.datetime

    def __post_init__(self):
        assert self.owner_org_id == self.organization.id

    @classmethod
    def from_json(cls, json_obj):
        return Dataset(id=UUID(json_obj['id']),
                       owner_org_id=UUID(json_obj['owner_org']),
                       name=json_obj['name'],
                       title=json_obj['title'],
                       resources=[Resource.from_json(elem) for elem in json_obj['resources']],
                       organization=Organization.from_json(json_obj['organization']),
                       metadata_created=datetime.datetime.fromisoformat(json_obj['metadata_created']),
                       metadata_modified=datetime.datetime.fromisoformat(json_obj['metadata_modified']),
                       )


@dataclass
class DataStoreResult:
    fields: List[Dict[str, str]]  # {'type': {'int4', 'text', ...}, 'id': Resource.name}
    records: List[Dict[str, Union[bool, int, float, str]]]
    total: int
    offset: int
    limit: int
    filters: Dict[str, Union[bool, int, float, str]]

    __df: Optional[pd.DataFrame] = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self):
        assert len(self.records) <= self.limit
        assert '_id' in self.field_names

    @classmethod
    def from_json(cls, json_obj):
        return DataStoreResult(fields=json_obj['fields'],
                               records=json_obj['records'],
                               total=json_obj['total'],
                               offset=json_obj.get('offset', 0),
                               limit=json_obj.get('limit', 100),
                               filters=json_obj.get('filters', dict()),
                               )

    @property
    def field_names(self):
        return [_field['id'] for _field in self.fields]

    @property
    def df(self):
        if self.__df is None:
            self.__df = pd.DataFrame(self.records)
            self.__df = self.__df.sort_values(by='_id')  # sort rows
            self.__df = self.__df[self.field_names]  # sort columns
            self.__df = self.__df.drop(columns=['_id'])  # drop '_id' column
        return self.__df.copy()
