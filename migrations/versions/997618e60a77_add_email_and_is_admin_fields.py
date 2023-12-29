"""Add email and is_admin fields

Revision ID: 997618e60a77
Revises: 
Create Date: 2023-12-20 14:14:31.902160

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '997618e60a77'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email', sa.String(length=250), nullable=True))
        batch_op.add_column(sa.Column('is_admin', sa.Integer(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('is_admin')
        batch_op.drop_column('email')

    # ### end Alembic commands ###