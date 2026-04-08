from pydantic import BaseModel, Field


class GetUserListResponseDTO(BaseModel):
    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="Email")
    nickname: str = Field(..., description="Nickname")


class CreateUserRequestDTO(BaseModel):
    email: str = Field(..., description="Email")
    password1: str = Field(..., description="Password1")
    password2: str = Field(..., description="Password2")
    nickname: str = Field(..., description="Nickname")

class CreateUserResponseData(BaseModel):
    userId: str = Field(..., description="UserId")
    email: str = Field(..., description="Email")
    nickname: str = Field(..., description="Nickname")
    roles: list[str] = Field(default_factory=list, description="User roles")
    message: str = Field(..., description="User Message")

class CreateUserResponseDTO(BaseModel):
    code: int = Field(..., description="Response Code")
    data: CreateUserResponseData = Field(..., description="Data")
    message: str = Field(..., description="Response Message")


class LoginResponseDTO(BaseModel):
    access_token: str = Field(..., description="Token")
    refresh_token: str = Field(..., description="Refresh token")
    avatar: str | None = Field(None, description="User avatar URL")
    user_id: str | None = Field(None, description="User ID")
    email: str | None = Field(None, description="Email")
    nickname: str | None = Field(None, description="Nickname")
    roles: list[str] = Field(default_factory=list, description="Roles")
