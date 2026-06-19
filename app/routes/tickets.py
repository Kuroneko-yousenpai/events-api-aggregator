from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_cancel_ticket_usecase, get_create_ticket_usecase
from app.schemas import CancelTicketResponse, CreateTicketRequest, CreateTicketResponse
from app.usecases.tickets import (
    CancelTicketUsecase,
    CreateTicketUsecase,
    EventNotFound,
    EventNotPublished,
    RegistrationClosed,
    SeatNotAvailable,
    TicketNotFound,
)

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


@router.post("", response_model=CreateTicketResponse, status_code=201)
async def create_ticket(
    data: CreateTicketRequest,
    usecase: CreateTicketUsecase = Depends(get_create_ticket_usecase),
) -> CreateTicketResponse:
    try:
        ticket = await usecase.do(
            event_id=data.event_id,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            seat=data.seat,
        )
    except EventNotFound as exc:
        raise HTTPException(status_code=404, detail="Event not found") from exc
    except EventNotPublished as exc:
        raise HTTPException(
            status_code=400, detail="Event is not published for registration"
        ) from exc
    except RegistrationClosed as exc:
        raise HTTPException(status_code=400, detail="Registration deadline has passed") from exc
    except SeatNotAvailable as exc:
        raise HTTPException(status_code=400, detail="Seat is already taken") from exc

    return CreateTicketResponse(ticket_id=ticket.id)


@router.delete("/{ticket_id}", response_model=CancelTicketResponse)
async def cancel_ticket(
    ticket_id: UUID,
    usecase: CancelTicketUsecase = Depends(get_cancel_ticket_usecase),
) -> CancelTicketResponse:
    try:
        await usecase.do(ticket_id)
    except TicketNotFound as exc:
        raise HTTPException(status_code=404, detail="Ticket not found") from exc
    except EventNotFound as exc:
        raise HTTPException(status_code=404, detail="Event not found") from exc

    return CancelTicketResponse(success=True)
