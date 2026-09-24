from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import InvalidTokenError, decode_token
from app.db.session import get_db
from app.models.membership import Membership, MembershipRole
from app.models.organization import Organization
from app.models.user import User

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


@dataclass
class CurrentPrincipal:
    user: User
    organization: Organization
    role: MembershipRole

    @property
    def is_admin(self) -> bool:
        """Workspace administrator: may manage the plan and delete projects.
        Read from the membership row (re-checked on every request), never
        from a token claim."""
        return self.role in (MembershipRole.OWNER, MembershipRole.ADMIN)


async def get_current_principal(
    token: str | None = Depends(_oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> CurrentPrincipal:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None:
        raise credentials_error

    try:
        payload = decode_token(token, expected_type="access")
    except InvalidTokenError as exc:
        raise credentials_error from exc

    user_id = payload.get("sub")
    organization_id = payload.get("org")
    if not user_id or not organization_id:
        raise credentials_error

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_error

    organization = await db.get(Organization, organization_id)
    if organization is None:
        raise credentials_error

    # Defense in depth: even though the token carries the org id, re-check
    # that the user actually still belongs to it before trusting it as the
    # tenant scope for every downstream query.
    membership = await db.scalar(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.organization_id == organization.id,
        )
    )
    if membership is None:
        raise credentials_error

    return CurrentPrincipal(user=user, organization=organization, role=membership.role)


def require_admin(
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> CurrentPrincipal:
    """Dependency for routes only a workspace owner/admin may call."""
    if not principal.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires a workspace administrator.",
        )
    return principal
