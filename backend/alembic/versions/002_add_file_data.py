"""add file_data column to books

Revision ID: 002_add_file_data
Revises: 001
Create Date: 2026-06-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_add_file_data"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("books", sa.Column("file_data", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    op.drop_column("books", "file_data")
