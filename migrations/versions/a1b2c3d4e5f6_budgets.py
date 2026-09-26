"""budgets table and progress calculation

Revision ID: a1b2c3d4e5f6
Revises: f9b3e7d1a5c2
Create Date: 2026-09-05 07:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = 'a1b2c3d4e5f6'
down_revision = 'f9b3e7d1a5c2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'budgets',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'user_id',
            UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'category_id',
            UUID(as_uuid=True),
            sa.ForeignKey('categories.id', ondelete='RESTRICT'),
            nullable=False,
        ),
        sa.Column('year_month', sa.String(7), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=True),
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
            "char_length(btrim(year_month)) = 7 AND year_month ~ '^[0-9]{4}-[0-9]{2}$'",
            name='ck_budgets_year_month_format',
        ),
    )
    op.create_index('ix_budgets_user_id', 'budgets', ['user_id'])
    op.create_index('ix_budgets_year_month', 'budgets', ['year_month'])


def downgrade():
    op.drop_index('ix_budgets_year_month', table_name='budgets')
    op.drop_index('ix_budgets_user_id', table_name='budgets')
    op.drop_table('budgets')
