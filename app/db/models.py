import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PaymentStatus(str, enum.Enum):
    CREATED = 'Created'
    PROCESSING = 'Processing'
    COMPLETED = 'Completed'
    CANCELED = 'Canceled'


class Merchant(Base):
    __tablename__ = 'merchants'

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    api_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    api_secret: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    balance: Mapped['Balance'] = relationship(back_populates='merchant', uselist=False)
    payments: Mapped[list['Payment']] = relationship(back_populates='merchant')


class Balance(Base):
    __tablename__ = 'balances'

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey('merchants.id', ondelete='CASCADE'), unique=True, nullable=False
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal('0.00'))
    reserved_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal('0.00')
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    merchant: Mapped['Merchant'] = relationship(back_populates='balance')


class Payment(Base):
    __tablename__ = 'payments'
    __table_args__ = (
        UniqueConstraint('merchant_id', 'external_invoice_id', name='uq_payment_merchant_invoice'),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey('merchants.id', ondelete='CASCADE'), nullable=False
    )
    external_invoice_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_payment_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    callback_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(
            PaymentStatus,
            name='payment_status',
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=PaymentStatus.CREATED,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    merchant: Mapped['Merchant'] = relationship(back_populates='payments')