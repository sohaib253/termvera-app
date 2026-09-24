from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    InvalidTokenError,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.membership import Membership, MembershipRole
from app.models.organization import Organization
from app.models.user import User
from app.schemas.auth import RegisterRequest, TokenResponse


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


async def register(db: AsyncSession, data: RegisterRequest) -> TokenResponse:
    existing = await db.scalar(select(User).where(User.email == data.email))
    if existing is not None:
        raise EmailAlreadyRegisteredError(data.email)

    organization = Organization(
        name=data.organization_name,
        industry=data.industry,
        country=data.country,
    )
    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
    )
    db.add_all([organization, user])
    await db.flush()

    membership = Membership(
        organization_id=organization.id,
        user_id=user.id,
        role=MembershipRole.OWNER,
    )
    db.add(membership)
    await db.commit()

    return _issue_tokens(user_id=user.id, organization_id=organization.id)


async def login(db: AsyncSession, email: str, password: str) -> TokenResponse:
    user = await db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError()
    if not user.is_active:
        raise InvalidCredentialsError()

    membership = await db.scalar(
        select(Membership).where(Membership.user_id == user.id)
    )
    if membership is None:
        raise InvalidCredentialsError()

    return _issue_tokens(user_id=user.id, organization_id=membership.organization_id)


def _issue_tokens(*, user_id: str, organization_id: str) -> TokenResponse:
    return TokenResponse(
        access_token=create_token(
            subject=user_id, organization_id=organization_id, token_type="access"
        ),
        refresh_token=create_token(
            subject=user_id, organization_id=organization_id, token_type="refresh"
        ),
    )


async def refresh(db: AsyncSession, refresh_token: str) -> TokenResponse:
    try:
        payload = decode_token(refresh_token, expected_type="refresh")
    except InvalidTokenError as exc:
        raise InvalidCredentialsError() from exc

    user_id = payload.get("sub")
    organization_id = payload.get("org")
    user = await db.get(User, user_id) if user_id else None
    if user is None or not user.is_active or not organization_id:
        raise InvalidCredentialsError()

    return _issue_tokens(user_id=user.id, organization_id=organization_id)
