from typing import Annotated
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import joinedload, selectinload
from geoalchemy2.functions import ST_Distance, ST_GeographyFromText, ST_X, ST_Y
from pydantic_extra_types.coordinate import Latitude, Longitude
from shapely import from_wkb

from schemas import OrganisationGet
from models import Base, Organisation, Building, Activity, Phone, organisation_activity_association_table
from db import engine, get_db_session, AsyncSessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


    session = AsyncSessionLocal()

    building = Building(address="РФ г. Москва Кутузовский проспект д. 49",
                        coordinate=ST_GeographyFromText(f"POINT(55.731718 37.487362)"))
    organisation = Organisation(name='''ООО "Рога и копыта"''', building=building)

    phone_0 = Phone(phone="+7 916 999 99 99")
    phone_1 = Phone(phone="+7 916 888 88 88")

    organisation.phones.append(phone_0)
    organisation.phones.append(phone_1)

    activity_0 = Activity(first_name="Еда")
    activity_1 = Activity(first_name="Еда", second_name="Молочная продукция")
    activity_2 = Activity(first_name="Еда", second_name="Мясная продукция")

    organisation.activities.append(activity_1)
    organisation.activities.append(activity_2)

    session.add_all([building, organisation, activity_0, activity_1, activity_2, phone_0, phone_1])

    building_2 = Building(address="РФ г. Москва Кутузовский проспект д. 48",
                        coordinate=ST_GeographyFromText(f"POINT(55.731018 37.486362)"))
    organisation_2 = Organisation(name='''ООО "Рога и копыта 2"''', building=building)

    phone_2 = Phone(phone="+7 916 999 99 98")
    phone_3 = Phone(phone="+7 916 888 88 89")

    organisation_2.phones.append(phone_2)
    organisation_2.phones.append(phone_3)

    activity_3 = Activity(first_name="Еда", second_name="Мясная продукция", third_name="Говядина")
    activity_4 = Activity(first_name="Еда", second_name="Мясная продукция", third_name="Свинина")
    activity_5 = Activity(first_name="Еда", second_name="Мясная продукция", third_name="Баранина")

    organisation_2.activities.append(activity_5)
    organisation_2.activities.append(activity_4)


    session.add_all([building_2, organisation_2, activity_3, activity_4, phone_2, phone_3])

    await session.commit()

    await session.close()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


app = FastAPI(lifespan=lifespan)


def building_to_pydantic(building: Building):
    building_to_pydantic = dict()
    building_to_pydantic["id"] = building.id
    building_to_pydantic["address"] = building.address
    loaded_point = from_wkb(building.coordinate.data)
    building_to_pydantic["longitude"] = loaded_point.x
    building_to_pydantic["latitude"] = loaded_point.y
    return building_to_pydantic

def organisation_to_pydantic(organisation, building=None):
    organisation_dict = dict()
    organisation_dict["id"] = organisation.id
    organisation_dict["name"] = organisation.name
    phones = organisation.phones
    organisation_dict["phones"] = [phone.phone for phone in phones]
    organisation_dict["building"] = building_to_pydantic(building) if building else building_to_pydantic(organisation.building)
    organisation_dict["activities"] = [coalesce(activity.third_name, activity.second_name, activity.first_name) \
                                       for activity in organisation.activities]
    return organisation_dict

def coalesce(*args):
    for arg in args:
        if arg is not None:
            return arg

@app.get("/building/{building_id}/organisations", response_model=list[OrganisationGet] )
async def get_organisations_by_building_id(building_id: int,
                          async_session: Annotated[AsyncSession, Depends(get_db_session)]):
    building = await async_session.get(Building, building_id)
    if not building:
        raise HTTPException(status_code=404, detail={"error": "Building not found"})

    organisations_stmt = select(Organisation)\
        .where(Organisation.building_id == building_id)\
        .options(selectinload(Organisation.phones))\
        .options(selectinload(Organisation.activities))
    organisations = (await async_session.execute(organisations_stmt)).scalars()
    return [organisation_to_pydantic(organisation, building) for organisation in organisations]

@app.get("/activity/{activity_id}/organisations", response_model=list[OrganisationGet])
async def get_organisations_by_activity(activity_id: int,
                                        async_session: Annotated[AsyncSession, Depends(get_db_session)]):
    organisations_stmt = select(Organisation)\
        .join(organisation_activity_association_table)\
        .where(organisation_activity_association_table.c.activity_id == activity_id)\
        .options(selectinload(Organisation.phones))\
        .options(selectinload(Organisation.activities))\
        .options(joinedload(Organisation.building))

    organisations = (await async_session.execute(organisations_stmt)).scalars()
    return [organisation_to_pydantic(organisation) for organisation in organisations]


@app.get("/distance/organisations", response_model=list[OrganisationGet])
async def get_organisations_at_distance_from_coordinate(distance: float,
                                                        longitude: Longitude,
                                                        latitude: Latitude,
                                        async_session: Annotated[AsyncSession, Depends(get_db_session)]):
    organisations_stmt = select(Organisation, )\
        .join(Building)\
        .where(ST_Distance(Building.coordinate,\
                       ST_GeographyFromText(f"""POINT({longitude} {latitude})""")) <= distance) \
        .options(selectinload(Organisation.phones)) \
        .options(selectinload(Organisation.activities)) \
        .options(joinedload(Organisation.building))

    organisations = (await async_session.execute(organisations_stmt)).scalars()

    return [organisation_to_pydantic(organisation) for organisation in organisations]


@app.get("/organisation/{organisation_id}", response_model=OrganisationGet)
async def get_organisation_by_id(organisation_id: int,
                                 async_session: Annotated[AsyncSession, Depends(get_db_session)]):

    organisation_stmt = select(Organisation).where(Organisation.id == organisation_id)\
        .options(selectinload(Organisation.phones))\
        .options(selectinload(Organisation.activities))\
        .options(joinedload(Organisation.building))

    organisation = (await async_session.execute(organisation_stmt)).scalar_one_or_none()

    if not organisation:
        raise HTTPException(status_code=404, detail={"error": "Organisation not found"})

    return organisation_to_pydantic(organisation)


@app.get("/organisations", response_model=list[OrganisationGet])
async def get_organisation_by_name(organisation_name: str,
                                 async_session: Annotated[AsyncSession, Depends(get_db_session)]):

    organisations_stmt = select(Organisation)\
        .where(func.lower(Organisation.name).like(f"%{organisation_name.lower()}%"))\
        .options(selectinload(Organisation.phones))\
        .options(selectinload(Organisation.activities))\
        .options(joinedload(Organisation.building))

    organisations = (await async_session.execute(organisations_stmt)).scalars()
    return [organisation_to_pydantic(organisation) for organisation in organisations]
@app.get("/activity/organisations", response_model=list[OrganisationGet])
async def get_organisations_by_activity_name(activity_name: str,
                                             async_session: Annotated[AsyncSession, Depends(get_db_session)]):
    organisations_stmt = select(Organisation)\
        .where(Organisation.activities.any(or_(
            func.lower(Activity.first_name).like(f"%{activity_name.lower()}%"),
            func.lower(Activity.second_name).like(f"%{activity_name.lower()}%"),
            func.lower(Activity.third_name).like(f"%{activity_name.lower()}%")))) \
        .options(selectinload(Organisation.phones)) \
        .options(selectinload(Organisation.activities)) \
        .options(joinedload(Organisation.building))

    organisations = (await async_session.execute(organisations_stmt)).scalars()

    return [organisation_to_pydantic(organisation) for organisation in organisations]
