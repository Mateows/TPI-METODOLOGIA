"""0001_init: establish the migration chain (C-01 has no domain models yet).

Revision ID: 0001_init
"""

from collections.abc import Sequence

revision: str = "0001_init"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
