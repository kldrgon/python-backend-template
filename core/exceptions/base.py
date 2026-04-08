class CustomException(Exception):
    code = 400
    error_code = "BAD_GATEWAY"
    message = "BAD GATEWAY"

    def __init__(self, message=None):
        if message:
            self.message = message


class RepositoryIntegrityError(Exception):
    """持久化层唯一约束冲突等数据完整性错误"""
    pass
