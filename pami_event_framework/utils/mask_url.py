"""通用工具函数"""

from urllib.parse import urlparse, urlunparse


def mask_url(url: str) -> str:
    """对 URL 中的密码做脱敏处理。

    例: mysql+asyncmy://root:secret@localhost:3306/db
      -> mysql+asyncmy://root:***@localhost:3306/db
    """
    parsed = urlparse(url)
    if parsed.password:
        masked = parsed._replace(
            netloc=(
                f"{parsed.username}:***@{parsed.hostname}"
                + (f":{parsed.port}" if parsed.port else "")
            )
        )
        return urlunparse(masked)
    return url
