import datetime

from pydantic import BaseModel
from pydantic_extra_types.phone_numbers import PhoneNumber
from pydantic_extra_types.coordinate import Latitude, Longitude

class BuildingGet(BaseModel):
    id: int
    address: str
    longitude: Longitude
    latitude: Latitude


class OrganisationGet(BaseModel):
    id: int
    name: str
    phones: list[PhoneNumber]
    building: BuildingGet
    activities: list[str]
