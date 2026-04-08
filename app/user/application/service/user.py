from app.user.domain.repository.user import UserRepository
from app.user.application.dto import LoginResponseDTO
from app.user.application.dto.user import UserReadDTO
from app.user.application.exception import (
    DuplicateEmailOrNicknameException,
    PasswordDoesNotMatchException,
    PasswordConfirmNotMatchException,
    UserNotFoundException,
    AgreementRequiredException,
    CaptchaInvalidException,
    CaptchaSendTooFrequentException,
)
from app.user.domain.command.user import UserGetByUsernameCommand, UserGetByIdCommand
from app.user.domain.command import (
    CreateUserCommand,
    UserRolesAssignCommand,
    UpdateUserProfileCommand,
    SetAvatarCommand,
)
from app.user.domain.aggregate.user import User
from app.user.domain.usecase.user import UserUseCase
from app.user.application.port.avatar_status_port import AvatarStatusPort
from app.user.domain.exception import DuplicateEmailOrNicknameError
from core.exceptions import RepositoryIntegrityError
from pami_event_framework import Transactional
from core.helpers.password import verify_password
from core.helpers.token import TokenHelper
from core.helpers.captcha import CaptchaService
from core.helpers.email_sender import EmailSender
from core.response.rersponse_exception import ApiResponseException
from core.config import config
from app.user.domain.factory.user_factory import UserFactory
from app.user.domain.domain_service import UserDomainService


def _user_to_dto(user: User, avatar_url: str | None = None) -> UserReadDTO:
    location = None
    if user.location:
        location = {
            "province": user.location.province,
            "city": user.location.city,
            "district": user.location.district,
        }
    linked_accounts = [
        {
            "provider": a.provider,
            "provider_account_id": a.provider_account_id,
        }
        for a in user.linked_accounts
    ]
    return UserReadDTO(
        user_id=user.user_id,
        email=user.email,
        nickname=user.nickname,
        roles=user.roles,
        is_admin=user.is_admin,
        avatar_blob_id=user.avatar,
        avatar_url=avatar_url,
        university=user.org_name,
        bio=user.bio,
        location=location,
        linked_accounts=linked_accounts or None,
    )


class UserCommandService(UserUseCase):
    def __init__(
        self,
        *,
        repository: UserRepository,
        user_factory: UserFactory,
        user_domain_service: UserDomainService | None = None,
        avatar_status_port: AvatarStatusPort | None = None,
    ):
        self.repository = repository
        self.user_factory = user_factory
        self.user_domain_service = user_domain_service
        self.avatar_status_port = avatar_status_port

    # ── UserUseCase ──────────────────────────────────

    @Transactional()
    async def create_user(self, *, command: CreateUserCommand) -> User:
        if command.password != command.confirmPassword:
            raise PasswordConfirmNotMatchException

        if command.agreed is False:
            raise AgreementRequiredException

        if self.user_domain_service is not None:
            try:
                await self.user_domain_service.ensure_user_can_be_created(
                    email=command.email, nickname=command.nickname
                )
            except DuplicateEmailOrNicknameError:
                raise DuplicateEmailOrNicknameException

        user = self.user_factory.create_user(
            email=command.email,
            password=command.password,
            nickname=command.nickname,
            role=command.role,
        )
        try:
            await self.repository.save(user=user)
        except RepositoryIntegrityError:
            raise DuplicateEmailOrNicknameException
        return user

    async def is_admin(self, *, user_id: str) -> bool:
        user = await self.repository.get_user_by_id(user_id=user_id)
        if not user:
            return False
        return user.is_admin

    @Transactional()
    async def assign_roles(self, *, command: UserRolesAssignCommand) -> bool:
        user = await self.repository.get_user_by_id(user_id=command.user_id)
        if user is None:
            raise UserNotFoundException
        user.assign_roles(command.roles)
        await self.repository.save(user=user)
        return True

    @Transactional()
    async def update_profile(self, *, command: UpdateUserProfileCommand) -> User:
        user = await self.repository.get_user_by_id(user_id=command.user_id)
        if not user:
            raise UserNotFoundException
        user.update_profile(
            nickname=command.nickname,
            org_name=command.org_name,
            bio=command.bio,
            location=command.location,
        )
        await self.repository.save(user=user)
        return user

    @Transactional()
    async def set_avatar(self, *, command: SetAvatarCommand) -> User:
        user = await self.repository.get_user_by_id(user_id=command.user_id)
        if not user:
            raise UserNotFoundException
        user.set_avatar(avatar=command.avatar)
        await self.repository.save(user=user)
        return user

    # ── 查询 ─────────────────────────────────────────

    async def login(self, *, email: str, password: str) -> LoginResponseDTO:
        user = await self.repository.get_user_by_email_or_nickname(email=email, nickname=email)
        if not user:
            raise UserNotFoundException
        if not verify_password(password, user.hashed_password):
            raise PasswordDoesNotMatchException
        normalized_roles = [str(item).upper() for item in (user.roles or []) if item]
        primary_role = normalized_roles[0] if normalized_roles else None
        return LoginResponseDTO(
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
            avatar=user.avatar,
            user_id=user.user_id,
            email=user.email,
            nickname=user.nickname,
            roles=list(user.roles or []),
        )

    async def get_by_user_id(self, *, command: UserGetByIdCommand) -> UserReadDTO:
        user = await self.repository.get_user_by_id(user_id=command.user_id)
        if not user:
            raise UserNotFoundException
        return _user_to_dto(user)

    async def get_by_username(self, *, command: UserGetByUsernameCommand) -> UserReadDTO:
        user = await self.repository.get_user_by_email_or_nickname(nickname=command.username)
        if not user:
            raise UserNotFoundException
        return _user_to_dto(user)

    async def get_user_list(self, *, limit: int, prev: int | None = None) -> list[UserReadDTO]:
        users = await self.repository.get_users(limit=limit, prev=prev)
        return [_user_to_dto(u) for u in users]

    async def send_registration_captcha(self, *, email: str) -> int:
        remaining_time = await CaptchaService.get_remaining_time(email)
        if remaining_time and remaining_time > 240:
            raise CaptchaSendTooFrequentException
        captcha_code = CaptchaService.generate_code()
        success = await CaptchaService.store_code(email, captcha_code)
        if not success:
            raise ApiResponseException(code=500, detail="验证码存储失败，请稍后重试")
        await EmailSender.send_captcha_email(email, captcha_code)
        return CaptchaService.CAPTCHA_EXPIRE_TIME

    @Transactional()
    async def register_with_captcha(self, *, command: CreateUserCommand, captcha_code: str) -> User:
        is_valid = await CaptchaService.verify_code(command.email, captcha_code, delete=False)
        if not is_valid:
            raise CaptchaInvalidException
        user = await self.create_user(command=command)
        await CaptchaService.delete_code(command.email)
        return user
