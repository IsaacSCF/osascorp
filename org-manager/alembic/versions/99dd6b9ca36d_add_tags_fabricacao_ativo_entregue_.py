"""add_tags_fabricacao_ativo_entregue_fields

Revision ID: 99dd6b9ca36d
Revises: 192dc89f51af
Create Date: 2025-10-16 16:51:35.116884

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '99dd6b9ca36d'
down_revision: Union[str, None] = '192dc89f51af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns
    op.add_column('orgs', sa.Column('tags_fabricacao', sa.Text(), nullable=True))
    op.add_column('orgs', sa.Column('ativo', sa.Boolean(), nullable=False, server_default='1'))
    op.add_column('orgs', sa.Column('entregue', sa.Boolean(), nullable=False, server_default='0'))
    # Remove old fabricacao column
    op.drop_column('orgs', 'fabricacao')


def downgrade() -> None:
    pass
