from core.db.models import UserLinkedAccountModel, UserRoleModel
from core.db.models.user import UserModel
from app.user.domain.aggregate.user import User
from app.user.domain.entity.linked_account import LinkedAccount
from app.user.domain.vo.location import Address


def orm_to_domain(orm: UserModel) -> User:
    roles = sorted([r.role for r in getattr(orm, "roles_rel", [])])

    linked_accounts = [
        LinkedAccount(
            provider=link.provider,
            provider_account_id=link.provider_account_id,
            access_token=link.access_token,
            refresh_token=link.refresh_token,
            expires_at=link.expires_at,
            token_type=link.token_type,
            scope=link.scope,
            id_token=link.id_token,
            raw_data=link.raw_data,
        )
        for link in getattr(orm, "linked_accounts_rel", [])
    ]

    location = None
    if orm.location:
        location = Address(
            province=orm.location.get("province"),
            city=orm.location.get("city"),
            district=orm.location.get("district"),
        )

    return User(
        user_id=orm.user_id,
        email=orm.email,
        hashed_password=orm.hashed_password,
        nickname=orm.nickname,
        phone=getattr(orm, "phone", None),
        is_admin=orm.is_admin,
        enabled=getattr(orm, "enabled", True),
        roles=roles,
        org_name=getattr(orm, "org_name", None),
        bio=getattr(orm, "bio", None),
        avatar=getattr(orm, "avatar", None),
        location=location,
        linked_accounts=linked_accounts,
    )


def domain_to_orm(domain: User, target: UserModel | None = None) -> UserModel:
    orm = target or UserModel()
    orm.user_id = getattr(orm, "user_id", None) or domain.user_id
    orm.email = domain.email
    orm.hashed_password = domain.hashed_password
    orm.nickname = domain.nickname
    orm.phone = domain.phone
    orm.is_admin = domain.is_admin
    orm.enabled = domain.enabled
    orm.org_name = domain.org_name
    orm.bio = domain.bio
    orm.avatar = domain.avatar

    if domain.location:
        orm.location = {
            "province": domain.location.province,
            "city": domain.location.city,
            "district": domain.location.district,
        }
    else:
        orm.location = None

    existing_roles = {r.role for r in getattr(orm, "roles_rel", [])}
    desired_roles = set(domain.roles)
    for role in sorted(desired_roles - existing_roles):
        if not hasattr(orm, "roles_rel"):
            orm.roles_rel = []  # type: ignore[attr-defined]
        orm.roles_rel.append(UserRoleModel(role=role))  # type: ignore[attr-defined]
    if hasattr(orm, "roles_rel"):
        orm.roles_rel = [r for r in orm.roles_rel if r.role in desired_roles]  # type: ignore[attr-defined]

    if not hasattr(orm, "linked_accounts_rel"):
        orm.linked_accounts_rel = []  # type: ignore[attr-defined]

    existing = {
        (link.provider, link.provider_account_id): link
        for link in orm.linked_accounts_rel  # type: ignore[attr-defined]
    }
    desired_keys = set()
    for account in domain.linked_accounts:
        key = (account.provider, account.provider_account_id)
        desired_keys.add(key)
        if key in existing:
            link = existing[key]
            link.access_token = account.access_token
            link.refresh_token = account.refresh_token
            link.expires_at = account.expires_at
            link.token_type = account.token_type
            link.scope = account.scope
            link.id_token = account.id_token
            link.raw_data = account.raw_data
        else:
            orm.linked_accounts_rel.append(  # type: ignore[attr-defined]
                UserLinkedAccountModel(
                    provider=account.provider,
                    provider_account_id=account.provider_account_id,
                    access_token=account.access_token,
                    refresh_token=account.refresh_token,
                    expires_at=account.expires_at,
                    token_type=account.token_type,
                    scope=account.scope,
                    id_token=account.id_token,
                    raw_data=account.raw_data,
                )
            )

    orm.linked_accounts_rel = [  # type: ignore[attr-defined]
        link for link in orm.linked_accounts_rel  # type: ignore[attr-defined]
        if (link.provider, link.provider_account_id) in desired_keys
    ]

    return orm
