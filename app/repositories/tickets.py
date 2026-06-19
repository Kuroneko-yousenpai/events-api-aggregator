from __future__ import annotations

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Ticket


class SqlAlchemyTicketRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        ticket_id: UUID,
        event_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> Ticket:
        stmt = (
            pg_insert(Ticket)
            .values(
                id=ticket_id,
                event_id=event_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                seat=seat,
                is_cancelled=False,
            )
            .on_conflict_do_update(
                index_elements=[Ticket.id],
                set_={
                    "event_id": event_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "seat": seat,
                    "is_cancelled": False,
                    "cancelled_at": None,
                },
            )
            .returning(Ticket)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get(self, ticket_id: UUID) -> Ticket | None:
        return await self._session.get(Ticket, ticket_id)

    async def mark_cancelled(self, ticket_id: UUID) -> None:
        ticket = await self._session.get(Ticket, ticket_id)
        if ticket is not None:
            ticket.is_cancelled = True
            ticket.cancelled_at = func.now()
