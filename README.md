# Backend Template

这是一个用于初始化新项目的后端模板仓库。

当前仓库已经收敛为最小可运行起点，默认保留：

- 用户域基础能力
- Blob 域基础能力
- Outbox 框架初始化
- 本地文件存储默认方案

未接入的新业务模型和早期实验性表结构已从初始化链中移除。

## 当前初始化范围

当前默认数据库初始化只包含两段迁移：

1. `framework_outbox`
2. `pre_domain`

对应关系：

- `framework_outbox`：框架级 `outbox_events`
- `pre_domain`：当前预备域的最小业务表

当前保留的核心模型：

- `UserModel`
- `UserRoleModel`
- `UserLinkedAccountModel`
- `BlobModel`
- `StorageLocatorModel`
- `BlobReferenceModel`

## Blob 存储默认方案

Blob 现在默认使用本地文件存储。

默认配置：

```python
config.blob_storage.storage_provider == "local"
config.blob_storage.local_base_path == "./storage"
```

说明：

- `local` 已正式接入 `create_storage_adapter()`
- 默认新项目不再依赖 MinIO 才能启动 Blob 基础能力
- `minio` / `s3` 方案仍然保留，可按需切换

兼容性：

- 新配置主入口：`config.blob_storage`
- 旧名称：`config.s3_blob` 仍保留兼容别名
- 旧的配置输入键 `s3_blob` 仍可被解析

## 环境配置

主要配置位于 `core/config/settings.py`。

最常用的是：

- `config.db.writer_db_url`
- `config.db.reader_db_url`
- `config.blob_storage.storage_provider`
- `config.blob_storage.local_base_path`
- `config.blob_storage.default_bucket`
- `config.framework.*`

如果你仍使用旧配置名，当前仓库也兼容：

```python
config.s3_blob
```

但新代码应优先使用：

```python
config.blob_storage
```

## 快速启动

### 1. 安装依赖

```shell
uv venv
uv sync --no-install-project --extra dev
```

### 2. 执行迁移

```shell
uv run alembic upgrade head
```

### 3. 启动服务

```shell
uv run python main.py --env local --debug
```

### 4. 运行测试

```shell
uv run pytest
```

## 测试说明

当前测试约定：

- 单元测试：纯内存
- 集成测试：真实 DB
- 系统测试：真实 DB + Redis + Kafka + Temporal

其中 Blob 系统测试默认会用 `LocalStorageAdapter` 覆盖存储层，不依赖真实 MinIO。

## 数据库与 Alembic

当前 Alembic 头部应为：

```shell
uv run alembic heads
```

预期结果：

```text
pre_domain (head)
```

当前历史链应为：

```text
<base> -> framework_outbox -> pre_domain
```

## SQLAlchemy 使用约定

写操作默认使用全局 `session`。

并发查询场景应使用 `session_factory()`，例如：

```python
from core.db import session_factory


async def get_by_id(*, user_id: str):
    async with session_factory() as read_session:
        result = await read_session.execute(...)
        return result.scalars().first()
```

## 目录说明

当前初始化仓库里与启动最相关的目录：

- `app/user/`
- `app/blob/`
- `core/config/`
- `core/db/`
- `migrations/versions/`
- `tests/`

`docs/` 当前只保留初始化模板仍然适用的通用说明，例如测试说明、领域边界设计和领域实现模板。
