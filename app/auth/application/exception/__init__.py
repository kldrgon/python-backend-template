__all__ = [
    "InvalidRefreshTokenException",
]


class InvalidRefreshTokenException(Exception):
    """Refresh Token 无效（需要重新登录）"""
    def __init__(self):
        super().__init__("Refresh Token 无效，请重新登录")
