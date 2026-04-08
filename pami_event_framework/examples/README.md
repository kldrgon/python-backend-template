# Examples 使用说明

## 示例文件

### 1. example_simple.py - 简单示例
基础的Kafka事件发布和消费。

这个示例没有引入领域模型，因此更适合作为 `ApplicationEvent` 的示例。

**启动方式：**
```bash
# 发布事件
python example_simple.py publish

# 消费事件
python example_simple.py consume
```

### 2. example_complete.py - 完整示例
完整的事件驱动流程，包括：
- 领域事件定义
- 聚合根
- Outbox模式
- Temporal Workflow
- WorkflowLauncher

**启动方式：**
```bash
# 1. 创建订单（发布事件到Outbox）
python example_complete.py create_order

# 2. 启动Outbox发布器（Outbox -> Kafka）
python example_complete.py outbox_publisher

# 3. 启动Temporal Worker（执行Workflow）
python example_complete.py temporal_worker

# 4. 启动WorkflowLauncher（Kafka -> Temporal）
python example_complete.py workflow_launcher
```

## 前置条件

### 1. Kafka
```bash
# Docker启动Kafka
docker run -d --name kafka \
  -p 9092:9092 \
  -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092 \
  apache/kafka:latest
```

### 2. Temporal
```bash
# Docker启动Temporal
docker run -d --name temporal \
  -p 7233:7233 \
  temporalio/auto-setup:latest
```

### 3. PostgreSQL
```bash
# Docker启动PostgreSQL
docker run -d --name postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=event_framework \
  -p 5432:5432 \
  postgres:15
```

### 4. 创建Outbox表
```bash
# 执行SQL脚本
psql -U postgres -d event_framework -f ../persistence/sql/create_outbox_table_pg.sql
```

## 完整流程演示

### 终端1：启动Temporal Worker
```bash
python example_complete.py temporal_worker
```

### 终端2：启动WorkflowLauncher
```bash
python example_complete.py workflow_launcher
```

### 终端3：启动Outbox发布器
```bash
python example_complete.py outbox_publisher
```

### 终端4：创建订单
```bash
python example_complete.py create_order
```

## 架构流程

```
create_order
  ↓
写入Outbox表
  ↓
outbox_publisher 轮询
  ↓
发送到Kafka
  ↓
workflow_launcher 消费
  ↓
启动Temporal Workflow
  ↓
temporal_worker 执行
```

## 注意事项

1. **修改配置**：示例中的数据库连接等配置需要根据实际环境修改
2. **依赖安装**：确保已安装所有依赖 `pip install -r requirements.txt`
3. **幂等性**：相同事件多次发送只会执行一次（Workflow ID保证）
4. **事件语义**：采用领域模型时使用 `DomainEvent`；不采用领域模型时由应用层显式产生 `ApplicationEvent`
