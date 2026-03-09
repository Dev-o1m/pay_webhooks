"""init schema with seed data"""

import uuid
from decimal import Decimal

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '20260309_0001'
down_revision = None
branch_labels = None
depends_on = None


payment_status = postgresql.ENUM(
    'Created',
    'Processing',
    'Completed',
    'Canceled',
    name='payment_status',
    create_type=False,
)


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'payment_status') THEN
                CREATE TYPE payment_status AS ENUM ('Created', 'Processing', 'Completed', 'Canceled');
            END IF;
        END
        $$;
        """
    )

    op.create_table(
        'merchants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False, unique=True),
        sa.Column('api_token', sa.String(length=255), nullable=False, unique=True),
        sa.Column('api_secret', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        'balances',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            'merchant_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('merchants.id', ondelete='CASCADE'),
            nullable=False,
            unique=True,
        ),
        sa.Column('total_amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('reserved_amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        'payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            'merchant_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('merchants.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('external_invoice_id', sa.String(length=255), nullable=False),
        sa.Column('provider_payment_id', sa.String(length=255), unique=True, nullable=True),
        sa.Column('amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('callback_url', sa.String(length=1024), nullable=False),
        sa.Column('status', payment_status, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('merchant_id', 'external_invoice_id', name='uq_payment_merchant_invoice'),
    )

    merchant_1_id = uuid.UUID('11111111-1111-1111-1111-111111111111')
    merchant_2_id = uuid.UUID('22222222-2222-2222-2222-222222222222')

    op.bulk_insert(
        sa.table(
            'merchants',
            sa.column('id', postgresql.UUID(as_uuid=True)),
            sa.column('name', sa.String()),
            sa.column('api_token', sa.String()),
            sa.column('api_secret', sa.String()),
        ),
        [
            {
                'id': merchant_1_id,
                'name': 'Demo Merchant',
                'api_token': 'merchant-demo-token',
                'api_secret': 'merchant-demo-secret',
            },
            {
                'id': merchant_2_id,
                'name': 'Backup Merchant',
                'api_token': 'merchant-backup-token',
                'api_secret': 'merchant-backup-secret',
            },
        ],
    )
    op.bulk_insert(
        sa.table(
            'balances',
            sa.column('id', postgresql.UUID(as_uuid=True)),
            sa.column('merchant_id', postgresql.UUID(as_uuid=True)),
            sa.column('total_amount', sa.Numeric(18, 2)),
            sa.column('reserved_amount', sa.Numeric(18, 2)),
        ),
        [
            {
                'id': uuid.UUID('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'),
                'merchant_id': merchant_1_id,
                'total_amount': Decimal('1000.00'),
                'reserved_amount': Decimal('0.00'),
            },
            {
                'id': uuid.UUID('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'),
                'merchant_id': merchant_2_id,
                'total_amount': Decimal('500.00'),
                'reserved_amount': Decimal('0.00'),
            },
        ],
    )


def downgrade() -> None:
    op.drop_table('payments')
    op.drop_table('balances')
    op.drop_table('merchants')
    op.execute('DROP TYPE IF EXISTS payment_status')