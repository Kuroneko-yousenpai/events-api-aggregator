import os
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import get_session
from app.main import app
from app.models import Base, Event, Place

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://app:secret@localhost:5432/events_test",
)


@pytest_asyncio.fixture
async def setup_database():
    engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def session(setup_database) -> AsyncGenerator[AsyncSession, None]:
    engine = setup_database
    TestSession = async_sessionmaker(engine, expire_on_commit=False)
    async with TestSession() as s:
        yield s


@pytest_asyncio.fixture
async def client(setup_database) -> AsyncGenerator[AsyncClient, None]:
    engine = setup_database
    TestSession = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_session():
        async with TestSession() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def place(session: AsyncSession) -> Place:
    p = Place(
        id=uuid.uuid4(),
        name="Tech Park Hall",
        city="Moscow",
        address="Lenina st, 1",
        seats_pattern="A1-10,B1-10",
        changed_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    session.add(p)
    await session.commit()
    await session.refresh(p)
    return p


@pytest_asyncio.fixture
async def published_event(session: AsyncSession, place: Place) -> Event:
    now = datetime.now(timezone.utc)
    e = Event(
        id=uuid.uuid4(),
        name="Python Conference",
        place_id=place.id,
        event_time=now + timedelta(days=10),
        registration_deadline=now + timedelta(days=5),
        status="published",
        number_of_visitors=0,
        changed_at=now,
        created_at=now,
        status_changed_at=now,
    )
    session.add(e)
    await session.commit()
    await session.refresh(e)
    e.place = place
    return e


@pytest_asyncio.fixture
async def unpublished_event(session: AsyncSession, place: Place) -> Event:
    now = datetime.now(timezone.utc)
    e = Event(
        id=uuid.uuid4(),
        name="Draft Event",
        place_id=place.id,
        event_time=now + timedelta(days=10),
        registration_deadline=now + timedelta(days=5),
        status="new",
        number_of_visitors=0,
        changed_at=now,
        created_at=now,
        status_changed_at=now,
    )
    session.add(e)
    await session.commit()
    await session.refresh(e)
    e.place = place
    return e


@pytest_asyncio.fixture
async def expired_event(session: AsyncSession, place: Place) -> Event:
    now = datetime.now(timezone.utc)
    e = Event(
        id=uuid.uuid4(),
        name="Past Conference",
        place_id=place.id,
        event_time=now - timedelta(days=1),
        registration_deadline=now - timedelta(hours=1),
        status="published",
        number_of_visitors=0,
        changed_at=now,
        created_at=now,
        status_changed_at=now,
    )
    session.add(e)
    await session.commit()
    await session.refresh(e)
    e.place = place
    return e
