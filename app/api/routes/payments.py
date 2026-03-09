import asyncio
import contextlib

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_merchant, get_provider_signature
from app.clients.provider import build_provider_response, simulate_provider_flow
from app.core.config import get_settings
from app.core.security import signatures_match
from app.db.models import Merchant
from app.db.session import get_db_session
from app.redis import get_redis
from app.schemas.payment import (
    PaymentCreateRequest,
    PaymentResponse,
    ProfileResponse,
    ProviderPaymentRequest,
    ProviderPaymentResponse,
    ProviderWebhookPayload,
)
from app.services.payments import create_payment, dispatch_to_provider, get_profile
from app.services.webhooks import process_webhook

settings = get_settings()
router = APIRouter()
provider_router = APIRouter(prefix='/provider')


@router.get('/api/v1/me', response_model=ProfileResponse)
async def read_profile(
    merchant: Merchant = Depends(get_current_merchant),
    session: AsyncSession = Depends(get_db_session),
) -> ProfileResponse:
    profile = await get_profile(session, merchant.id)
    return ProfileResponse(**profile)


@router.post('/api/v1/payments', response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_merchant_payment(
    payload: PaymentCreateRequest,
    request: Request,
    merchant: Merchant = Depends(get_current_merchant),
    session: AsyncSession = Depends(get_db_session),
) -> PaymentResponse:
    payment = await create_payment(session, merchant, payload.external_invoice_id, payload.amount)
    task = asyncio.create_task(dispatch_to_provider(request.app, str(payment.id)))
    request.app.state.tasks.add(task)
    task.add_done_callback(lambda done: request.app.state.tasks.discard(done))
    return PaymentResponse(
        id=payment.id,
        external_invoice_id=payment.external_invoice_id,
        amount=payment.amount,
        status=payment.status,
    )


@router.post('/api/v1/provider/webhook', status_code=status.HTTP_202_ACCEPTED)
async def provider_webhook(
    request: Request,
    payload: ProviderWebhookPayload,
    raw_body: bytes = Depends(get_provider_signature),
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> Response:
    signature = request.state.provider_signature
    if not signatures_match(settings.provider_webhook_secret, raw_body, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid provider signature')

    await process_webhook(session, redis, payload.id, payload.external_invoice_id, payload.status)
    return Response(status_code=status.HTTP_202_ACCEPTED)


@provider_router.post('/api/v1/payments', response_model=ProviderPaymentResponse, status_code=status.HTTP_201_CREATED)
async def provider_create_payment(
    payload: ProviderPaymentRequest,
    request: Request,
    redis: Redis = Depends(get_redis),
) -> ProviderPaymentResponse:
    response_payload = build_provider_response(
        external_invoice_id=payload.external_invoice_id,
        amount=payload.amount,
        callback_url=payload.callback_url,
    )
    with contextlib.suppress(Exception):
        await redis.hset(
            f"provider_payment:{response_payload['id']}",
            mapping={
                'external_invoice_id': payload.external_invoice_id,
                'callback_url': payload.callback_url,
                'status': 'Created',
            },
        )

    task = asyncio.create_task(
        simulate_provider_flow(
            request.app,
            response_payload['id'],
            payload.external_invoice_id,
            payload.callback_url,
        )
    )
    request.app.state.tasks.add(task)
    task.add_done_callback(lambda done: request.app.state.tasks.discard(done))
    return ProviderPaymentResponse(**response_payload)
