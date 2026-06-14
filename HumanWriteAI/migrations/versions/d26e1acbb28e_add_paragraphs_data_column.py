"""Add paragraphs_data column to analyses table

Revision ID: d26e1acbb28e
Revises: a601ea16123c
Create Date: 2026-06-14 16:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd26e1acbb28e'
down_revision = 'a601ea16123c'
branch_labels = None
depends_on = None


def upgrade():
    # Add paragraphs_data JSON column to analyses table
    with op.batch_alter_table('analyses', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('paragraphs_data', sa.JSON(), nullable=True)
        )


def downgrade():
    with op.batch_alter_table('analyses', schema=None) as batch_op:
        batch_op.drop_column('paragraphs_data')