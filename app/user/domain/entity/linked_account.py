from dataclasses import dataclass, field


@dataclass(slots=True)
class LinkedAccount:
    provider: str
    provider_account_id: str

    # OAuth 登录预留字段（MVP阶段为 None）
    access_token: str | None = None
    refresh_token: str | None = None
    expires_at: int | None = None
    token_type: str | None = None
    scope: str | None = None
    id_token: str | None = None

    # 平台特有原始数据（如微信 union_id、session_key 等）
    raw_data: dict | None = None
