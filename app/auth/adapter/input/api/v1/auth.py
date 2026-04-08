from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Header

from app.auth.application.dto import RefreshTokenResponseDTO
from app.auth.domain.usecase.jwt import JwtUseCase
from app.container import Container
from core.response.api_response import ApiResponse
from core.response.rersponse_exception import ApiResponseException

auth_router = APIRouter()


@auth_router.post(
    "/refresh-token",
    response_model=ApiResponse[RefreshTokenResponseDTO],
)
@inject
async def refresh_token(
    authorization: str = Header(..., description="Bearer token"),
    usecase: JwtUseCase = Depends(Provide[Container.jwt_command_service]),
):
    """
    刷新访问令牌
    从 Authorization 头获取 refresh token: Bearer <refresh_token>
    """
    # 解析 Authorization 头
    if not authorization:
        raise ApiResponseException(
            code=4001,
            detail="缺少 Authorization 请求头",
        )

    try:
        scheme, credentials = authorization.split(" ")
        if scheme.lower() != "bearer":
            raise ApiResponseException(
                code=4002,
                detail="Authorization 格式错误",
            )
    except ValueError:
        raise ApiResponseException(
            code=4002,
            detail="Authorization 格式错误",
        )

    if not credentials:
        raise ApiResponseException(
            code=4002,
            detail="Token 不能为空",
        )

    # 使用 refresh token 生成新的 access token
    refresh_token_dto: RefreshTokenResponseDTO = await usecase.create_refresh_token(token=credentials)

    return ApiResponse.success(
        data=refresh_token_dto,
        message="Token 刷新成功"
    )


@auth_router.post(
    "/verify",
    response_model=ApiResponse[bool],
)
@inject
async def verify_token(
    authorization: str = Header(..., description="Bearer token"),
    usecase: JwtUseCase = Depends(Provide[Container.jwt_command_service]),
):
    """
    验证令牌
    从 Authorization 头获取 token: Bearer <access_token>
    """
    if not authorization:
        raise ApiResponseException(
            code=4001,
            detail="缺少 Authorization 请求头",
        )

    try:
        scheme, credentials = authorization.split(" ")
        if scheme.lower() != "bearer":
            raise ApiResponseException(
                code=4002,
                detail="Authorization 格式错误",
            )
    except ValueError:
        raise ApiResponseException(
            code=4002,
            detail="Authorization 格式错误",
        )

    if not credentials:
        raise ApiResponseException(
            code=4002,
            detail="Token 不能为空",
        )
    
    # 验证 token
    await usecase.verify_token(token=credentials)
    
    return ApiResponse.success(
        data=True,
        message="Token 验证成功"
    )
