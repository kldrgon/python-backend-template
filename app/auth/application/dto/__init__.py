from pydantic import BaseModel, Field

from app.auth.application.dto.miniapp_auth import MiniappBindResponseDTO


class RefreshTokenResponseDTO(BaseModel):
    access_token: str = Field(...,description="Access Token")
