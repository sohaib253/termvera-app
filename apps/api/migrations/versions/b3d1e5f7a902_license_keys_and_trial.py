"""license keys and trial

Revision ID: b3d1e5f7a902
Revises: 7c2e9a41d5b3
Create Date: 2026-09-26 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3d1e5f7a902'
down_revision: Union[str, None] = '7c2e9a41d5b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Runs on desktop (SQLite) installs during upgrade, so batch mode.
def upgrade() -> None:
    with op.batch_alter_table("license_accounts") as batch:
        batch.add_column(sa.Column("license_key", sa.Text(), nullable=True))
        batch.add_column(sa.Column("license_id", sa.String(length=40), nullable=True))
        batch.add_column(sa.Column("licensee", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("trial_started_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("clock_high_water", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("license_accounts") as batch:
        batch.drop_column("clock_high_water")
        batch.drop_column("trial_started_at")
        batch.drop_column("licensee")
        batch.drop_column("license_id")
        batch.drop_column("license_key")
