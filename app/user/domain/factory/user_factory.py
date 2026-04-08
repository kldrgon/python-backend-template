from uuid import uuid4
from app.user.domain.aggregate.user import User


class UserFactory:

    def create_user(
        self,
        *,
        user_id: str | None = None,
        email: str,
        password: str,
        nickname: str,
        role: str,
    ) -> User:
        uid = user_id or uuid4().hex
        return User.create(user_id=uid, email=email, password=password, nickname=nickname, role=role)
