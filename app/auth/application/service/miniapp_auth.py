from uuid import uuid4

from app.auth.application.dto.miniapp_auth import MiniappBindResponseDTO
from app.auth.application.port.user_account_port import UserAccountPort
from app.auth.domain.command.miniapp_bind import MiniappBindCommand
from app.auth.domain.usecase.miniapp_auth import MiniappAuthUseCase
from pami_event_framework import Transactional
from core.helpers.token import TokenHelper
from core.config import config
from core.response.rersponse_exception import ApiResponseException


WECHAT_MINIAPP_PROVIDER = "wechat_miniapp"


class MiniappAuthCommandService(MiniappAuthUseCase):
    def __init__(self, *, user_account_port: UserAccountPort):
        self.user_account_port = user_account_port

    @Transactional()
    async def bind_and_login(self, *, command: MiniappBindCommand) -> MiniappBindResponseDTO:
        """
        小程序绑定并登录
        1. 优先按 openid 找用户
        2. 再按手机号找用户
        3. 没找到就创建
        4. 绑定手机号和 openid
        """
        openid = command.openid
        phone = command.phone
        unionid = command.unionid
        session_meta = command.session_meta or {}

        user_by_unionid, user_by_openid = await self._find_user_by_wechat_identity(
            openid=str(openid),
            unionid=str(unionid) if unionid else None,
        )
        user = user_by_unionid or user_by_openid
        found_by_oauth = user_by_openid is not None

        # 2) 再按手机号找用户
        if user is None:
            user = await self.user_account_port.find_by_phone(phone=str(phone))

        # 3) 没找到就创建
        if user is None:
            email = f"wx_{openid}@miniapp.local"
            nickname = f"wx_{str(openid)[:12]}"
            password = uuid4().hex
            user = await self.user_account_port.create_user(
                email=email, password=password, nickname=nickname, role="student"
            )
        else:
            owner_by_phone = await self.user_account_port.find_by_phone(phone=str(phone))
            if owner_by_phone is not None and owner_by_phone.user_id != user.user_id:
                raise ApiResponseException(status_code=409, detail="该手机号已被其它账号占用")

            if not found_by_oauth:
                existing_uid = await self.user_account_port.get_oauth_binding_uid(
                    user_id=user.user_id, provider=WECHAT_MINIAPP_PROVIDER
                )
                if existing_uid and existing_uid != str(openid):
                    raise ApiResponseException(status_code=409, detail="该手机号已绑定其它微信号")

        # 手机号绑定 + openid 绑定（同一次 load-mutate-save，避免覆盖）
        await self.user_account_port.bind_phone_and_link_oauth(
            user_id=user.user_id,
            phone=str(phone),
            provider=WECHAT_MINIAPP_PROVIDER,
            external_uid=str(openid),
            union_id=str(unionid) if unionid else None,
            meta={"session": session_meta},
            link_oauth=not found_by_oauth,
        )

        return self._build_response(user)

    async def login_by_openid(self, *, openid: str) -> MiniappBindResponseDTO:
        """按 openid 登录（需已完成 bind）。"""
        user = await self.user_account_port.find_by_oauth(
            provider=WECHAT_MINIAPP_PROVIDER, external_uid=openid
        )
        if user is None:
            raise ApiResponseException(status_code=404, detail="未绑定手机号，请先调用 /auth/v1/miniapp/bind")
        return self._build_response(user)

    @Transactional()
    async def login_or_register(
        self,
        *,
        openid: str,
        unionid: str | None = None,
        session_meta: dict | None = None,
    ) -> MiniappBindResponseDTO:
        user_by_unionid, user_by_openid = await self._find_user_by_wechat_identity(
            openid=openid,
            unionid=unionid,
        )
        user = user_by_unionid or user_by_openid

        if user is None:
            email = f"wx_{openid}@miniapp.local"
            nickname = f"wx_{str(openid)[:12]}"
            password = uuid4().hex
            user = await self.user_account_port.create_user(
                email=email, password=password, nickname=nickname, role="student"
            )

        await self.user_account_port.bind_phone_and_link_oauth(
            user_id=user.user_id,
            phone=None,
            provider=WECHAT_MINIAPP_PROVIDER,
            external_uid=openid,
            union_id=unionid,
            meta={"session": session_meta or {}},
            link_oauth=user_by_openid is None,
        )
        return self._build_response(user)

    async def _find_user_by_wechat_identity(
        self,
        *,
        openid: str,
        unionid: str | None,
    ):
        user_by_unionid = None
        if unionid:
            user_by_unionid = await self.user_account_port.find_by_unionid(
                provider=WECHAT_MINIAPP_PROVIDER,
                union_id=unionid,
            )

        user_by_openid = await self.user_account_port.find_by_oauth(
            provider=WECHAT_MINIAPP_PROVIDER,
            external_uid=openid,
        )

        if (
            user_by_unionid is not None
            and user_by_openid is not None
            and user_by_unionid.user_id != user_by_openid.user_id
        ):
            raise ApiResponseException(status_code=409, detail="该微信账号已关联其它用户")

        return user_by_unionid, user_by_openid

    def _build_response(self, user) -> MiniappBindResponseDTO:
        normalized_roles = [str(item).upper() for item in (user.roles or []) if item]
        primary_role = normalized_roles[0] if normalized_roles else None
        return MiniappBindResponseDTO(
            user_id=user.user_id,
            nickname=user.nickname,
            email=user.email,
            avatar=user.avatar,
            roles=list(user.roles or []),
            access_token=TokenHelper.encode(
                payload={
                    "user_id": user.user_id,
                    "sub": "access",
                    "role": primary_role,
                    "roles": normalized_roles,
                },
                expire_period=config.jwt.access_token_expire_seconds,
            ),
            refresh_token=TokenHelper.encode(
                payload={
                    "user_id": user.user_id,
                    "sub": "refresh",
                    "role": primary_role,
                    "roles": normalized_roles,
                },
                expire_period=config.jwt.refresh_token_expire_seconds,
            ),
        )
