from __future__ import annotations

"""
## NOTE: 该文件夹存在的意义为，fastapi 与 @inject 配合使用具有一定问题
## @inject 通过函数变量来查询，而fastapi的路由推荐使用Annotated ,会导致inject失效，故只能通过文件夹来管理，通过get_container,get_user_domain_service等函数来获取容器中的服务
"""

from .container import get_container
from .user import get_user_domain_service
from .blob import (
    get_blob_attachment_domain_service,
    get_blob_external_command_service,
    get_blob_file_domain_service,
    get_blob_public_domain_service,
    get_blob_query_service,
)
from .security import get_current_user_id_optional, require_admin

__all__ = [
    "get_container",
    "get_user_domain_service",
    "get_blob_attachment_domain_service",
    "get_blob_external_command_service",
    "get_blob_file_domain_service",
    "get_blob_public_domain_service",
    "get_blob_query_service",
    "get_current_user_id_optional",
    "require_admin",
]