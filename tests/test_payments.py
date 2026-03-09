import json
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db.models import Balance, Payment, PaymentStatus
from tests.conftest import auth_headers, wait_for_tasks


@pytest.mark.asyncio
async def test_get_profile_returns_balance(client):
    response = await client.get(
        '/api/v1/me',
        headers=auth_headers('merchant-demo-secret', 'merchant-demo-token'),
    )

    assert response.status_code == 200
    assert response.json() == {
        'merchant_id': '11111111-1111-1111-1111-111111111111',
        'merchant_name': 'Demo Merchant',
        'total_balance': '1000.00',
        'reserved_balance': '0.00',
        'available_balance': '1000.00',
    }


@pytest.mark.asyncio
async def test_successful_payment_reserves_then_debits_balance(client, session):
    payload = {'external_invoice_id': 'order-1', 'amount': '125.50'}
    body = json.dumps(payload, separators=(',', ':')).encode('utf-8')

    response = await client.post(
        '/api/v1/payments',
        content=body,
        headers={
            **auth_headers('merchant-demo-secret', 'merchant-demo-token', body),
            'content-type': 'application/json',
        },
    )

    assert response.status_code == 201
    assert response.json()['status'] == 'Created'

    await wait_for_tasks()

    payment = await session.scalar(select(Payment).where(Payment.external_invoice_id == 'order-1'))
    balance = await session.scalar(select(Balance).where(Balance.merchant_id == payment.merchant_id))

    assert payment is not None
    assert payment.status == PaymentStatus.COMPLETED
    assert balance.total_amount == Decimal('874.50')
    assert balance.reserved_amount == Decimal('0.00')


@pytest.mark.asyncio
async def test_canceled_payment_releases_reserved_amount(client, session):
    payload = {'external_invoice_id': 'cancel-order-2', 'amount': '40.00'}
    body = json.dumps(payload, separators=(',', ':')).encode('utf-8')

    response = await client.post(
        '/api/v1/payments',
        content=body,
        headers={
            **auth_headers('merchant-demo-secret', 'merchant-demo-token', body),
            'content-type': 'application/json',
        },
    )

    assert response.status_code == 201
    await wait_for_tasks()

    payment = await session.scalar(select(Payment).where(Payment.external_invoice_id == 'cancel-order-2'))
    balance = await session.scalar(select(Balance).where(Balance.merchant_id == payment.merchant_id))

    assert payment is not None
    assert payment.status == PaymentStatus.CANCELED
    assert balance.total_amount == Decimal('1000.00')
    assert balance.reserved_amount == Decimal('0.00')


@pytest.mark.asyncio
async def test_payment_rejected_when_available_balance_is_not_enough(client):
    payload = {'external_invoice_id': 'too-big', 'amount': '5000.00'}
    body = json.dumps(payload, separators=(',', ':')).encode('utf-8')

    response = await client.post(
        '/api/v1/payments',
        content=body,
        headers={
            **auth_headers('merchant-demo-secret', 'merchant-demo-token', body),
            'content-type': 'application/json',
        },
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Insufficient available balance'
