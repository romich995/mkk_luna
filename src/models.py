from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Text, String, ForeignKey, Table, Column, Integer
from geoalchemy2 import Geography

class Base(DeclarativeBase):
    pass

organisation_activity_association_table = Table(
    "organisation_activity_association_table",
    Base.metadata,
    Column("organisation_id", Integer, ForeignKey("organisations.id"), index=True),
    Column("activity_id", Integer, ForeignKey("activities.id"), index=True)

)

class Phone(Base):
    __tablename__ = "phones"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    phone: Mapped[str] = mapped_column(String(20))
    organisation_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"))

    organisation: Mapped["Organisation"] = relationship("Organisation", back_populates="phones")

class Organisation(Base):
    __tablename__ = "organisations"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(Text)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"))
    building: Mapped["Building"] = relationship("Building", back_populates="organisations")

    activities: Mapped[list["Activity"]] = relationship("Activity", secondary=organisation_activity_association_table, back_populates="organisations")

    phones: Mapped[list["Phone"]] = relationship("Phone", back_populates="organisation")

class Activity(Base):
    __tablename__ = "activities"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(Text)
    second_name: Mapped[str] = mapped_column(Text, nullable=True)
    third_name: Mapped[str] = mapped_column(Text, nullable=True)

    organisations = relationship("Organisation",
                                 secondary=organisation_activity_association_table,
                                 back_populates="activities" )

class Building(Base):
    __tablename__ = "buildings"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    address: Mapped[str] = mapped_column(Text)

    coordinate: Mapped[Geography] = mapped_column(Geography(geometry_type='POINT',
                                                            srid=4326,
                                                            spatial_index=True))

    organisations: Mapped[list["Organisation"]] = relationship("Organisation", back_populates="building")

