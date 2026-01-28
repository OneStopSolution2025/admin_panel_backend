"""add phone to users

Revision ID: 001_add_phone_to_users
Revises: 
Create Date: 2026-01-28 09:17:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_add_phone_to_users'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add phone column to users table"""
    # Add phone column as nullable (won't break existing data)
    op.add_column('users', sa.Column('phone', sa.String(length=20), nullable=True))
    
    # Optional: Add index on phone for faster lookups if needed
    # op.create_index(op.f('ix_users_phone'), 'users', ['phone'], unique=False)


def downgrade() -> None:
    """Remove phone column from users table"""
    # Optional: Drop index if it was created
    # op.drop_index(op.f('ix_users_phone'), table_name='users')
    
    # Drop the phone column
    op.drop_column('users', 'phone')
