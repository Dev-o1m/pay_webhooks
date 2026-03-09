from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Header, HTTPException, Request, status

from app.core.security import signatures_match
from app.db.models import Merchant
from app.db.session import get_db_session


async def get_current_merchant(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    x_api_key: str | None = Header(default=None),
    x_signature: str | None = Header(default=None),
) -> Merchant:
    if not x_api_key or x_signature is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Missing authentication headers')

    merchant = await session.scalar(select(Merchant).where(Merchant.api_token == x_api_key))
    if merchant is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid API token')

    body = await request.body()
    if not signatures_match(merchant.api_secret, body, x_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid request signature')

    return merchant


async def get_provider_signature(
    request: Request,
    x_provider_signature: str | None = Header(default=None),
) -> bytes:
    if x_provider_signature is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Missing provider signature')

    request.state.provider_signature = x_provider_signature
    return await request.body()
