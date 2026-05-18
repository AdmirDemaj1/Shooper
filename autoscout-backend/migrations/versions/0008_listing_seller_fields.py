"""Add seller fields to listings table for platform-native listings.

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-18 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('listings', sa.Column('seller_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True))
    op.add_column('listings', sa.Column('status', sa.String(20), nullable=False, server_default='active'))
    op.add_column('listings', sa.Column('photo_urls', JSONB, nullable=False, server_default='[]'))
    op.add_column('listings', sa.Column('contact_phone', sa.String(30), nullable=True))
    op.add_column('listings', sa.Column('views_count', sa.Integer, nullable=False, server_default='0'))
    op.create_index('ix_listings_seller_user_id', 'listings', ['seller_user_id'])


def downgrade() -> None:
    op.drop_index('ix_listings_seller_user_id', 'listings')
    op.drop_column('listings', 'views_count')
    op.drop_column('listings', 'contact_phone')
    op.drop_column('listings', 'photo_urls')
    op.drop_column('listings', 'status')
    op.drop_column('listings', 'seller_user_id')
