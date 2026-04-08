from core.response.rersponse_exception import ApiResponseException


# ==================== 登录相关错误 (4100-4119) ====================
class UserNotFoundException(ApiResponseException):
    """用户不存在"""
    def __init__(self):
        super().__init__(
            status_code=404,  # 标准 HTTP 状态码
            detail="用户不存在",
            code=4101  # 业务错误码保留在响应体中
        )


class PasswordDoesNotMatchException(ApiResponseException):
    """密码错误"""
    def __init__(self):
        super().__init__(
            status_code=401,  # 标准 HTTP 状态码 (Unauthorized)
            detail="密码错误",
            code=4102  # 业务错误码保留在响应体中
        )


# ==================== 注册相关错误 (4120-4139) ====================
class DuplicateEmailOrNicknameException(ApiResponseException):
    """邮箱或昵称已存在"""
    def __init__(self):
        super().__init__(
            status_code=409,  # 标准 HTTP 状态码 (Conflict)
            detail="邮箱或昵称已被注册",
            code=4121  # 业务错误码保留在响应体中
        )


class PasswordConfirmNotMatchException(ApiResponseException):
    """两次密码不一致"""
    def __init__(self):
        super().__init__(
            status_code=400,  # 标准 HTTP 状态码
            detail="两次输入的密码不一致",
            code=4122  # 业务错误码保留在响应体中
        )


class AgreementRequiredException(ApiResponseException):
    """未同意用户协议"""
    def __init__(self):
        super().__init__(
            status_code=400,  # 标准 HTTP 状态码
            detail="请先同意用户协议",
            code=4123  # 业务错误码保留在响应体中
        )


# ==================== 验证码相关错误 (4140-4149) ====================
class CaptchaInvalidException(ApiResponseException):
    """验证码错误或已过期"""
    def __init__(self):
        super().__init__(
            status_code=400,  # 标准 HTTP 状态码
            detail="验证码错误或已过期",
            code=4141  # 业务错误码保留在响应体中
        )


class CaptchaSendTooFrequentException(ApiResponseException):
    """验证码发送过于频繁"""
    def __init__(self):
        super().__init__(
            status_code=429,  # 标准 HTTP 状态码 (Too Many Requests)
            detail="验证码发送过于频繁，请稍后再试",
            code=4142  # 业务错误码保留在响应体中
        )
