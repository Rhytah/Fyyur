"""empty message

Revision ID: f729977a5e8b
Revises: 14d393b5e326
Create Date: 2019-10-30 11:07:31.756388

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f729977a5e8b'
down_revision = '14d393b5e326'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('Venue', sa.Column('deleted', sa.Boolean(), nullable=True))
    op.add_column('Venue', sa.Column('seeking_description', sa.Text(), nullable=True))
    op.add_column('Venue', sa.Column('seeking_talent', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('Venue', 'seeking_talent')
    op.drop_column('Venue', 'seeking_description')
    op.drop_column('Venue', 'deleted')
    # ### end Alembic commands ###
