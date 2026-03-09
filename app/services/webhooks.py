from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import quantize_amount
from app.db.models import Balance, Payment, PaymentStatus


async def process_webhook(
    session: AsyncSession,
    redis,
    provider_payment_id: str,
    external_invoice_id: str,
    status: str,
) -> None:
    dedupe_key = f'webhook:{provider_payment_id}:{status}'
    if not await redis.set(dedupe_key, '1', ex=300, nx=True):
        return

    payment = await session.scalar(
        select(Payment).where(
            Payment.provider_payment_id == provider_payment_id,
            Payment.external_invoice_id == external_invoice_id,
        )
    )
    if payment is None:
        return

    balance = await session.scalar(
        select(Balance).where(Balance.merchant_id == payment.merchant_id).with_for_update()
    )
    if balance is None:
        return

    if status == 'Created' and payment.status == PaymentStatus.CREATED:
        payment.status = PaymentStatus.PROCESSING
    elif status == 'Completed' and payment.status in {PaymentStatus.CREATED, PaymentStatus.PROCESSING}:
        payment.status = PaymentStatus.COMPLETED
        balance.reserved_amount = quantize_amount(balance.reserved_amount - payment.amount)
        balance.total_amount = quantize_amount(balance.total_amount - payment.amount)
    elif status == 'Canceled' and payment.status in {PaymentStatus.CREATED, PaymentStatus.PROCESSING}:
        payment.status = PaymentStatus.CANCELED
        balance.reserved_amount = quantize_amount(balance.reserved_amount - payment.amount)
    await session.commit()
