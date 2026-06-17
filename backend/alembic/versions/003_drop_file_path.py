"""drop file_path column from books

Revision ID: 003_drop_file_path
Revises: 002_add_file_data
Create Date: 2026-06-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_drop_file_path"
down_revision: Union[str, None] = "002_add_file_data"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("books", "file_path")


def downgrade() -> None:
    op.add_column(
        "books",
        sa.Column("file_path", sa.String(length=500), nullable=False),
    )
