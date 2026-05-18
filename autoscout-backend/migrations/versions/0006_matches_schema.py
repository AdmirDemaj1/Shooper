"""Upgrade matches table schema for Sprint 4.

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-17 12:00:00.000000
"""
import sqlalchemy as sa
from alembic import op

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # New columns on matches
    op.add_column('matches', sa.Column('score_source', sa.String(20), nullable=True, server_default='llm'))
    op.add_column('matches', sa.Column('summary', sa.Text, nullable=True))
    op.add_column('matches', sa.Column('selected_for_delivery', sa.Boolean, nullable=False, server_default='false'))
    op.add_column('matches', sa.Column('delivery_channel', sa.String(50), nullable=True))
    op.add_column('matches', sa.Column('user_action', sa.String(50), nullable=True))
    op.add_column('matches', sa.Column('updated_at', sa.DateTime, nullable=True))

    # Widen llm_reasoning from String(1000) to Text (in-place, safe)
    op.alter_column('matches', 'llm_reasoning', type_=sa.Text, existing_nullable=True)

    # Uniqueness: one match per (profile, listing)
    op.create_unique_constraint(
        'uq_matches_profile_listing',
        'matches',
        ['search_profile_id', 'listing_id'],
    )

    # Indexes for history queries
    op.create_index('ix_matches_profile_delivered_at', 'matches', ['search_profile_id', 'delivered_at'])
    op.create_index('ix_matches_profile_created_at', 'matches', ['search_profile_id', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_matches_profile_created_at', table_name='matches')
    op.drop_index('ix_matches_profile_delivered_at', table_name='matches')
    op.drop_constraint('uq_matches_profile_listing', 'matches', type_='unique')
    op.drop_column('matches', 'updated_at')
    op.drop_column('matches', 'user_action')
    op.drop_column('matches', 'delivery_channel')
    op.drop_column('matches', 'selected_for_delivery')
    op.drop_column('matches', 'summary')
    op.drop_column('matches', 'score_source')
    op.alter_column('matches', 'llm_reasoning', type_=sa.String(1000), existing_nullable=True)
