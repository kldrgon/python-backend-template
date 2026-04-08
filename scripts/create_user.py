#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import getpass
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pami_event_framework import Transactional

from app.user.domain.command import CreateUserCommand
from app.user.domain.entity.linked_account import LinkedAccount
from app.user.domain.vo.user_role import UserRole

DEFAULT_OAUTH_PROVIDER = "wechat_miniapp"


@dataclass(slots=True)
class UserCreationInput:
    email: str
    nickname: str
    password: str
    role: UserRole
    phone: str | None = None
    openid: str | None = None
    unionid: str | None = None
    provider: str | None = None
    agreed: bool = True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="创建用户辅助脚本")
    parser.add_argument("--email", help="用户邮箱")
    parser.add_argument("--nickname", "--name", dest="nickname", help="用户昵称")
    parser.add_argument("--password", help="登录密码")
    parser.add_argument("--password-confirm", dest="password_confirm", help="确认密码")
    parser.add_argument(
        "--role",
        choices=[role.value for role in UserRole],
        help="单个角色，只支持 teacher 或 student",
    )
    parser.add_argument("--phone", help="手机号，可选")
    parser.add_argument("--openid", help="微信 openid，可选")
    parser.add_argument("--unionid", help="微信 unionid，可选")
    parser.add_argument(
        "--provider",
        help=f"第三方账号 provider，仅在传入 openid 时生效；未指定时默认 {DEFAULT_OAUTH_PROVIDER}",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="即使参数已足够，也继续交互询问可选字段",
    )
    parser.add_argument(
        "--no-input",
        action="store_true",
        help="禁止交互输入，缺少必填参数时直接报错",
    )
    parser.add_argument(
        "--agreed",
        dest="agreed",
        action="store_true",
        default=True,
        help="是否同意协议，默认 true",
    )
    parser.add_argument(
        "--no-agreed",
        dest="agreed",
        action="store_false",
        help="标记为未同意协议",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def normalize_role(raw: str) -> UserRole:
    value = str(raw).strip().lower()
    if not value:
        raise ValueError("role 不能为空")
    try:
        return UserRole(value)
    except ValueError as exc:
        raise ValueError("role 仅支持 teacher 或 student") from exc


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _prompt_text(
    prompt: str,
    *,
    input_fn: Callable[[str], str],
    default: str | None = None,
    required: bool = False,
) -> str:
    while True:
        suffix = f" [{default}]" if default else ""
        value = input_fn(f"{prompt}{suffix}: ").strip()
        if value:
            return value
        if default is not None:
            return default
        if not required:
            return ""
        print(f"{prompt} 不能为空，请重新输入。")


def _prompt_password(password_fn: Callable[[str], str]) -> str:
    while True:
        password = password_fn("请输入密码: ").strip()
        if not password:
            print("密码不能为空，请重新输入。")
            continue
        confirm = password_fn("请再次输入密码: ").strip()
        if password != confirm:
            print("两次输入的密码不一致，请重新输入。")
            continue
        return password


def collect_user_input(
    args: argparse.Namespace,
    *,
    input_fn: Callable[[str], str] = input,
    password_fn: Callable[[str], str] = getpass.getpass,
) -> UserCreationInput:
    allow_prompt = not bool(args.no_input)

    email = _clean_optional(args.email)
    nickname = _clean_optional(args.nickname)
    role_value = _clean_optional(args.role)
    password = _clean_optional(args.password)
    password_confirm = _clean_optional(args.password_confirm)
    phone = _clean_optional(args.phone)
    openid = _clean_optional(args.openid)
    unionid = _clean_optional(args.unionid)
    provider = _clean_optional(args.provider)

    if email is None:
        if not allow_prompt:
            raise ValueError("缺少必填参数 email")
        email = _prompt_text("请输入邮箱", input_fn=input_fn, required=True)

    if nickname is None:
        if not allow_prompt:
            raise ValueError("缺少必填参数 nickname")
        nickname = _prompt_text("请输入昵称", input_fn=input_fn, required=True)

    if role_value is None:
        if not allow_prompt:
            raise ValueError("缺少必填参数 role")
        role_value = _prompt_text(
            "请输入角色（teacher/student）",
            input_fn=input_fn,
            required=True,
        )

    if password is None:
        if not allow_prompt:
            raise ValueError("缺少必填参数 password")
        password = _prompt_password(password_fn)
    elif password_confirm is not None and password != password_confirm:
        raise ValueError("password 与 password-confirm 不一致")

    if args.interactive and allow_prompt:
        if phone is None:
            phone = _clean_optional(_prompt_text("请输入手机号（可留空）", input_fn=input_fn))
        if openid is None:
            openid = _clean_optional(_prompt_text("请输入 openid（可留空）", input_fn=input_fn))
        if unionid is None:
            unionid = _clean_optional(_prompt_text("请输入 unionid（可留空）", input_fn=input_fn))

    if unionid and not openid:
        raise ValueError("提供 unionid 时必须同时提供 openid")
    if provider and not openid:
        raise ValueError("提供 provider 时必须同时提供 openid")
    if openid and provider is None:
        provider = DEFAULT_OAUTH_PROVIDER

    return UserCreationInput(
        email=email,
        nickname=nickname,
        password=password,
        role=normalize_role(role_value),
        phone=phone,
        openid=openid,
        unionid=unionid,
        provider=provider,
        agreed=bool(args.agreed),
    )


@Transactional()
async def attach_optional_bindings(
    *,
    repository,
    user_id: str,
    phone: str | None,
    openid: str | None,
    unionid: str | None,
    provider: str | None,
) -> None:
    if phone:
        existing_phone_user = await repository.get_user_by_phone(phone=phone)
        if existing_phone_user and existing_phone_user.user_id != user_id:
            raise ValueError("手机号已被其他用户占用")

    if openid:
        if not provider:
            raise ValueError("绑定 openid 时缺少 provider")
        existing_oauth_user = await repository.get_user_by_linked_account(
            provider=provider,
            provider_account_id=openid,
        )
        if existing_oauth_user and existing_oauth_user.user_id != user_id:
            raise ValueError("openid 已绑定到其他用户")

    user = await repository.get_user_by_id(user_id=user_id)
    if user is None:
        raise ValueError("创建后的用户不存在，无法补充资料")

    if phone:
        user.set_phone(phone=phone)

    if openid:
        raw_data = {"union_id": unionid} if unionid else None
        user.link_account(
            account=LinkedAccount(
                provider=provider,
                provider_account_id=openid,
                raw_data=raw_data,
            )
        )

    await repository.save(user=user)


async def create_user_from_input(
    *,
    user_usecase,
    user_repository,
    payload: UserCreationInput,
):
    provider = payload.provider
    if payload.openid and provider is None:
        provider = DEFAULT_OAUTH_PROVIDER

    command = CreateUserCommand(
        email=payload.email,
        nickname=payload.nickname,
        password=payload.password,
        confirmPassword=payload.password,
        role=payload.role,
        agreed=payload.agreed,
    )
    user = await user_usecase.create_user(command=command)

    if payload.phone or payload.openid:
        await attach_optional_bindings(
            repository=user_repository,
            user_id=user.user_id,
            phone=payload.phone,
            openid=payload.openid,
            unionid=payload.unionid,
            provider=provider,
        )

    return user


async def main_async(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = collect_user_input(args)

    from app.bootstrap_web import get_web_bootstrap, shutdown_web_bootstrap
    from app.container import Container
    from pami_event_framework.persistence import set_session_context, reset_session_context

    container = Container()
    await get_web_bootstrap()
    container.init_resources()
    context_token = set_session_context(f"script-create-user-{uuid.uuid4().hex}")

    try:
        user_usecase = container.user_container.user_command_service()
        user_repository = container.user_container.user_sqlalchemy_repo()

        user = await create_user_from_input(
            user_usecase=user_usecase,
            user_repository=user_repository,
            payload=payload,
        )
    finally:
        reset_session_context(context_token)
        container.shutdown_resources()
        await shutdown_web_bootstrap()

    print("用户创建成功")
    print(f"user_id: {user.user_id}")
    print(f"email: {user.email}")
    print(f"nickname: {user.nickname}")
    print(f"role: {payload.role.value}")
    if payload.phone:
        print(f"phone: {payload.phone}")
    if payload.openid:
        print(f"openid: {payload.openid}")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return asyncio.run(main_async(argv))
    except KeyboardInterrupt:
        print("已取消")
        return 130
    except Exception as exc:
        print(f"创建用户失败: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
