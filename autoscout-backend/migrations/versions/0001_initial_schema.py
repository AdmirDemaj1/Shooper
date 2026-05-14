"""Initial schema: users, search_profiles, listings, matches

Revision ID: 0001
Revises:
Create Date: 2026-05-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('phone_number', sa.String(20), nullable=False),
        sa.Column('whatsapp_opt_in', sa.Boolean(), nullable=True),
        sa.Column('country', sa.String(2), nullable=True),
        sa.Column('locale', sa.String(10), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone_number')
    )
    op.create_index('ix_users_phone_number', 'users', ['phone_number'], unique=True)

    op.create_table(
        'search_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_search_profiles_user_id', 'search_profiles', ['user_id'])

    op.create_table(
        'listings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_id', sa.String(50), nullable=False),
        sa.Column('source_listing_id', sa.String(255), nullable=False),
        sa.Column('source_url', sa.String(500), nullable=True),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('description', sa.String(2000), nullable=True),
        sa.Column('make', sa.String(100), nullable=True),
        sa.Column('model', sa.String(100), nullable=True),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('mileage', sa.Integer(), nullable=True),
        sa.Column('price', sa.String(50), nullable=True),
        sa.Column('currency', sa.String(3), nullable=True),
        sa.Column('location_text', sa.String(255), nullable=True),
        sa.Column('seller_name', sa.String(255), nullable=True),
        sa.Column('raw_payload', sa.String(), nullable=True),
        sa.Column('dedup_hash', sa.String(255), nullable=True),
        sa.Column('first_seen_at', sa.DateTime(), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_listings_source_id', 'listings', ['source_id'])
    op.create_index('ix_listings_dedup_hash', 'listings', ['dedup_hash'])

    op.create_table(
        'matches',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('search_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('listing_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('relevance_score', sa.Integer(), nullable=True),
        sa.Column('llm_reasoning', sa.String(1000), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('delivery_status', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_matches_search_profile_id', 'matches', ['search_profile_id'])
    op.create_index('ix_matches_listing_id', 'matches', ['listing_id'])


def downgrade() -> None:
    op.drop_index('ix_matches_listing_id', table_name='matches')
    op.drop_index('ix_matches_search_profile_id', table_name='matches')
    op.drop_table('matches')
    op.drop_index('ix_listings_dedup_hash', table_name='listings')
    op.drop_index('ix_listings_source_id', table_name='listings')
    op.drop_table('listings')
    op.drop_index('ix_search_profiles_user_id', table_name='search_profiles')
    op.drop_table('search_profiles')
    op.drop_index('ix_users_phone_number', table_name='users')
    op.drop_table('users')
