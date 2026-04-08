import structlog
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, Request
from typing import Annotated

from app.container import Container

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

from app.user.adapter.input.api.v1.request import CreateUserRequest, LoginRequest, UpdateUserProfileRequest
from app.user.adapter.output.domain_service.avatar_url_adapter import get_avatar_url_adapter
from app.user.application.port.avatar_url_port import AvatarUrlPort
from app.user.application.port.avatar_status_port import AvatarStatusPort
from app.user.application.dto import CreateUserResponseDTO, GetUserListResponseDTO, LoginResponseDTO
from app.user.application.dto.user import UserReadDTO
from app.user.query.service import UserQueryService
from app.user.domain.command import CreateUserCommand, UserRolesAssignCommand, UpdateUserProfileCommand
from app.user.domain.command.user import UserGetByIdCommand
from app.user.domain.usecase.user import UserUseCase
from app.user.domain.vo.location import Address
from core.fastapi.dependencies import IsAdmin, PermissionDependency
from core.response import ApiResponse, PagedResult
from core.response.rersponse_exception import ApiResponseException

user_router = APIRouter(tags=["user"])


async def _resolve_avatar_url(
    blob_id: str | None,
    avatar_url_port: AvatarUrlPort | None,
    request: Request,
) -> str | None:
    if not blob_id:
        return None
    if avatar_url_port is None:
        avatar_url_port = get_avatar_url_adapter(request)
    return await avatar_url_port.get_avatar_url(blob_id=blob_id)


async def _dto_with_avatar(
    dto: UserReadDTO,
    request: Request,
    avatar_url_port: AvatarUrlPort | None,
) -> UserReadDTO:
    dto.avatar_url = await _resolve_avatar_url(dto.avatar_blob_id, avatar_url_port, request)
    return dto


@user_router.post(
    "/send-captcha",
    response_model=ApiResponse[dict],
)
@inject
async def send_captcha(
    email: str = Query(..., description="邮箱地址"),
    usecase: UserUseCase = Depends(Provide[Container.user_container.user_command_service]),
):
    """发送注册验证码到邮箱"""
    try:
        email = email.strip()
        logger.info("captcha_send_requested", email=email)
        expires_in = await usecase.send_registration_captcha(email=email)
        return ApiResponse.success(
            data={"email": email, "expires_in": expires_in},
            message="验证码已发送，请查收邮件",
        )
    except ApiResponseException:
        raise
    except Exception as e:
        logger.error("captcha_send_error", email=email, error=str(e), exc_info=True)
        raise ApiResponseException(code=500, detail=f"发送验证码失败: {str(e)}")


@user_router.get(
    "/",
    response_model=ApiResponse[PagedResult[GetUserListResponseDTO]],
)
@inject
async def get_user_list(
    limit: int = Query(10, description="Limit"),
    offset: int = Query(0, description="Offset"),
    svc: UserQueryService = Depends(Provide[Container.user_container.user_query_service]),
):
    eff_limit = min(max(limit, 1), 100)
    eff_offset = max(offset, 0)
    items, total = await svc.list_users(limit=eff_limit, offset=eff_offset)
    dto_items = [GetUserListResponseDTO(user_id=i.user_id, email=i.email, nickname=i.nickname) for i in items]
    return ApiResponse.success(data=PagedResult(items=dto_items, total=total, limit=eff_limit, offset=eff_offset))


@user_router.post(
    "/register",
    response_model=CreateUserResponseDTO,
)
@inject
async def create_user(
    request: CreateUserRequest,
    usecase: UserUseCase = Depends(Provide[Container.user_container.user_command_service]),
):
    try:
        if request.email:
            request.email = request.email.strip()
        if request.nickname:
            request.nickname = request.nickname.strip()

        logger.info("user_register_requested", email=request.email)
        command = CreateUserCommand(
            email=request.email,
            nickname=request.nickname,
            password=request.password,
            confirmPassword=request.confirmPassword if request.confirmPassword else request.password,
            role=request.role,
            agreed=request.agreed if request.agreed is not None else True,
        )
        user = await usecase.register_with_captcha(command=command, captcha_code=request.captcha_code)

        logger.info("user_created", email=request.email, user_id=user.user_id)
        return {
            "code": 200,
            "data": {
                "userId": user.user_id,
                "email": user.email,
                "nickname": user.nickname,
                "roles": list(user.roles or []),
                "message": "注册成功，请登录!",
            },
            "message": "注册成功",
        }
    except ApiResponseException:
        raise
    except Exception as e:
        logger.error("user_register_error", email=request.email, error=str(e), exc_info=True)
        raise ApiResponseException(code=500, detail=f"注册失败: {str(e)}")


