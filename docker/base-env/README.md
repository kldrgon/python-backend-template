# Base Environment

这个目录提供一套可复用的基础依赖环境，目标是作为单机可持久化、可长期运行的 base-env 基线。

当前包含：

- PostgreSQL
- Kafka
- Redis
- Temporal
- Temporal UI
- MinIO（已预留，默认注释）

这些服务都配置了持久化卷。

## 文件说明

- `docker-compose.base-env.yml`：基础环境编排文件
- `.env.base-env.example`：示例环境变量
- `postgres/init/01-create-extra-databases.sh`：初始化额外数据库
- `temporal/setup-postgres.sh`：初始化 Temporal PostgreSQL schema
- `temporal/dynamicconfig/base-env.yaml`：Temporal 动态配置

## 使用方式

1. 复制环境变量文件

```bash
cp docker/base-env/.env.base-env.example docker/base-env/.env.base-env
```

2. 启动基础环境

```bash
docker compose --env-file docker/base-env/.env.base-env -f docker/base-env/docker-compose.base-env.yml up -d
```

3. 停止基础环境

```bash
docker compose --env-file docker/base-env/.env.base-env -f docker/base-env/docker-compose.base-env.yml down
```

如果需要连同数据卷一起删除：

```bash
docker compose --env-file docker/base-env/.env.base-env -f docker/base-env/docker-compose.base-env.yml down -v
```

## 端口

- PostgreSQL：`${POSTGRES_PORT}`，默认 `5432`
- Kafka 外部访问：`${KAFKA_EXTERNAL_PORT}`，默认 `9094`
- Redis：`${REDIS_PORT}`，默认 `6379`
- Temporal：`${TEMPORAL_PORT}`，默认 `7233`
- Temporal UI：`${TEMPORAL_UI_PORT}`，默认 `8088`
- MinIO API：`${MINIO_API_PORT}`，默认 `9000`
- MinIO Console：`${MINIO_CONSOLE_PORT}`，默认 `9001`

## Temporal 说明

当前 Temporal 方案使用更接近生产基线的服务化方式：

- `temporalio/server`
- 独立的 `temporal-schema-setup`
- 独立的 `temporal-ui`

关键点：

- `DB=postgres12` 是 Temporal 官方 compose 中的常见配置名
- 这里的 `postgres12` 是 Temporal 的 PostgreSQL 驱动标识，不要求实际数据库镜像必须是 PostgreSQL 12；当前使用 `postgres:16-alpine` 也是可以的
- `POSTGRES_SEEDS=postgres` 通过 compose 内部服务名连接 PostgreSQL
- schema 初始化由 `temporal-schema-setup` 单独执行
- `temporal` 服务使用 `SKIP_SCHEMA_SETUP=true`
- 已显式指定：
  - `DBNAME=${POSTGRES_TEMPORAL_DB}`
  - `VISIBILITY_DBNAME=${POSTGRES_TEMPORAL_VISIBILITY_DB}`
  - `TEMPORAL_ADDRESS=temporal:7233`
  - `TEMPORAL_CLI_ADDRESS=temporal:7233`

说明：

- 这仍然不是多节点高可用方案
- 但比 `auto-setup` 更适合作为生产基线
- 当前是单实例 Temporal Server + PostgreSQL 持久化
- 如果以后需要更高等级生产部署，再继续拆分 frontend / history / matching / worker 等角色

## Kafka 外部访问

Kafka 同时支持两种访问方式：

- 容器内访问：`kafka:9092`
- 宿主机/IP 访问：`${KAFKA_EXTERNAL_HOST}:${KAFKA_EXTERNAL_PORT}`

如果其他机器需要访问 Kafka，把 `.env.base-env` 里的：

```text
KAFKA_EXTERNAL_HOST=localhost
```

改成宿主机真实 IP 即可。

## MinIO

MinIO 目前作为可选服务预留在 compose 文件里，默认注释。

原因：

- 当前应用默认 Blob 存储方案是本地文件
- 新项目初始化阶段通常不强制要求 S3 兼容存储

如果要启用：

- 取消 `docker-compose.base-env.yml` 里 `minio` 服务和 `minio_data` 卷的注释
- 根据 `.env.base-env` 调整账号密码和端口
