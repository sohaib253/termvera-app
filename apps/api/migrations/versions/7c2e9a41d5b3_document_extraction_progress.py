"""document extraction progress

Revision ID: 7c2e9a41d5b3
Revises: 634826f7813b
Create Date: 2026-09-25 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c2e9a41d5b3'
down_revision: Union[str, None] = '634826f7813b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents", sa.Column("extraction_pages_done", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("documents", "extraction_pages_done")
