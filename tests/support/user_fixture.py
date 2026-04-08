from uuid import uuid4
from core.db.models.user import UserModel
from core.helpers.password import hash_password


def make_user(
    id: int | None = None,
    *,
    user_id: str | None = None,
    password: str = "password123",
    email: str = "test@example.com",
    nickname: str = "testuser",
    is_admin: bool = False,
) -> UserModel:
    model = UserModel(
        user_id=user_id or uuid4().hex,
        hashed_password=hash_password(password),
        email=email,
        nickname=nickname,
        is_admin=is_admin,
        enabled=True,
    )
    if id is not None:
        model.id = id
    return model
