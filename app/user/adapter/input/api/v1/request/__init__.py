from pydantic import BaseModel, Field
from app.user.domain.vo.user_role import UserRole


class LoginRequest(BaseModel):
    email: str = Field(..., description="Email")
    password: str = Field(..., description="Password")


class CreateUserRequest(BaseModel):
    email: str = Field(..., description="Email")
    nickname: str = Field(..., description="Nickname")
    password: str = Field(..., description="Password")
    confirmPassword: str | None = Field(None, description="ConfirmPassword")
    role: UserRole = Field(..., description="UserRole")
    agreed: bool | None = Field(None, description="AgreedProtocol")
    captcha_code: str = Field(..., description="验证码")


class AddressRequest(BaseModel):
    province: str = Field(..., description="Province")
    city: str = Field(..., description="City")
    district: str = Field(..., description="District")


class UpdateUserProfileRequest(BaseModel):
    nickname: str | None = Field(None, description="Nickname")
    org_name: str | None = Field(None, description="Organization name (university)")
    bio: str | None = Field(None, description="Bio")
    location: AddressRequest | None = Field(None, description="Address [province, city, district]")
