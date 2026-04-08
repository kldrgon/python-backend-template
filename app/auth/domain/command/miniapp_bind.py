from dataclasses import dataclass


@dataclass
class MiniappBindCommand:
    openid: str
    phone: str
    unionid: str | None = None
    session_meta: dict | None = None
