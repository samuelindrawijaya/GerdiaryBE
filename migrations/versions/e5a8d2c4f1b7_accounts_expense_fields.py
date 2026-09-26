"""accounts table and food_entries expense columns

Revision ID: e5a8d2c4f1b7
Revises: b7e4c1a2f9d3
Create Date: 2026-09-05 05:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = 'e5a8d2c4f1b7'
down_revision = 'b7e4c1a2f9d3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'accounts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'user_id',
            UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('emoji', sa.String(32), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "char_length(btrim(name)) > 0",
            name='ck_accounts_name_not_blank',
        ),
    )
    op.create_index('ix_accounts_user_id', 'accounts', ['user_id'])

    op.add_column(
        'food_entries',
        sa.Column('amount', sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        'food_entries',
        sa.Column(
            'account_id',
            UUID(as_uuid=True),
            sa.ForeignKey('accounts.id', ondelete='RESTRICT'),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        'ck_food_entries_amount_non_negative',
        'food_entries',
        'amount IS NULL OR amount >= 0',
    )


def downgrade():
    op.drop_constraint(
        'ck_food_entries_amount_non_negative', 'food_entries', type_='check'
    )
    op.drop_column('food_entries', 'account_id')
    op.drop_column('food_entries', 'amount')
    op.drop_index('ix_accounts_user_id', table_name='accounts')
    op.drop_table('accounts')
