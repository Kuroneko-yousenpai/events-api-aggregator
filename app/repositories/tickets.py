from __future__ import annotations

from uuid import UUID

from sqlalchemy import func
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
        ticket = Ticket(
            id=ticket_id,
            event_id=event_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            seat=seat,
        )
        self._session.add(ticket)
        await self._session.flush()
        return ticket

    async def get(self, ticket_id: UUID) -> Ticket | None:
        return await self._session.get(Ticket, ticket_id)

    async def mark_cancelled(self, ticket_id: UUID) -> None:
        ticket = await self._session.get(Ticket, ticket_id)
        if ticket is not None:
            ticket.is_cancelled = True
            ticket.cancelled_at = func.now()
