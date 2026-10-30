from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from src.db import Base, get_async_session
from src.app import app
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

DATABASE_URL = "sqlite+aiosqlite:///./test_test.db"

test_engine = create_async_engine(DATABASE_URL)

test_async_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def setup_test_db():
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


async def override_get_async_session():
    async with test_async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def client(setup_test_db):
    app.dependency_overrides[get_async_session] = override_get_async_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def db_session(setup_test_db):
    async with test_async_session_maker() as session:
        yield session
