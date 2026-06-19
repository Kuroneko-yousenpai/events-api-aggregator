import enum

import sqlalchemy as sa
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class EventStatus(str, enum.Enum):
    new = "new"
    published = "published"


class SyncStatus(str, enum.Enum):
    idle = "idle"
    running = "running"
    success = "success"
    failed = "failed"


class Place(Base):
    __tablename__ = "places"

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String, nullable=False)
    city = Column(String, nullable=False, index=True)
    address = Column(String, nullable=False)
    seats_pattern = Column(String, nullable=False)
    changed_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)

    events = relationship("Event", back_populates="place")


class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String, nullable=False)
    place_id = Column(UUID(as_uuid=True), ForeignKey("places.id"), nullable=False)
    event_time = Column(DateTime(timezone=True), nullable=False, index=True)
    registration_deadline = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, nullable=False, default=EventStatus.new.value)
    number_of_visitors = Column(Integer, nullable=False, default=0)
    changed_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    status_changed_at = Column(DateTime(timezone=True), nullable=False)

    place = relationship("Place", back_populates="events")
    tickets = relationship("Ticket", back_populates="event")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(UUID(as_uuid=True), primary_key=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    seat = Column(String, nullable=False)
    is_cancelled = Column(sa.Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    event = relationship("Event", back_populates="tickets")


class SyncState(Base):
    __tablename__ = "sync_state"

    id = Column(Integer, primary_key=True, default=1)
    last_sync_time = Column(DateTime(timezone=True), nullable=True)
    last_changed_at = Column(DateTime(timezone=True), nullable=True)
    sync_status = Column(String, nullable=False, default=SyncStatus.idle.value)
    last_error = Column(Text, nullable=True)
