import asyncio
import random
from decimal import Decimal
from typing import Any

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.clients.provider import ProviderClient
from app.core.config import get_settings
from app.core.security import quantize_amount
from app.db.models import Balance, Merchant, Payment, PaymentStatus

settings = get_settings()


async def create_payment(
    session: AsyncSession,
    merchant: Merchant,
    external_invoice_id: str,
    amount: Decimal,
) -> Payment:
    normalized_amount = quantize_amount(amount)
    callback_url = f"{settings.public_base_url}/api/v1/provider/webhook"

    try:
        balance = await session.scalar(
            select(Balance)
            .where(Balance.merchant_id == merchant.id)
            .with_for_update()
        )
        if balance is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Balance not found')

        available = quantize_amount(balance.total_amount - balance.reserved_amount)
        if normalized_amount > available:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Insufficient available balance')

        balance.reserved_amount = quantize_amount(balance.reserved_amount + normalized_amount)
        payment = Payment(
            merchant_id=merchant.id,
            external_invoice_id=external_invoice_id,
            amount=normalized_amount,
            callback_url=callback_url,
            status=PaymentStatus.CREATED,
        )
        session.add(payment)
        await session.flush()
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='external_invoice_id already exists') from exc
    except Exception:
        await session.rollback()
        raise

    await session.refresh(payment)
    return payment


async def get_profile(session: AsyncSession, merchant_id: Any) -> dict[str, Any]:
    merchant = await session.scalar(
        select(Merchant).options(selectinload(Merchant.balance)).where(Merchant.id == merchant_id)
    )
    if merchant is None or merchant.balance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Merchant not found')

    total = quantize_amount(merchant.balance.total_amount)
    reserved = quantize_amount(merchant.balance.reserved_amount)
    available = quantize_amount(total - reserved)
    return {
        'merchant_id': merchant.id,
        'merchant_name': merchant.name,
        'total_balance': total,
        'reserved_balance': reserved,
        'available_balance': available,
    }


async def dispatch_to_provider(app, payment_id: str) -> None:
    from app.db.session import SessionLocal

    delay = random.uniform(settings.request_delay_min_seconds, settings.request_delay_max_seconds)
    await asyncio.sleep(delay)

    async with SessionLocal() as session:
        payment = await session.scalar(select(Payment).where(Payment.id == payment_id))
        if payment is None or payment.status != PaymentStatus.CREATED:
            return

        client = ProviderClient(app=app)
        try:
            provider_payment = await client.create_payment(
                external_invoice_id=payment.external_invoice_id,
                amount=payment.amount,
                callback_url=payment.callback_url,
            )
        except httpx.HTTPError:
            return

        payment.provider_payment_id = provider_payment['id']
        payment.status = PaymentStatus.PROCESSING
        await session.commit()
