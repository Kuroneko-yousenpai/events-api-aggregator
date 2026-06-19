from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update as sa_update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Event, Place


class SqlAlchemyPlaceRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def upsert(self, place_data: dict) -> Place:
        stmt = (
            pg_insert(Place)
            .values(
                id=place_data["id"],
                name=place_data["name"],
                city=place_data["city"],
                address=place_data["address"],
                seats_pattern=place_data["seats_pattern"],
                changed_at=place_data["changed_at"],
                created_at=place_data["created_at"],
            )
            .on_conflict_do_update(
                index_elements=[Place.id],
                set_={
                    "name": place_data["name"],
                    "city": place_data["city"],
                    "address": place_data["address"],
                    "seats_pattern": place_data["seats_pattern"],
                    "changed_at": place_data["changed_at"],
                },
            )
            .returning(Place)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()


class SqlAlchemyEventRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def upsert(self, event_data: dict, place_id: UUID) -> Event:
        stmt = (
            pg_insert(Event)
            .values(
                id=event_data["id"],
                name=event_data["name"],
                place_id=place_id,
                event_time=event_data["event_time"],
                registration_deadline=event_data["registration_deadline"],
                status=event_data["status"],
                number_of_visitors=event_data["number_of_visitors"],
                changed_at=event_data["changed_at"],
                created_at=event_data["created_at"],
                status_changed_at=event_data["status_changed_at"],
            )
            .on_conflict_do_update(
                index_elements=[Event.id],
                set_={
                    "name": event_data["name"],
                    "place_id": place_id,
                    "event_time": event_data["event_time"],
                    "registration_deadline": event_data["registration_deadline"],
                    "status": event_data["status"],
                    "number_of_visitors": event_data["number_of_visitors"],
                    "changed_at": event_data["changed_at"],
                    "status_changed_at": event_data["status_changed_at"],
                },
            )
            .returning(Event)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get(self, event_id: UUID) -> Event | None:
        stmt = select(Event).options(selectinload(Event.place)).where(Event.id == event_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        date_from: datetime | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Event], int]:
        filters = []
        if date_from is not None:
            filters.append(Event.event_time >= date_from)

        count_stmt = select(func.count()).select_from(Event)
        for f in filters:
            count_stmt = count_stmt.where(f)
        total = (await self._session.execute(count_stmt)).scalar_one()

        stmt = (
            select(Event)
            .options(selectinload(Event.place))
            .order_by(Event.event_time)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        for f in filters:
            stmt = stmt.where(f)

        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def increment_visitors(self, event_id: UUID, delta: int) -> None:
        stmt = (
            sa_update(Event)
            .where(Event.id == event_id)
            .values(
                number_of_visitors=func.greatest(
                    0, Event.number_of_visitors + delta
                )
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()
