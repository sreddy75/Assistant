"""add_azure_devops_endpoints

Revision ID: fc16332f1d23
Revises: 3e624f7236cb
Create Date: 2024-09-18 07:48:12.320310

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'fc16332f1d23'
down_revision: Union[str, None] = '3e624f7236cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table('azure_devops_endpoints',
        sa.Column('id', sa.VARCHAR(), nullable=False),
        sa.Column('path', sa.String(), nullable=False),
        sa.Column('method', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parameters', postgresql.JSONB(), nullable=True),
        sa.Column('response_schema', postgresql.JSONB(), nullable=True),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_azure_devops_endpoints_embedding', 'azure_devops_endpoints', ['embedding'], unique=False, postgresql_using='ivfflat')

def downgrade():
    op.drop_index('idx_azure_devops_endpoints_embedding', table_name='azure_devops_endpoints')
    op.drop_table('azure_devops_endpoints')