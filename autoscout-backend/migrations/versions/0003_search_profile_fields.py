"""Add search profile criteria and location fields.

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-14 17:30:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add all new columns to search_profiles
    op.add_column('search_profiles', sa.Column('make', sa.String(100), nullable=True))
    op.add_column('search_profiles', sa.Column('model', sa.String(100), nullable=True))
    op.add_column('search_profiles', sa.Column('year_min', sa.Integer(), nullable=True))
    op.add_column('search_profiles', sa.Column('year_max', sa.Integer(), nullable=True))
    op.add_column('search_profiles', sa.Column('price_min', sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column('search_profiles', sa.Column('price_max', sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column('search_profiles', sa.Column('currency', sa.String(3), nullable=False, server_default='EUR'))
    op.add_column('search_profiles', sa.Column('mileage_max', sa.Integer(), nullable=True))
    op.add_column('search_profiles', sa.Column('location_lat', sa.Float(), nullable=True))
    op.add_column('search_profiles', sa.Column('location_lng', sa.Float(), nullable=True))
    op.add_column('search_profiles', sa.Column('radius_km', sa.Integer(), nullable=True))
    op.add_column('search_profiles', sa.Column('body_type', sa.String(50), nullable=True))
    op.add_column('search_profiles', sa.Column('transmission', sa.String(50), nullable=True))
    op.add_column('search_profiles', sa.Column('fuel_type', sa.String(50), nullable=True))
    op.add_column('search_profiles', sa.Column('free_text_criteria', sa.Text(), nullable=True))
    op.add_column('search_profiles', sa.Column('delivery_time_local', sa.Integer(), nullable=False, server_default='8'))
    op.add_column('search_profiles', sa.Column('timezone', sa.String(64), nullable=False, server_default='Europe/Tirane'))


def downgrade() -> None:
    op.drop_column('search_profiles', 'timezone')
    op.drop_column('search_profiles', 'delivery_time_local')
    op.drop_column('search_profiles', 'free_text_criteria')
    op.drop_column('search_profiles', 'fuel_type')
    op.drop_column('search_profiles', 'transmission')
    op.drop_column('search_profiles', 'body_type')
    op.drop_column('search_profiles', 'radius_km')
    op.drop_column('search_profiles', 'location_lng')
    op.drop_column('search_profiles', 'location_lat')
    op.drop_column('search_profiles', 'mileage_max')
    op.drop_column('search_profiles', 'currency')
    op.drop_column('search_profiles', 'price_max')
    op.drop_column('search_profiles', 'price_min')
    op.drop_column('search_profiles', 'year_max')
    op.drop_column('search_profiles', 'year_min')
    op.drop_column('search_profiles', 'model')
    op.drop_column('search_profiles', 'make')
