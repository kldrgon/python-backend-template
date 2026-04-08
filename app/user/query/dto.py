from pydantic import BaseModel, ConfigDict


class UserListItemDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    email: str
    nickname: str


class UserDetailDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    email: str
    nickname: str
    roles: list[str]
    is_admin: bool | None = None


class Pagination(BaseModel):
    limit: int
    prev: int | None = None


