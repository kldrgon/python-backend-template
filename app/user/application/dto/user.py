from pydantic import BaseModel, ConfigDict


class UserReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    email: str
    nickname: str
    roles: list[str]
    is_admin: bool = False

    # 头像：avatar_blob_id 是内部存储ID，avatar_url 是对外暴露的下载链接
    avatar_blob_id: str | None = None
    avatar_url: str | None = None

    # 档案
    university: str | None = None   # 对应 org_name
    bio: str | None = None
    location: dict | None = None    # {"province": "", "city": "", "district": ""}

    linked_accounts: list[dict] | None = None
