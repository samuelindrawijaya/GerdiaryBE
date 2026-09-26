"""user_trigger_preferences table

Replace semantics use hard delete: trigger preferences are replaceable
configuration, not journal history, unlike soft-deleted food entries
(docs/BE-ONBOARDING-TRIGGER-CONTRACT.md).

Revision ID: c4d5e6f7a8b9
Revises: a1b2c3d4e5f6
Create Date: 2026-09-06 09:00:00

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = 'c4d5e6f7a8b9'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_trigger_preferences',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'user_id',
            UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('trigger_key', sa.String(50), nullable=True),
        sa.Column('label', sa.String(100), nullable=False),
        sa.Column('emoji', sa.String(32), nullable=True),
        sa.Column('reaction_level', sa.String(20), nullable=False),
        sa.Column(
            'is_custom',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
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
        sa.CheckConstraint(
            "reaction_level IN ('strong','mild','tolerated')",
            name='ck_user_trigger_preferences_reaction_level',
        ),
        sa.CheckConstraint(
            "(is_custom = true AND trigger_key IS NULL) OR "
            "(is_custom = false AND trigger_key IS NOT NULL)",
            name='ck_user_trigger_preferences_custom_key',
        ),
    )
    op.create_index(
        'ix_user_trigger_preferences_user_id',
        'user_trigger_preferences',
        ['user_id'],
    )
    op.create_index(
        'uq_user_trigger_preferences_user_key',
        'user_trigger_preferences',
        ['user_id', 'trigger_key'],
        unique=True,
        postgresql_where=sa.text('trigger_key IS NOT NULL'),
    )


def downgrade():
    op.drop_index(
        'uq_user_trigger_preferences_user_key',
        table_name='user_trigger_preferences',
    )
    op.drop_index(
        'ix_user_trigger_preferences_user_id',
        table_name='user_trigger_preferences',
    )
    op.drop_table('user_trigger_preferences')
