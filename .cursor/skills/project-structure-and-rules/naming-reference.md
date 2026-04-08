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

## Concrete Naming Example

如果要新增课程仓储、查询服务和创建请求模型：

```text
Repository:
- interface: CourseRepository
- implementation: SQLAlchemyCourseRepository

QueryService:
- interface: CourseQueryService
- implementation: SQLAlchemyCourseQueryService

DTO:
- CreateCourseRequest
- CourseDetailResponse
```

## Real Code Example

项目里的真实命名形态如下：

```python
class CourseQueryService(Protocol):
    async def get_course(self, *, course_id: str) -> CourseDTO | None:
        ...


class SQLAlchemyCourseQueryService(CourseQueryService):
    async def get_course(self, *, course_id: str) -> CourseDTO | None:
        stmt = select(CourseModel).where(CourseModel.course_id == course_id)
        ...
```

```python
class SQLAlchemyUserRepository(BaseAggregateRepository, UserRepository):
    async def get_user_by_id(self, *, user_id: str) -> User | None:
        stmt = await session.execute(
            _with_relations(select(UserModel).where(UserModel.user_id == user_id))
        )
        ...
```

```python
class CreateCourseRequest(BaseModel):
    title: str = Field(..., min_length=1)
    summary: list | None = None
    content: list | None = None
```

这些真实代码分别对应：

- 查询接口：`CourseQueryService`
- 查询实现：`SQLAlchemyCourseQueryService`
- 仓储实现：`SQLAlchemyUserRepository`
- 请求 DTO：`CreateCourseRequest`
