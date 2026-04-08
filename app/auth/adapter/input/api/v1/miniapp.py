import asyncio
import structlog

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends
from core.helpers.token import TokenHelper

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)
from app.auth.application.service.miniapp_auth import MiniappAuthCommandService
from app.auth.domain.command.miniapp_bind import MiniappBindCommand
from app.auth.adapter.input.api.v1.request import (
    MiniappBindRequest,
    MiniappAutoLoginRequest,
    MiniappReLoginRequest,
)
from app.container import Container
from core.config import config
from core.helpers.wechat_miniapp import (
    WechatMiniappApiError,
    decrypt_phone_number,
    wechat_access_token,
    wechat_get_user_phone_number,
    wechat_jscode2session,
)
from core.response.api_response import ApiResponse
from core.response.rersponse_exception import ApiResponseException


router = APIRouter()


@router.post(
    "/miniapp/bind",
    response_model=ApiResponse[dict],
    summary="小程序首次绑定并登录（openid + 手机号）",
)
@inject
async def miniapp_bind_and_login(
    body: MiniappBindRequest,
    miniapp_auth_service: MiniappAuthCommandService = Depends(Provide[Container.miniapp_auth_command_service]),
):
    try:
        appid = config.wx_miniapp.appid
        secret = config.wx_miniapp.secret
    except Exception as e:
        raise ApiResponseException(status_code=500, detail="缺少小程序配置：WX_MINIAPP_APPID/WX_MINIAPP_SECRET") from e

    last_exc: Exception | None = None
    for attempt in range(1, 4):
        try:
            sess = await wechat_jscode2session(appid=appid, secret=secret, js_code=body.login_code)
            openid = sess.get("openid")
            unionid = sess.get("unionid")
            session_key = sess.get("session_key")
            if not openid:
                raise ApiResponseException(status_code=400, detail="微信登录失败：缺少 openid")

            phone: str | None = None
            if body.phone_code:
                access_token = await wechat_access_token(appid=appid, secret=secret)
                phone_payload = await wechat_get_user_phone_number(access_token=access_token, phone_code=body.phone_code)
                phone_info = (phone_payload or {}).get("phone_info") or {}
                phone = phone_info.get("purePhoneNumber") or phone_info.get("phoneNumber")
            else:
                if not session_key:
                    raise ApiResponseException(status_code=400, detail="微信登录失败：缺少 session_key（无法解密手机号）")
                phone_info = decrypt_phone_number(
                    session_key=str(session_key),
                    encrypted_data=str(body.encrypted_data),
                    iv=str(body.iv),
                )
                phone = phone_info.get("purePhoneNumber") or phone_info.get("phoneNumber")

            if not phone:
                raise ApiResponseException(status_code=400, detail="获取手机号失败")
            break
        except (WechatMiniappApiError, ValueError, ApiResponseException) as e:
            last_exc = e
            if attempt < 3:
                await asyncio.sleep(0.5 * attempt)
                continue
            if isinstance(e, ApiResponseException):
                raise
            raise ApiResponseException(status_code=400, detail=f"微信接口失败：{str(e)}") from e
    else:
        raise ApiResponseException(status_code=400, detail=f"微信接口失败：{str(last_exc)}")

    result = await miniapp_auth_service.bind_and_login(
        command=MiniappBindCommand(
            openid=str(openid),
            phone=str(phone),
            unionid=str(unionid) if unionid else None,
            session_meta=sess,
        )
    )

    return ApiResponse.success(
        data={
            "access_token": result.access_token,
            "refresh_token": result.refresh_token,
            "user_id": result.user_id,
            "nickname": result.nickname,
            "email": result.email,
            "avatar": result.avatar,
            "roles": result.roles,
        }
    )


@router.post(
    "/miniapp/relogin",
    response_model=ApiResponse[dict],
    summary="小程序重新登录（已绑定用户，无需手机号验证）",
)
@inject
async def miniapp_relogin(
    body: MiniappReLoginRequest,
    miniapp_auth_service: MiniappAuthCommandService = Depends(Provide[Container.miniapp_auth_command_service]),
):
    try:
        appid = config.wx_miniapp.appid
        secret = config.wx_miniapp.secret
    except Exception as e:
        raise ApiResponseException(status_code=500, detail="缺少小程序配置：WX_MINIAPP_APPID/WX_MINIAPP_SECRET") from e

    try:
        sess = await wechat_jscode2session(appid=appid, secret=secret, js_code=body.login_code)
        openid = sess.get("openid")
        if not openid:
            raise ApiResponseException(status_code=400, detail="微信登录失败：缺少 openid")
    except WechatMiniappApiError as e:
        raise ApiResponseException(status_code=400, detail=f"微信接口失败：{str(e)}") from e

    logger.info("miniapp_relogin", openid=openid)
    result = await miniapp_auth_service.login_by_openid(openid=str(openid))

    return ApiResponse.success(
        data={
            "access_token": result.access_token,
            "refresh_token": result.refresh_token,
            "user_id": result.user_id,
            "nickname": result.nickname,
            "email": result.email,
            "avatar": result.avatar,
            "roles": result.roles,
        }
    )


@router.post(
    "/miniapp/login",
    response_model=ApiResponse[dict],
    summary="小程序静默登录（无需手机号，不存在则自动创建）",
)
@inject
async def miniapp_auto_login(
    body: MiniappAutoLoginRequest,
    miniapp_auth_service: MiniappAuthCommandService = Depends(Provide[Container.miniapp_auth_command_service]),
):
    try:
        appid = config.wx_miniapp.appid
        secret = config.wx_miniapp.secret
    except Exception as e:
        raise ApiResponseException(status_code=500, detail="缺少小程序配置：WX_MINIAPP_APPID/WX_MINIAPP_SECRET") from e

    try:
        sess = await wechat_jscode2session(appid=appid, secret=secret, js_code=body.login_code)
        openid = sess.get("openid")
        unionid = sess.get("unionid")
        if not openid:
            raise ApiResponseException(status_code=400, detail="微信登录失败：缺少 openid")
    except WechatMiniappApiError as e:
        raise ApiResponseException(status_code=400, detail=f"微信接口失败：{str(e)}") from e

    logger.info("miniapp_auto_login", openid=openid, unionid=unionid)
    result = await miniapp_auth_service.login_or_register(
        openid=str(openid),
        unionid=str(unionid) if unionid else None,
        session_meta=sess,
    )

    return ApiResponse.success(
        data={
            "access_token": result.access_token,
            "refresh_token": result.refresh_token,
            "user_id": result.user_id,
            "nickname": result.nickname,
            "email": result.email,
            "avatar": result.avatar,
            "roles": result.roles,
        }
    )
