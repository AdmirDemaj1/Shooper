"""Add transmission, fuel_type, body_type to listings table.

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-17 13:00:00.000000
"""
import sqlalchemy as sa
from alembic import op

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('listings', sa.Column('transmission', sa.String(50), nullable=True))
    op.add_column('listings', sa.Column('fuel_type', sa.String(50), nullable=True))
    op.add_column('listings', sa.Column('body_type', sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column('listings', 'body_type')
    op.drop_column('listings', 'fuel_type')
    op.drop_column('listings', 'transmission')
