from pydantic import BaseModel, Field, model_validator


class RefreshTokenRequest(BaseModel):
    token: str = Field(..., description="Token")


class VerifyTokenRequest(BaseModel):
    token: str = Field(..., description="Token")

class MiniappBindRequest(BaseModel):
    login_code: str = Field(..., description="wx.login() 返回的 code")
    phone_code: str | None = Field(None, description="getPhoneNumber 返回的 code（推荐）")
    encrypted_data: str | None = Field(None, description="getPhoneNumber 返回的 encryptedData（旧版）")
    iv: str | None = Field(None, description="getPhoneNumber 返回的 iv（旧版）")

    @model_validator(mode="after")
    def _validate_phone_payload(self):
        if self.phone_code:
            return self
        if self.encrypted_data and self.iv:
            return self
        raise ValueError("首次绑定必须提供 phone_code 或 (encrypted_data + iv)")

class MiniappAutoLoginRequest(BaseModel):
    login_code: str = Field(..., description="wx.login() 返回的 code")

class MiniappReLoginRequest(BaseModel):
    login_code: str = Field(..., description="wx.login() 返回的 code")
