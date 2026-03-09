from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import PaymentStatus


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    merchant_id: UUID
    merchant_name: str
    total_balance: Decimal
    reserved_balance: Decimal
    available_balance: Decimal


class PaymentCreateRequest(BaseModel):
    external_invoice_id: str = Field(min_length=1, max_length=255)
    amount: Decimal = Field(gt=0)


class PaymentResponse(BaseModel):
    id: UUID
    external_invoice_id: str
    amount: Decimal
    status: PaymentStatus


class ProviderPaymentRequest(BaseModel):
    external_invoice_id: str
    amount: str
    callback_url: str


class ProviderPaymentResponse(BaseModel):
    id: str
    external_invoice_id: str
    amount: int
    callback_url: str
    status: str


class ProviderWebhookPayload(BaseModel):
    id: str
    external_invoice_id: str
    status: str
