class DecodeTokenException(Exception):
    """Token 无效或解码失败"""
    def __init__(self):
        super().__init__("Token 无效或已过期")


class ExpiredTokenException(Exception):
    """Token 已过期"""
    def __init__(self):
        super().__init__("Token 已过期")

