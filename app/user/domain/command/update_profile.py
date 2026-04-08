from pydantic import BaseModel
from app.user.domain.vo.location import Address


class UpdateUserProfileCommand(BaseModel):
    user_id: str
    nickname: str | None = None
    org_name: str | None = None
    bio: str | None = None
    location: Address | None = None
