# Dev Environment

这个目录提供一套用于开发和测试的临时依赖环境。

目标：

- 快速启动
- 不做持久化
- 随起随销
- 满足本地开发、联调和测试辅助场景

当前包含：

- PostgreSQL
- Kafka
- Redis
- Temporal（纯内存）
- MinIO（已预留，默认注释）

## 文件说明

- `docker-compose.dev-env.yml`：开发/测试环境编排文件
- `.env.dev-env.example`：示例环境变量

## 使用方式

1. 复制环境变量文件

```bash
cp docker/dev-env/.env.dev-env.example docker/dev-env/.env.dev-env
```

2. 启动 dev-env

```bash
docker compose --env-file docker/dev-env/.env.dev-env -f docker/dev-env/docker-compose.dev-env.yml up -d
```

3. 停止 dev-env

```bash
docker compose --env-file docker/dev-env/.env.dev-env -f docker/dev-env/docker-compose.dev-env.yml down
```

## 端口

- PostgreSQL：`${POSTGRES_PORT}`，默认 `55432`
- Kafka：`${KAFKA_EXTERNAL_PORT}`，默认 `39094`
- Redis：`${REDIS_PORT}`，默认 `56379`
- Temporal gRPC：`${TEMPORAL_PORT}`，默认 `57233`
- Temporal UI：`${TEMPORAL_UI_PORT}`，默认 `58233`

## Temporal 说明

这里的 Temporal 使用官方 CLI 开发服务：

```text
temporal server start-dev --ip 0.0.0.0
```

特点：

- 使用开发模式
- 默认是纯内存 SQLite
- 不依赖 PostgreSQL
- 容器重启后数据丢失

这正适合测试和快速开发，不适合作为长期运行环境。

## Kafka 说明

Kafka 仍保留容器内和宿主机双地址访问：

- 容器内：`kafka:9092`
- 宿主机/IP：`${KAFKA_EXTERNAL_HOST}:${KAFKA_EXTERNAL_PORT}`

## MinIO

MinIO 作为可选依赖预留，默认注释。

当前应用默认 Blob 存储方案是本地文件，因此通常不需要启用它。
