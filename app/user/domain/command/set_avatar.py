from pydantic import BaseModel


class SetAvatarCommand(BaseModel):
    """设置用户头像命令"""
    user_id: str
    avatar: str  # 头像 URL

