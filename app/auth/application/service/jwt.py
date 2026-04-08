from app.auth.application.dto import RefreshTokenResponseDTO
from app.auth.application.exception import InvalidRefreshTokenException
from app.auth.domain.usecase.jwt import JwtUseCase
from core.exceptions import DecodeTokenException, ExpiredTokenException
from core.helpers.token import TokenHelper


class JwtCommandService(JwtUseCase):
    """JWT命令服务类，实现JWT相关的业务逻辑"""
    
    async def verify_token(self, token: str) -> None:
        try:
            # 尝试解码token，如果成功说明token有效
            TokenHelper.decode(token=token)
        except (DecodeTokenException, ExpiredTokenException):
            # 捕获解码异常和过期异常，统一抛出业务异常
            raise DecodeTokenException

    async def create_refresh_token(
        self,
        token: str,
    ) -> RefreshTokenResponseDTO:
        try:
            # 解码 refresh token，获取用户信息
            decoded_created_token = TokenHelper.decode(token=token)
            
            user_id = decoded_created_token.get("user_id")
            role = decoded_created_token.get("role")
            roles = decoded_created_token.get("roles")
            
            # 检查是否为 refresh token
            sub = decoded_created_token.get("sub")
            if sub != "refresh":
                raise InvalidRefreshTokenException
            
            # 生成新的 access token
            return RefreshTokenResponseDTO(
                access_token=TokenHelper.encode(
                    payload={
                        "user_id": user_id,
                        "sub": "access",
                        "role": role,
                        "roles": roles if isinstance(roles, list) else [],
                    }
                )
            )
        except (DecodeTokenException, ExpiredTokenException):
            # Refresh token 无效或过期
            raise InvalidRefreshTokenException