import datetime
from dataclasses import dataclass
from typing import List
from typing import Optional

from api_wrappers.data_gov_sg.datatypes import ResourceFormat


@dataclass
class DatasetMetadata:
    dataset_id: str
    name: str
    format: ResourceFormat

    managed_by: str
    contact_emails: List[str]

    created_at: datetime.datetime
    last_updated_at: datetime.datetime
    coverage_start: Optional[datetime.datetime]
    coverage_end: Optional[datetime.datetime]

    @classmethod
    def from_json(cls, json_obj):
        return DatasetMetadata(dataset_id=json_obj['datasetId'],
                               name=json_obj['name'],
                               format=ResourceFormat(json_obj['format']),
                               managed_by=json_obj['managedBy'],
                               contact_emails=json_obj['contactEmails'],
                               created_at=datetime.datetime.fromisoformat(json_obj['createdAt']),
                               last_updated_at=datetime.datetime.fromisoformat(json_obj['lastUpdatedAt']),
                               coverage_start=datetime.datetime.fromisoformat(json_obj['coverageStart'])
                               if 'coverageStart' in json_obj else None,
                               coverage_end=datetime.datetime.fromisoformat(json_obj['coverageEnd'])
                               if 'coverageEnd' in json_obj else None,
                               )
