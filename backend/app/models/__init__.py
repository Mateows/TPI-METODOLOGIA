<<<<<<< Updated upstream
=======
"""Domain models package.

Importing this package registers every model on ``Base.metadata`` so Alembic
(and the app) sees the full schema from a single import point.
"""

from __future__ import annotations

from app.models.clinic import Clinic
from app.models.box import BOX_STATUSES, Box
from app.models.refresh_token import RefreshToken
from app.models.user import USER_ROLES, User

__all__ = ["BOX_STATUSES", "Box", "Clinic", "RefreshToken", "USER_ROLES", "User"]
>>>>>>> Stashed changes
