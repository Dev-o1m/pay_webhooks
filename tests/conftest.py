import os
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

os.environ['APP_NAME'] = 'Pay Webhooks Test'
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./test.db'
os.environ['ALEMBIC_DATABASE_URL'] = 'sqlite:///./test.db'
os.environ['REDIS_URL'] = 'redis://localhost:6379/1'
os.environ['PROVIDER_BASE_URL'] = 'http://testserver/provider'
os.environ['PUBLIC_BASE_URL'] = 'http://testserver'
os.environ['PROVIDER_WEBHOOK_SECRET'] = 'provider-webhook-secret'
os.environ['REQUEST_DELAY_MIN_SECONDS'] = '0'
os.environ['REQUEST_DELAY_MAX_SECONDS'] = '0'
os.environ['PROVIDER_DECISION_DELAY_SECONDS'] = '0'
os.environ['TESTING'] = 'true'

from app.core.security import build_signature
from app.db.base import Base
from app.db.models import Balance, Merchant, Payment
from app.main import app
from app.redis import get_redis


class FakeRedis:
    def __init__(self):
        self.storage = {}

    async def set(self, key, value, ex=None, nx=False):
        if nx and key in self.storage:
            return False
        self.storage[key] = value
        return True

    async def hset(self, key, mapping):
        self.storage[key] = dict(mapping)
        return len(mapping)

    async def aclose(self):
        return None


TEST_DB_PATH = Path('test.db')
engine = create_async_engine(os.environ['DATABASE_URL'], future=True)
TestSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def override_get_redis():
    yield app.state.redis


@pytest_asyncio.fixture(scope='session', autouse=True)
async def prepare_database():
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        merchant = Merchant(
            id=UUID('11111111-1111-1111-1111-111111111111'),
            name='Demo Merchant',
            api_token='merchant-demo-token',
            api_secret='merchant-demo-secret',
        )
        backup = Merchant(
            id=UUID('22222222-2222-2222-2222-222222222222'),
            name='Backup Merchant',
            api_token='merchant-backup-token',
            api_secret='merchant-backup-secret',
        )
        session.add_all(
            [
                merchant,
                backup,
                Balance(
                    merchant_id=merchant.id,
                    total_amount=Decimal('1000.00'),
                    reserved_amount=Decimal('0.00'),
                ),
                Balance(
                    merchant_id=backup.id,
                    total_amount=Decimal('500.00'),
                    reserved_amount=Decimal('0.00'),
                ),
            ]
        )
        await session.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest_asyncio.fixture(autouse=True)
async def app_state():
    app.state.tasks = set()
    app.state.redis = FakeRedis()
    app.dependency_overrides[get_redis] = override_get_redis

    async with TestSessionLocal() as session:
        await session.execute(delete(Payment))
        await session.execute(
            update(Balance)
            .where(Balance.merchant_id == UUID('11111111-1111-1111-1111-111111111111'))
            .values(total_amount=Decimal('1000.00'), reserved_amount=Decimal('0.00'))
        )
        await session.execute(
            update(Balance)
            .where(Balance.merchant_id == UUID('22222222-2222-2222-2222-222222222222'))
            .values(total_amount=Decimal('500.00'), reserved_amount=Decimal('0.00'))
        )
        await session.commit()

    yield
    if app.state.tasks:
        await wait_for_tasks()
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://testserver') as async_client:
        yield async_client


async def wait_for_tasks(timeout: float = 1.0):
    import asyncio

    deadline = asyncio.get_running_loop().time() + timeout
    while app.state.tasks and asyncio.get_running_loop().time() < deadline:
        await asyncio.sleep(0.05)


def auth_headers(secret: str, token: str, body: bytes = b'') -> dict[str, str]:
    return {
        'x-api-key': token,
        'x-signature': build_signature(secret, body),
    }


@pytest_asyncio.fixture
async def session():
    async with TestSessionLocal() as db_session:
        yield db_session
