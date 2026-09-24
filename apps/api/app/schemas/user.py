from pydantic import BaseModel, ConfigDict

from app.models.membership import MembershipRole
from app.schemas.organization import OrganizationRead


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str


class MeResponse(BaseModel):
    user: UserRead
    organization: OrganizationRead
    role: MembershipRole
    is_admin: bool
