import os
from functools import lru_cache

from pydantic import AliasChoices, BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseModel):
    env: str = "local"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    sentry_sdn: str = ""
    log_json_format: bool = False
    log_level: str = "INFO"


class DatabaseSettings(BaseModel):
    writer_db_url: str = "mysql+aiomysql://fastapi:fastapi@localhost:3306/fastapi"
    reader_db_url: str = "mysql+aiomysql://fastapi:fastapi@localhost:3306/fastapi"


class JwtSettings(BaseModel):
    secret_key: str = "fastapi"
    algorithm: str = "HS256"
    access_token_expire_seconds: int = 3600
    refresh_token_expire_seconds: int = 2 * 24 * 3600


class RedisSettings(BaseModel):
    host: str = "localhost"
    port: int = 6379
    password: str | None = None
    db: int = 0


class BlobStorageSettings(BaseModel):
    endpoint: str = "localhost:9000"
    access_key: str = "s3_access_key"
    secret_key: str = "s3_secret_key"
    is_secure: bool = False
    region: str = "us-east-1"
    disable_chunked_encoding: bool = False
    default_bucket: str = "blobs"
    storage_provider: str = "local"
    local_base_path: str = "./storage"
    url_expires: int = 3600
    signing_secret_key: str = ""
    internal_download_base_url: str = "http://localhost:8000/blob"
    thumbnail_redis_cache_enabled: bool = True
    thumbnail_redis_cache_ttl: int = 3600
    thumbnail_redis_cache_max_size: int = 600 * 1024
    material_draft_max_bytes: int = 2 * 1024 * 1024


class WxMiniappSettings(BaseModel):
    appid: str = ""
    secret: str = ""


class PasswordSettings(BaseModel):
    hash_secret_key: str = "a-secret-hash-key"


class SmtpSettings(BaseModel):
    host: str | None = None
    port: int = 587
    username: str | None = None
    password: str | None = None
    use_tls: bool = True


class FrameworkSettings(BaseModel):
    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_prefix: str = ""
    kafka_topic_strategy: str = "fine_grained"
    kafka_aggregate_topic_name: str = "domain-events"
    kafka_default_partitions: int = 10
    kafka_env_prefix: str = ""
    # Launcher
    launcher_consumer_group_id: str = "workflow-launcher"
    launcher_enable_canary_group: bool = False
    launcher_canary_group_suffix: str = "-canary"
    # Temporal
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "temporal-event-queue"
    temporal_env_prefix: str = ""
    # Outbox
    outbox_publish_interval_seconds: int = 10
    outbox_batch_size: int = 100
    outbox_max_retries: int = 3
    event_handler_domains: str = ""
    outbox_publish_batch_size: int = 1000
    ensure_group_before_publish: bool = False
    stream_autoclaim_idle_ms: int = 10 * 60 * 1000
    stream_autoclaim_count: int = 64
    # RabbitMQ（已废弃，保留兼容）
    rabbitmq_url: str = "amqp://admin:admin@localhost:5672/"
    exchange_name: str = "temporal_events"
    exchange_type: str = "topic"
    queue_name: str = "temporal_event_queue"
    routing_keys: str = "#"


class HealthSettings(BaseModel):
    check_interval_seconds: int = 120
    heartbeat_interval: int = 30
    heartbeat_ttl: int = 120
    zombie_timeout: int = 120
    stuck_pending_timeout: int = 300
    consumer_lag_timeout: int = 300
    message_max_retries: int = 5
    retry_base_delay: int = 60
    stuck_pending_recovery_strategy: str = "alert_only"
    monitored_consumers: str = ""
    domain_event_group_start_id: str = "$"
    domain_event_group_setid_on_start: str | None = None


class RigidTxSettings(BaseModel):
    flexible_transaction_max_retries: int = 3
    retry_interval_seconds: int = 60
    max_retry_interval_seconds: int = 3600
    alert_threshold_hours: int = 24
    queue_size_alert_threshold: int = 1000


class LibreOfficeSettings(BaseModel):
    path: str | None = None


class AISettings(BaseModel):
    dashscope_api_key: str = "dummy_key"


class UserSettings(BaseModel):
    avatar_status_key_prefix: str = "user:avatar:status:"
    avatar_status_ttl: int = 86400


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    app: AppSettings = AppSettings()
    db: DatabaseSettings = DatabaseSettings()
    jwt: JwtSettings = JwtSettings()
    redis: RedisSettings = RedisSettings()
    blob_storage: BlobStorageSettings = Field(
        default_factory=BlobStorageSettings,
        validation_alias=AliasChoices("blob_storage", "s3_blob"),
    )
    wx_miniapp: WxMiniappSettings = WxMiniappSettings()
    password: PasswordSettings = PasswordSettings()
    smtp: SmtpSettings = SmtpSettings()
    framework: FrameworkSettings = FrameworkSettings()
    health: HealthSettings = HealthSettings()
    rigid_tx: RigidTxSettings = RigidTxSettings()
    libreoffice: LibreOfficeSettings = LibreOfficeSettings()
    ai: AISettings = AISettings()
    user: UserSettings = UserSettings()
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: int = 60

    @property
    def s3_blob(self) -> BlobStorageSettings:
        return self.blob_storage


S3BlobSettings = BlobStorageSettings


@lru_cache
def get_settings() -> Settings:
    return Settings()


config: Settings = get_settings()
