"""Add listing identity uniqueness and supporting indexes.

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-17 11:00:00.000000
"""
from alembic import op


revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        'uq_listings_source_listing',
        'listings',
        ['source_id', 'source_listing_id'],
    )
    op.create_index('ix_listings_source_listing_id', 'listings', ['source_id', 'source_listing_id'])
    op.create_index('ix_listings_last_seen_at', 'listings', ['last_seen_at'])


def downgrade() -> None:
    op.drop_index('ix_listings_last_seen_at', table_name='listings')
    op.drop_index('ix_listings_source_listing_id', table_name='listings')
    op.drop_constraint('uq_listings_source_listing', 'listings', type_='unique')
