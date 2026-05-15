"""Create llm_calls table for cost telemetry.

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-15 14:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'llm_calls',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('endpoint', sa.String(100), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=False),
        sa.Column('output_tokens', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_llm_calls_user_id', 'llm_calls', ['user_id'])
    op.create_index('ix_llm_calls_created_at', 'llm_calls', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_llm_calls_created_at', table_name='llm_calls')
    op.drop_index('ix_llm_calls_user_id', table_name='llm_calls')
    op.drop_table('llm_calls')
