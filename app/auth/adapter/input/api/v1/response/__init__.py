from pydantic import BaseModel, Field

class RefreshTokenData(BaseModel):
    access_token: str = Field(..., description="Access Token")

class RefreshTokenResponse(BaseModel):
    code: int = Field(..., description="Response Code")
    data: RefreshTokenData = Field(..., description="Data")
    message: str = Field(..., description="Response Message")
