"""
系统测试配置

测试策略：
- 使用真实数据库（test DB）
- 使用真实 Redis（Testcontainers redis:7-alpine）
- 使用真实 Kafka（Testcontainers Redpanda，比 Confluent 启动快）
- 使用真实 Temporal（SDK 内置 WorkflowEnvironment.start_local()，无需 Docker）
- 使用真实 FastAPI app + 完整中间件链
- 通过 HTTP 请求测试（httpx AsyncClient）
- 只 Mock 真正无法控制的外部依赖（如微信 API、SMTP）

Fixture 层级：
  redis_container (session)      ← 启动 Redis 容器，patch 客户端
  redpanda_container (session)   ← 启动 Redpanda 容器，更新 kafka config
  temporal_env (session)         ← 启动 Temporal 本地服务，更新 temporal config
  ─── 后台 Worker（完整事件链）───
  outbox_publisher_bg (session)  ← DB outbox → Kafka（0.5s 短轮询）
  event_launcher_bg (session)    ← Kafka → 触发 Temporal Workflow
  temporal_worker_bg (session)   ← 运行所有 Workflow + Activity
  all_workers_running (function) ← 便捷 fixture，确保整条链都在跑
  ─── Per-Test ───────────────────
  session_context (autouse)      ← 每个测试独立的 DB session context
  session                        ← 保证 DB + Redis 干净
  app                            ← 启动 FastAPI lifespan
  client                         ← httpx AsyncClient
  registered_user / auth_headers ← 用户相关 fixture
"""

import asyncio
import os
from contextlib import contextmanager
from uuid import uuid4

import pytest
import pytest_asyncio

from httpx import AsyncClient, ASGITransport
from redis import asyncio as aioredis

from core.db.session import (
    reset_session_context,
    session as db_session,
    set_session_context,
)
from core.helpers.token import TokenHelper
from core.config import config
from tests.support.test_db_coordinator import TestDbCoordinator
from tests.support.async_utils import wait_until  # noqa: F401  供测试文件通过 conftest 直接使用

test_db_coordinator = TestDbCoordinator()


# ── 跳过 Testcontainers 说明 ──────────────────────────────────────────────
#
# 在 .env.test 中设置以下字段可跳过 Testcontainers，直接对接已有服务：
#
#   REDIS__URL=redis://:password@host:6379/0   （优先，完整 URL）
#   或分项设置：
#   REDIS__HOST=host  REDIS__PORT=6379  REDIS__PASSWORD=xxx
#
#   FRAMEWORK__KAFKA_BOOTSTRAP_SERVERS=host:9092
#   FRAMEWORK__TEMPORAL_HOST=host:7233
#
# 未设置则自动启动 Testcontainers（需要本地 Docker daemon）。
# ─────────────────────────────────────────────────────────────────────────


def _resolve_redis_url() -> str | None:
    """从 REDIS__URL 或 REDIS__HOST/PORT/PASSWORD 拼出 Redis URL，未配置返回 None。"""
    url = os.environ.get("REDIS__URL")
    if url:
        return url
    host = os.environ.get("REDIS__HOST")
    if not host:
        return None
    port = os.environ.get("REDIS__PORT", "6379")
    password = os.environ.get("REDIS__PASSWORD", "")
    db = os.environ.get("REDIS__DB", "0")
    if password:
        return f"redis://:{password}@{host}:{port}/{db}"
    return f"redis://{host}:{port}/{db}"


async def _safe_close_redis_client(client) -> None:
    """在不同 loop 清理阶段容忍 redis asyncio 客户端关闭异常。"""
    try:
        await client.aclose()
    except RuntimeError:
        pass


# ── Testcontainers / 外部服务（Session 级，整个测试会话只启动一次）────────


