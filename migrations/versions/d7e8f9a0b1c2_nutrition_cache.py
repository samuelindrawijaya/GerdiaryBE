"""nutrition_cache table

Revision ID: d7e8f9a0b1c2
Revises: c4d5e6f7a8b9
Create Date: 2026-09-07 08:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = 'd7e8f9a0b1c2'
down_revision = 'c4d5e6f7a8b9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'nutrition_cache',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('provider', sa.String(30), nullable=False),
        sa.Column('provider_product_id', sa.String(100), nullable=False),
        sa.Column('barcode', sa.String(14), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('brand', sa.String(255), nullable=True),
        sa.Column('energy_kcal_100g', sa.Numeric(10, 2), nullable=True),
        sa.Column('fat_100g', sa.Numeric(10, 2), nullable=True),
        sa.Column('carbohydrates_100g', sa.Numeric(10, 2), nullable=True),
        sa.Column('sugars_100g', sa.Numeric(10, 2), nullable=True),
        sa.Column('protein_100g', sa.Numeric(10, 2), nullable=True),
        sa.Column('salt_100g', sa.Numeric(10, 2), nullable=True),
        sa.Column(
            'cached_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "provider <> '' AND provider_product_id <> ''",
            name='ck_nutrition_cache_provider_not_blank',
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) > 0",
            name='ck_nutrition_cache_name_not_blank',
        ),
        sa.CheckConstraint(
            "energy_kcal_100g IS NULL OR energy_kcal_100g >= 0",
            name='ck_nutrition_cache_energy_non_negative',
        ),
        sa.CheckConstraint(
            "fat_100g IS NULL OR fat_100g >= 0",
            name='ck_nutrition_cache_fat_non_negative',
        ),
        sa.CheckConstraint(
            "carbohydrates_100g IS NULL OR carbohydrates_100g >= 0",
            name='ck_nutrition_cache_carbs_non_negative',
        ),
        sa.CheckConstraint(
            "sugars_100g IS NULL OR sugars_100g >= 0",
            name='ck_nutrition_cache_sugars_non_negative',
        ),
        sa.CheckConstraint(
            "protein_100g IS NULL OR protein_100g >= 0",
            name='ck_nutrition_cache_protein_non_negative',
        ),
        sa.CheckConstraint(
            "salt_100g IS NULL OR salt_100g >= 0",
            name='ck_nutrition_cache_salt_non_negative',
        ),
    )
    op.create_index('ix_nutrition_cache_barcode', 'nutrition_cache', ['barcode'])
    op.create_index(
        'uq_nutrition_cache_provider_product',
        'nutrition_cache',
        ['provider', 'provider_product_id'],
        unique=True,
    )


def downgrade():
    op.drop_index(
        'uq_nutrition_cache_provider_product',
        table_name='nutrition_cache',
    )
    op.drop_index('ix_nutrition_cache_barcode', table_name='nutrition_cache')
    op.drop_table('nutrition_cache')
