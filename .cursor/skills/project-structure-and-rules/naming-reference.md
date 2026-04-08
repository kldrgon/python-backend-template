# Naming Reference

这里的 QueryService 指面向读侧查询的服务接口。
这里的 UseCase 指单个业务用例的应用层入口。
这里的 DTO 指用于输入输出传递的数据对象。

## Interface And Implementation Patterns

```text
Repository
- interface: <Aggregate>Repository
- implementation: SQLAlchemy<Aggregate>Repository

QueryService
- interface: <Aggregate>QueryService
- implementation: SQLAlchemy<Aggregate>QueryService

DomainService
- interface: <Capability>DomainService
- implementation: SQLAlchemy<Capability>DomainService

UseCase
- interface: <Capability>UseCase
- implementation: <Capability>CommandService
```

## Naming Anti-Examples

```text
Bad:
- <Aggregate>SQLAlchemyRepository
- Sqlalchemy<Aggregate>Repository
- SA<Aggregate>Repository

Better:
- SQLAlchemy<Aggregate>Repository
```

## File Naming Examples

API 路由文件可按项目选定的分类标准命名：

- `<aggregate>.py`
- `<capability>.py`
- `<use_case>.py`
- `<module>.py`

其他示例：

- `<aggregate>_mapper.py`
- `<aggregate>_query.py`
- `<aggregate>_events.py`
- `<capability>_service.py`

## DTO And Event Examples

```text
DTO:
- Create<Aggregate>Request
- Update<Aggregate>Request
- <Aggregate>DetailResponse

Event:
- <Aggregate>CreatedEvent
- <Aggregate>UpdatedEvent
- <Capability>TriggeredEvent
```
