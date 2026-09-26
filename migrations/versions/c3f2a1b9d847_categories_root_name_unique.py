"""categories root name unique partial index

Revision ID: c3f2a1b9d847
Revises: dcabfe49bcbb
Create Date: 2026-09-05 01:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = 'c3f2a1b9d847'
down_revision = 'dcabfe49bcbb'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        'uq_categories_root_user_name',
        'categories',
        ['user_id', 'name'],
        unique=True,
        postgresql_where=sa.text('parent_id IS NULL'),
    )


def downgrade():
    op.drop_index('uq_categories_root_user_name', table_name='categories')