@user_router.post(
    "/login",
    response_model=ApiResponse[dict],
)
@inject
async def login(
    body: LoginRequest,
    http_request: Request,
    usecase: UserUseCase = Depends(Provide[Container.user_container.user_command_service]),
    avatar_url_port: Annotated[AvatarUrlPort, Depends(get_avatar_url_adapter)] = None,
):
    if body.email:
        body.email = body.email.strip()
    token = await usecase.login(email=body.email, password=body.password)
    avatar_url = await _resolve_avatar_url(token.avatar, avatar_url_port, http_request)
    data = {
        "user": {
            "id": token.user_id,
            "email": token.email,
            "nickname": token.nickname,
            "roles": list(getattr(token, "roles", []) or []),
            "avatar": avatar_url,
            "avatar_blob_id": token.avatar,
        },
        "access_token": token.access_token,
        "refresh_token": token.refresh_token,
    }
    return ApiResponse.success(data=data, message="登录成功")


@user_router.patch(
    "/roles",
    response_model=ApiResponse[bool],
)
@inject
async def roles_assign(
    request: UserRolesAssignCommand,
    usecase: UserUseCase = Depends(Provide[Container.user_container.user_command_service]),
):
    result = await usecase.assign_roles(command=request)
    return ApiResponse.success(data=result)


@user_router.get(
    "/profile",
    response_model=ApiResponse[UserReadDTO],
)
@inject
async def get_profile(
    request: Request,
    user_id: str = Query(..., description="User ID"),
    usecase: UserUseCase = Depends(Provide[Container.user_container.user_command_service]),
    avatar_url_port: Annotated[AvatarUrlPort, Depends(get_avatar_url_adapter)] = None,
):
    dto = await usecase.get_by_user_id(command=UserGetByIdCommand(user_id=user_id))
    dto = await _dto_with_avatar(dto, request, avatar_url_port)
    return ApiResponse.success(data=dto)


@user_router.patch(
    "/{user_id}",
    response_model=ApiResponse[UserReadDTO],
)
@inject
async def update_user_profile(
    user_id: str,
    body: UpdateUserProfileRequest,
    http_request: Request,
    usecase: UserUseCase = Depends(Provide[Container.user_container.user_command_service]),
    avatar_url_port: Annotated[AvatarUrlPort, Depends(get_avatar_url_adapter)] = None,
):
    location = None
    if body.location:
        location = Address(
            province=body.location.province,
            city=body.location.city,
            district=body.location.district,
        )

    command = UpdateUserProfileCommand(
        user_id=user_id,
        nickname=body.nickname,
        org_name=body.org_name,
        bio=body.bio,
        location=location,
    )
    await usecase.update_profile(command=command)

    dto = await usecase.get_by_user_id(command=UserGetByIdCommand(user_id=user_id))
    dto = await _dto_with_avatar(dto, http_request, avatar_url_port)
    return ApiResponse.success(data=dto)


@user_router.get(
    "/{user_id}/avatar/status",
    response_model=ApiResponse[dict],
    summary="查询头像处理状态",
)
@inject
async def get_avatar_status(
    user_id: str,
    avatar_status_port: AvatarStatusPort = Depends(Provide[Container.user_container.avatar_status_port]),
):
    """
    轮询头像上传处理状态。

    - PENDING：处理中（或尚未上传）
    - APPROVED：头像已成功绑定
    - REJECTED：处理失败
    """
    status = await avatar_status_port.get_status(user_id=user_id)
    return ApiResponse.success(data={"status": status})