@pytest.fixture(scope="session")
def redis_service():
    """
    优先读取 REDIS__URL 或 REDIS__HOST/PORT/PASSWORD；未设置则启动 Testcontainers Redis 容器。
    仅负责提供 Redis 服务连接信息，不复用异步客户端实例。
    """
    url = _resolve_redis_url()

    @contextmanager
    def _use_existing(redis_url: str):
        from urllib.parse import urlparse
        parsed = urlparse(redis_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379
        yield {"host": host, "port": port, "redis_url": redis_url}

    if url:
        with _use_existing(url) as info:
            yield info
    else:
        from testcontainers.redis import RedisContainer

        with RedisContainer(image="redis:7-alpine") as container:
            host = container.get_container_host_ip()
            port = container.get_exposed_port(6379)
            redis_url = f"redis://{host}:{port}/0"
            yield {"host": host, "port": int(port), "redis_url": redis_url}


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def redis_container(redis_service):
    """
    整个 session 共享同一批 Redis 客户端并 patch 到模块级变量。
    session 事件循环统一，不存在跨 loop 复用问题。
    """
    import core.helpers.redis as redis_module

    redis_url = redis_service["redis_url"]
    app_client = aioredis.from_url(redis_url, decode_responses=True)
    app_binary_client = aioredis.from_url(redis_url, decode_responses=False)
    test_client = aioredis.from_url(redis_url, decode_responses=True)

    redis_module._default_redis_client = app_client
    redis_module.redis_client = app_client
    redis_module._binary_redis_client = app_binary_client
    redis_module.binary_redis_client = app_binary_client

    try:
        yield {
            "host": redis_service["host"],
            "port": redis_service["port"],
            # 测试代码使用独立客户端，避免与 app 共用连接导致跨 loop 错误
            "client": test_client,
        }
    finally:
        await _safe_close_redis_client(test_client)
        await _safe_close_redis_client(app_client)
        await _safe_close_redis_client(app_binary_client)


@pytest.fixture(scope="session")
def redpanda_container():
    """
    .env.test 中 FRAMEWORK__KAFKA_BOOTSTRAP_SERVERS 有值则直接用；否则启动 Testcontainers Redpanda。
    """
    bootstrap_servers = os.environ.get("FRAMEWORK__KAFKA_BOOTSTRAP_SERVERS")

    if bootstrap_servers:
        config.framework.kafka_bootstrap_servers = bootstrap_servers
        yield {"bootstrap_servers": bootstrap_servers}
    else:
        from testcontainers.kafka import RedpandaContainer

        with RedpandaContainer() as container:
            bootstrap_servers = container.get_bootstrap_server()
            config.framework.kafka_bootstrap_servers = bootstrap_servers
            yield {"bootstrap_servers": bootstrap_servers}


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def temporal_env():
    """
    .env.test 中 FRAMEWORK__TEMPORAL_HOST 有值则对接已有 Temporal；否则启动本地测试服务。
    """
    temporal_host = os.environ.get("FRAMEWORK__TEMPORAL_HOST")

    if temporal_host:
        from temporalio.client import Client as TemporalClient

        config.framework.temporal_host = temporal_host
        client = await TemporalClient.connect(temporal_host)

        class _ExternalTemporalEnv:
            def __init__(self, c):
                self.client = c

        yield _ExternalTemporalEnv(client)
    else:
        from temporalio.testing import WorkflowEnvironment

        async with await WorkflowEnvironment.start_local() as env:
            target_host = env.client.service_client.config.target_host
            config.framework.temporal_host = target_host
            yield env


# ── Background Workers（Session 级，整条事件链）──────────────────────────


@pytest.fixture(scope="session")
def _do_autodiscover():
    """
    自动发现所有 Workflow 和 Activity，整个 session 只运行一次。
    必须在 worker 相关 fixture 之前执行。
    """
    from pami_event_framework.autodiscovery import autodiscover
    from core.config import EVENT_HANDLER_PACKAGES

    autodiscover(packages=EVENT_HANDLER_PACKAGES)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def outbox_publisher_bg(redpanda_container):
    """
    后台运行 Outbox Publisher（DB outbox → Kafka）。
    使用 0.5s 短轮询间隔，测试中事件能快速被推送。
    """
    from pami_event_framework.kafka.config import KafkaConfig
    from pami_event_framework.kafka.producer import KafkaEventProducer
    from pami_event_framework.tasks.outbox_publisher import OutboxPublisher

    kafka_producer = KafkaEventProducer(
        config=KafkaConfig(
            bootstrap_servers=redpanda_container["bootstrap_servers"],
            env_prefix=config.framework.kafka_env_prefix or None,
        )
    )
    await kafka_producer.start()

    publisher = OutboxPublisher(
        kafka_producer=kafka_producer,
        batch_size=100,
        interval_seconds=0.5,
    )
    task = asyncio.create_task(publisher.start())

    yield publisher

    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    await kafka_producer.stop()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def event_launcher_bg(_do_autodiscover, redpanda_container, temporal_env):
    """
    后台运行 Workflow Launcher（Kafka 消费 → 触发 Temporal Workflow）。
    直接复用 temporal_env.client，无需重新连接 Temporal。
    """
    from pami_event_framework.launcher.workflow_launcher import WorkflowLauncher
    from pami_event_framework.kafka.config import KafkaConfig
    from pami_event_framework.config import TemporalConfig
    from pami_event_framework.autodiscovery import get_event_handler_map

    launcher = WorkflowLauncher(
        kafka_config=KafkaConfig(
            bootstrap_servers=redpanda_container["bootstrap_servers"],
            env_prefix=config.framework.kafka_env_prefix or None,
        ),
        temporal_client=temporal_env.client,
        event_handler_map=get_event_handler_map(),
        consumer_group_id="test-workflow-launcher",
        temporal_config=TemporalConfig(
            server_url=config.framework.temporal_host,
            env_prefix=config.framework.temporal_env_prefix or config.framework.kafka_env_prefix or None,
        ),
    )
    task = asyncio.create_task(launcher.start())

    yield launcher

    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def temporal_worker_bg(_do_autodiscover, temporal_env):
    """
    后台运行 Temporal Worker（执行所有 Workflow 和 Activity）。
    初始化独立 DI 容器，供 @inject 修饰的 Activity 使用。
    """
    from temporalio.worker import Worker, UnsandboxedWorkflowRunner
    from pami_event_framework.autodiscovery import (
        get_all_task_queues,
        get_workflows_by_queue,
        get_all_activities,
    )
    from app.container import Container

    container = Container()
    container.init_resources()
    container.wire(packages=["app"])
    temporal_env_prefix = config.framework.temporal_env_prefix or config.framework.kafka_env_prefix or ""

    all_activities = get_all_activities()

    tasks = []
    for task_queue in get_all_task_queues():
        actual_task_queue = (
            f"{temporal_env_prefix}.{task_queue}" if temporal_env_prefix else task_queue
        )
        worker = Worker(
            temporal_env.client,
            task_queue=actual_task_queue,
            workflows=get_workflows_by_queue(task_queue),
            activities=all_activities,
            workflow_runner=UnsandboxedWorkflowRunner(),
        )
        tasks.append(asyncio.create_task(worker.run()))

    yield

    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    container.shutdown_resources()


@pytest_asyncio.fixture(loop_scope="session")
async def all_workers_running(outbox_publisher_bg, event_launcher_bg, temporal_worker_bg):
    """
    便捷 fixture：确保完整事件链（outbox → Kafka → Temporal → Activity）都在后台运行。

    在需要验证完整异步流程的系统测试中使用：
        async def test_register_user_complete_flow(client, all_workers_running, redis_container):
            resp = await client.post("/user/v1/register", ...)
            await wait_until(lambda: check_welcome_email_sent(...), timeout=30)
    """
    yield


# ── DB Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def _apply_migrations():
    """Session 级别：只在整个测试会话开始时跑一次 Alembic migration。"""
    test_db_coordinator.apply_alembic()


@pytest_asyncio.fixture(scope="function", autouse=True, loop_scope="session")
async def session_context():
    """每个系统测试独立的 session context，必须是 async 才能在事件循环 task 内设置 ContextVar"""
    session_id = str(uuid4())
    context = set_session_context(session_id=session_id)
    yield
    try:
        await db_session.remove()
    except (RuntimeError, LookupError):
        pass
    reset_session_context(context=context)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def session(_apply_migrations, redis_service, redis_container):
    """整个测试会话开始时清空一次 DB + Redis，不在测试间重复清理"""
    test_db_coordinator.delete_all()
    redis_client = aioredis.from_url(redis_service["redis_url"], decode_responses=True)
    await redis_client.flushdb()
    try:
        yield db_session
    finally:
        try:
            await db_session.remove()
        except (RuntimeError, LookupError):
            pass
        await _safe_close_redis_client(redis_client)


# ── App Fixture ───────────────────────────────────────────────────────────


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def app(session, redpanda_container, temporal_env):
    """
    启动真实 FastAPI app（真实 Redis + Redpanda Kafka + Temporal）。
    每个测试独立的 app 实例，重置 WebBootstrap 单例确保使用最新 config。
    """
    import app.bootstrap_web as bw
    bw._web_bootstrap = None

    from app.server import create_app
    app_ = create_app()

    async with app_.router.lifespan_context(app_):
        yield app_


# ── HTTP Client Fixture ───────────────────────────────────────────────────


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def client(app):
    """
    提供 httpx AsyncClient，通过 ASGITransport 直连 ASGI app。
    lifespan 已在 app fixture 中启动，此处无需重复触发。
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


# ── Auth Helpers ──────────────────────────────────────────────────────────


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def registered_user(client, redis_service) -> dict:
    """
    注册一个测试用户并返回其基本信息。
    向真实 Redis 预写入验证码，而非 mock CaptchaService。
    使用 uuid 后缀确保多次 session 运行不冲突。
    """
    email = f"system_test_{uuid4().hex[:8]}@example.com"
    captcha_code = "000000"

    redis_client = aioredis.from_url(redis_service["redis_url"], decode_responses=True)
    await redis_client.setex(f"captcha:{email}", 300, captcha_code)

    user_data = {
        "email": email,
        "nickname": "systestuser",
        "password": "Password123",
        "confirmPassword": "Password123",
        "role": "student",
        "captcha_code": captcha_code,
    }

    resp = await client.post("/user/v1/register", json=user_data)
    assert resp.status_code == 200, f"注册失败: {resp.text}"

    await _safe_close_redis_client(redis_client)
    return {**user_data, "user_id": resp.json()["data"]["userId"]}


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def auth_headers(client, registered_user) -> dict:
    """
    使用 registered_user 登录，返回 Authorization header。
    可直接传给 client.get/post(..., headers=auth_headers)。
    """
    resp = await client.post(
        "/user/v1/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    assert resp.status_code == 200, f"登录失败: {resp.text}"
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def make_token() -> callable:
    """
    生成测试 JWT Token 的工厂 fixture，无需真实用户。

    用法：
        token = make_token(user_id="u1")
        headers = {"Authorization": f"Bearer {token}"}
    """
    def _make(user_id: str, sub: str = "access") -> str:
        return TokenHelper.encode(
            payload={"user_id": user_id, "sub": sub},
            expire_period=3600,
        )
    return _make
