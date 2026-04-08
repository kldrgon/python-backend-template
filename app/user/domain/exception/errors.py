class InvalidEmailError(Exception):
    def __init__(self, *, email: str):
        self.email = email
        super().__init__(f"invalid email: {email}")


class WeakPasswordError(Exception):
    def __init__(self):
        super().__init__("weak password")


class EmptyNicknameError(Exception):
    def __init__(self):
        super().__init__("empty nickname")


class DisabledUserCannotBeAssignedRolesError(Exception):
    def __init__(self, *, user_id: str):
        self.user_id = user_id
        super().__init__(f"disabled user cannot be assigned roles: user_id={user_id}")


class DuplicateEmailOrNicknameError(Exception):
    def __init__(self, *, email: str | None, nickname: str | None):
        self.email = email
        self.nickname = nickname
        super().__init__("duplicate email or nickname")


