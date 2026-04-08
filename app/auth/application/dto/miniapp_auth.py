from pydantic import BaseModel, Field


class MiniappBindResponseDTO(BaseModel):
    user_id: str = Field(..., description="用户ID")
    nickname: str = Field(..., description="昵称")
    email: str = Field(..., description="邮箱")
    avatar: str | None = Field(None, description="头像")
    roles: list[str] = Field(default_factory=list, description="角色列表")
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
