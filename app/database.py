from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_session():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
