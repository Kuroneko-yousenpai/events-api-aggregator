from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.cache import TTLCache
from app.config import SEATS_CACHE_TTL_SECONDS
from app.dependencies import (
    get_get_event_usecase,
    get_get_seats_usecase,
    get_list_events_usecase,
)
from app.schemas import (
    EventDetail,
    EventListItem,
    EventListResponse,
    PlaceDetailed,
    PlaceShort,
    SeatsResponse,
)
from app.usecases.events import (
    EventNotFound,
    EventNotPublished,
    GetEventUsecase,
    GetSeatsUsecase,
    ListEventsUsecase,
)

router = APIRouter(prefix="/api/events", tags=["events"])

_seats_cache: TTLCache[list[str]] = TTLCache(ttl_seconds=SEATS_CACHE_TTL_SECONDS)


@router.get("", response_model=EventListResponse)
async def list_events(
    request: Request,
    date_from: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    usecase: ListEventsUsecase = Depends(get_list_events_usecase),
) -> EventListResponse:
    date_from_dt = (
        datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc)
        if date_from is not None
        else None
    )

    events, total = await usecase.do(date_from_dt, page, page_size)

    base_url = str(request.url).split("?")[0]
    has_next = page * page_size < total
    has_previous = page > 1

    def page_url(p: int) -> str:
        params = request.query_params.multi_items()
        kept = [(k, v) for k, v in params if k != "page"]
        kept.append(("page", str(p)))
        query = "&".join(f"{k}={v}" for k, v in kept)
        return f"{base_url}?{query}"

    return EventListResponse(
        count=total,
        next=page_url(page + 1) if has_next else None,
        previous=page_url(page - 1) if has_previous else None,
        results=[
            EventListItem(
                id=e.id,
                name=e.name,
                place=PlaceShort.model_validate(e.place),
                event_time=e.event_time,
                registration_deadline=e.registration_deadline,
                status=e.status,
                number_of_visitors=e.number_of_visitors,
            )
            for e in events
        ],
    )


@router.get("/{event_id}", response_model=EventDetail)
async def get_event(
    event_id: UUID,
    usecase: GetEventUsecase = Depends(get_get_event_usecase),
) -> EventDetail:
    try:
        event = await usecase.do(event_id)
    except EventNotFound as exc:
        raise HTTPException(status_code=404, detail="Event not found") from exc

    return EventDetail(
        id=event.id,
        name=event.name,
        place=PlaceDetailed.model_validate(event.place),
        event_time=event.event_time,
        registration_deadline=event.registration_deadline,
        status=event.status,
        number_of_visitors=event.number_of_visitors,
    )


@router.get("/{event_id}/seats", response_model=SeatsResponse)
async def get_seats(
    event_id: UUID,
    usecase: GetSeatsUsecase = Depends(get_get_seats_usecase),
) -> SeatsResponse:
    cache_key = str(event_id)
    cached = _seats_cache.get(cache_key)
    if cached is not None:
        return SeatsResponse(event_id=event_id, available_seats=cached)

    try:
        seats = await usecase.do(event_id)
    except EventNotFound as exc:
        raise HTTPException(status_code=404, detail="Event not found") from exc
    except EventNotPublished as exc:
        raise HTTPException(
            status_code=400, detail="Event is not published for registration"
        ) from exc

    _seats_cache.set(cache_key, seats)
    return SeatsResponse(event_id=event_id, available_seats=seats)
