"""Add comment column to rentals table

Revision ID: add_comment_to_rentals
Revises: 
Create Date: 2024-03-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_comment_to_rentals'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add comment column to rentals table
    op.add_column('rentals', sa.Column('comment', sa.String(), nullable=True))


def downgrade():
    # Remove comment column from rentals table
    op.drop_column('rentals', 'comment') 