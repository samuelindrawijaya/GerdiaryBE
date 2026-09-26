"""favorite_foods table

Revision ID: b7e4c1a2f9d3
Revises: c3f2a1b9d847
Create Date: 2026-09-05 03:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = 'b7e4c1a2f9d3'
down_revision = 'c3f2a1b9d847'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'favorite_foods',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'user_id',
            UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('food_name', sa.String(255), nullable=False),
        sa.Column('emoji', sa.String(32), nullable=True),
        sa.Column('brand', sa.String(255), nullable=True),
        sa.Column('portion', sa.Numeric(8, 2), nullable=True),
        sa.Column('portion_unit', sa.String(20), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
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
            "portion_unit IS NULL OR portion_unit IN ('g','ml','cup','pcs','slice','bowl','pack')",
            name='ck_favorite_foods_portion_unit',
        ),
    )
    op.create_index(
        'ix_favorite_foods_user_id',
        'favorite_foods',
        ['user_id'],
    )


def downgrade():
    op.drop_index('ix_favorite_foods_user_id', table_name='favorite_foods')
    op.drop_table('favorite_foods')
