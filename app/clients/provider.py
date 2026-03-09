from decimal import Decimal
from uuid import uuid4

import httpx

from app.core.config import get_settings
from app.core.security import build_signature
from app.schemas.payment import ProviderWebhookPayload

settings = get_settings()


class ProviderClient:
    def __init__(self, app=None):
        self.app = app

    async def create_payment(self, external_invoice_id: str, amount: Decimal, callback_url: str) -> dict:
        payload = {
            'external_invoice_id': external_invoice_id,
            'amount': f'{amount:.2f}',
            'callback_url': callback_url,
        }
        transport = httpx.ASGITransport(app=self.app) if settings.testing and self.app is not None else None
        client_kwargs = {'transport': transport, 'timeout': 10.0}
        if transport:
            client_kwargs['base_url'] = 'http://testserver'

        async with httpx.AsyncClient(**client_kwargs) as client:
            target_url = '/provider/api/v1/payments' if transport else f"{settings.provider_base_url}/api/v1/payments"
            response = await client.post(target_url, json=payload)
            response.raise_for_status()
            return response.json()


async def deliver_webhook(app, callback_url: str, payload: ProviderWebhookPayload) -> None:
    body = payload.model_dump_json().encode('utf-8')
    signature = build_signature(settings.provider_webhook_secret, body)
    transport = httpx.ASGITransport(app=app) if settings.testing and app is not None else None
    client_kwargs = {'transport': transport, 'timeout': 10.0}
    if transport:
        client_kwargs['base_url'] = 'http://testserver'

    async with httpx.AsyncClient(**client_kwargs) as client:
        target_url = callback_url.replace('http://testserver', '') if transport else callback_url
        await client.post(
            target_url,
            content=body,
            headers={'content-type': 'application/json', 'x-provider-signature': signature},
        )


async def simulate_provider_flow(app, provider_payment_id: str, external_invoice_id: str, callback_url: str) -> None:
    created_payload = ProviderWebhookPayload(
        id=provider_payment_id,
        external_invoice_id=external_invoice_id,
        status='Created',
    )
    await deliver_webhook(app, callback_url, created_payload)

    import asyncio

    await asyncio.sleep(settings.provider_decision_delay_seconds)
    final_status = 'Canceled' if external_invoice_id.lower().startswith('cancel') else 'Completed'
    final_payload = ProviderWebhookPayload(
        id=provider_payment_id,
        external_invoice_id=external_invoice_id,
        status=final_status,
    )
    await deliver_webhook(app, callback_url, final_payload)


def build_provider_response(external_invoice_id: str, amount: str, callback_url: str) -> dict:
    provider_payment_id = str(uuid4())
    pennies = int((Decimal(amount) * 100).to_integral_value())
    return {
        'id': provider_payment_id,
        'external_invoice_id': external_invoice_id,
        'amount': pennies,
        'callback_url': callback_url,
        'status': 'Created',
    }
