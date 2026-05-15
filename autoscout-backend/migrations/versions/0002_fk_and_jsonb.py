"""Add FK constraints and change raw_payload to JSONB

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-14 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add FK constraint: search_profiles.user_id -> users.id
    op.create_foreign_key(
        'fk_search_profiles_user_id',
        'search_profiles', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )

    # Add FK constraint: matches.search_profile_id -> search_profiles.id
    op.create_foreign_key(
        'fk_matches_search_profile_id',
        'matches', 'search_profiles',
        ['search_profile_id'], ['id'],
        ondelete='CASCADE'
    )

    # Add FK constraint: matches.listing_id -> listings.id
    op.create_foreign_key(
        'fk_matches_listing_id',
        'matches', 'listings',
        ['listing_id'], ['id'],
        ondelete='CASCADE'
    )

    # Convert raw_payload from String to JSONB
    op.execute('ALTER TABLE listings ALTER COLUMN raw_payload TYPE jsonb USING COALESCE(raw_payload::jsonb, NULL)')


def downgrade() -> None:
    # Convert raw_payload back from JSONB to String
    op.execute('ALTER TABLE listings ALTER COLUMN raw_payload TYPE text USING raw_payload::text')

    # Drop FK constraints
    op.drop_constraint('fk_matches_listing_id', 'matches', type_='foreignkey')
    op.drop_constraint('fk_matches_search_profile_id', 'matches', type_='foreignkey')
    op.drop_constraint('fk_search_profiles_user_id', 'search_profiles', type_='foreignkey')
