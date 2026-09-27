"""Desktop (single-user, offline) onboarding: no accounts or passwords.

On a customer's own laptop an email/password login is pure friction: the
person at the keyboard has already signed in to Windows, and the data sits
in their Windows profile either way. So the desktop build asks for a name
and company once, and signs its one user in automatically after that, the
way desktop software normally behaves.

These routes exist only in the desktop build (ENVIRONMENT=desktop). The
server there listens on 127.0.0.1 only, and main.py rejects any request
whose Host isn't a loopback name, so a web page can't reach them through
DNS rebinding.
"""

import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import create_token, hash_password
from app.db.session import get_db
from app.models.membership import Membership, MembershipRole
from app.models.organization import Organization
from app.models.user import User
from app.schemas.auth import TokenResponse
from app.services import license as license_service

router = APIRouter(prefix="/api/desktop", tags=["desktop"])

# Stored when the user gives no email; never used to sign in or contact anyone.
_PLACEHOLDER_EMAIL = "owner@desktop.invalid"


class DesktopStatus(BaseModel):
    desktop: bool
    setup_required: bool
    # False during free early access: no trial to mention.
    billing_enabled: bool = True


class DesktopSetup(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    organization_name: str = Field(min_length=1, max_length=255)
    email: EmailStr | None = None
    industry: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)


def _require_desktop() -> None:
    if not get_settings().is_desktop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")


def _tokens(user_id: str, organization_id: str) -> TokenResponse:
    return TokenResponse(
        access_token=create_token(subject=user_id, organization_id=organization_id, token_type="access"),
        refresh_token=create_token(subject=user_id, organization_id=organization_id, token_type="refresh"),
    )


async def _owner(db: AsyncSession) -> Membership | None:
    return await db.scalar(
        select(Membership)
        .where(Membership.role == MembershipRole.OWNER)
        .order_by(Membership.created_at)
        .limit(1)
    )


@router.get("/status", response_model=DesktopStatus)
async def desktop_status(db: AsyncSession = Depends(get_db)) -> DesktopStatus:
    settings = get_settings()
    if not settings.is_desktop:
        return DesktopStatus(
            desktop=False, setup_required=False, billing_enabled=settings.billing_enabled
        )
    return DesktopStatus(
        desktop=True,
        setup_required=await _owner(db) is None,
        billing_enabled=settings.billing_enabled,
    )


@router.post("/setup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def desktop_setup(data: DesktopSetup, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    _require_desktop()
    if (await db.scalar(select(func.count()).select_from(User))) or 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This app is already set up.")

    organization = Organization(
        name=data.organization_name.strip(), industry=data.industry, country=data.country
    )
    user = User(
        email=str(data.email) if data.email else _PLACEHOLDER_EMAIL,
        # Nobody signs in with this; it only satisfies the column. A random
        # value means the account can't be logged into by password at all.
        hashed_password=hash_password(secrets.token_urlsafe(32)),
        full_name=data.full_name.strip(),
    )
    db.add_all([organization, user])
    await db.flush()
    db.add(Membership(organization_id=organization.id, user_id=user.id, role=MembershipRole.OWNER))
    await db.commit()
    # Start the trial clock now, at setup, rather than on first use.
    await license_service.get_or_create_license(db, organization_id=organization.id)
    return _tokens(user.id, organization.id)


@router.post("/session", response_model=TokenResponse)
async def desktop_session(db: AsyncSession = Depends(get_db)) -> TokenResponse:
    _require_desktop()
    owner = await _owner(db)
    if owner is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Set up the app first.")
    return _tokens(owner.user_id, owner.organization_id)
