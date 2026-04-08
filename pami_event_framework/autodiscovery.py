# -*- coding: utf-8 -*-
"""Workflow/Activity 自动发现机制

提供基于装饰器的自动注册和发现能力，类似 Celery autodiscover_tasks() 和 Spring @Component。
支持通过 tags 进行过滤。
"""

import re
import structlog
import importlib
import inspect

from typing import Optional, List, Dict, Any, Tuple, Callable
from pathlib import Path


logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


# ============ 全局注册表 ============

# Workflow 注册表 {event_type: [(workflow_class, queue, domain, tags), ...]}
_WORKFLOW_REGISTRY: Dict[str, List[Tuple[type, str, str, List[str]]]] = {}

# Signal Handler 注册表
# {event_type: [(workflow_class, signal_name, workflow_id_resolver, payload_resolver, domain, tags), ...]}
_SIGNAL_HANDLER_REGISTRY: Dict[
    str,
    List[Tuple[type, str, Callable[[Dict[str, Any]], str], Callable[[Dict[str, Any]], Any], str, List[str]]],
] = {}

# Activity 注册表 [(activity_func, domain, tags), ...]
_ACTIVITY_REGISTRY: List[Tuple[Callable, str, List[str]]] = []


# ============ 内部工具函数 ============

def _to_snake_case(name: str) -> str:
    """驼峰转蛇形：UserCreated -> user_created"""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def _infer_event_from_class(cls: type) -> str:
    """从 workflow 类名推断事件类型

    OnUserCreatedWorkflow -> USER_CREATED
    """
    name = cls.__name__
    if name.startswith('On') and name.endswith('Workflow'):
        event_name = name[2:-8]  # 去掉 On 和 Workflow
        return _to_snake_case(event_name).upper()

    # 尝试从 docstring 读取：'''事件类型: USER_CREATED'''
    doc = inspect.getdoc(cls)
    if doc and '事件类型:' in doc:
        parts = doc.split('事件类型:')[1].strip().split()
        if parts:
            return parts[0]

    raise ValueError(f"Cannot infer event type from {cls.__name__}. Please specify explicitly.")


def _infer_domain_from_module(module_path: str) -> str:
    """从模块路径推断域名

    app.user.event_handler.workflows -> user
    app.blob.event_handler.activities -> blob
    """
    parts = module_path.split('.')
    if len(parts) >= 2 and parts[0] == 'app':
        return parts[1]
    return "default"


def _infer_queue_from_domain(domain: str) -> str:
    """从域名推断默认队列名"""
    return "default-event-handler-queue"


# ============ 装饰器 ============

def event_handler(
    event_type: Optional[str] = None,
    queue: Optional[str] = None,
    domain: Optional[str] = None,
    tags: Optional[List[str]] = None
):
    """Workflow 注册装饰器

    将 workflow 类注册到全局表，支持自动推断事件类型、队列和域。

    Args:
        event_type: 事件类型，如 "USER_CREATED"，不填则从类名推断
        queue: 任务队列，如 "default-event-handler-queue"，不填则使用默认
        domain: 域名，如 "user"，不填则从模块路径推断
        tags: 标签列表，用于过滤，如 ["email", "critical"]

    Example:
        @workflow.defn
        @event_handler()  # 自动推断
        class OnUserCreatedWorkflow:
            ...

        @workflow.defn
        @event_handler(tags=["email", "critical"])
        class OnUserCreatedWorkflow:
            ...
    """
    def decorator(cls: type) -> type:
        inferred_event = event_type or _infer_event_from_class(cls)
        inferred_domain = domain or _infer_domain_from_module(cls.__module__)
        inferred_queue = queue or _infer_queue_from_domain(inferred_domain)
        tag_list = tags or []

        if inferred_event not in _WORKFLOW_REGISTRY:
            _WORKFLOW_REGISTRY[inferred_event] = []

        _WORKFLOW_REGISTRY[inferred_event].append((
            cls,
            inferred_queue,
            inferred_domain,
            tag_list,
        ))

        # 注意：该装饰器会在 Temporal workflow sandbox 导入期执行。
        # 这里调用 structlog 可能触发 datetime.now()，导致 sandbox 校验失败。
        # 因此避免在此处记录日志。

        return cls

    return decorator


def signal_handler(
    *,
    event_type: str,
    signal_name: str,
    workflow_id_resolver: Callable[[Dict[str, Any]], str],
    payload_resolver: Optional[Callable[[Dict[str, Any]], Any]] = None,
    domain: Optional[str] = None,
    tags: Optional[List[str]] = None,
):
    """Signal Handler 注册装饰器

    将 workflow 类注册到 Signal Handler 全局表，用于 Kafka 事件桥接到
    已存在的 Workflow Signal。

    Args:
        event_type: 事件类型，如 "PAYMENT_CALLBACK_RECEIVED"
        signal_name: Workflow 中定义的 signal 名称
        workflow_id_resolver: 从事件数据解析 workflow_id 的函数
        payload_resolver: 从事件数据解析 signal payload 的函数，不填则透传事件
        domain: 域名，如 "payment"，不填则从模块路径推断
        tags: 标签列表，用于过滤
    """

    if not event_type:
        raise ValueError("signal_handler requires event_type")
    if not signal_name:
        raise ValueError("signal_handler requires signal_name")
    if workflow_id_resolver is None:
        raise ValueError("signal_handler requires workflow_id_resolver")

    def decorator(cls: type) -> type:
        inferred_domain = domain or _infer_domain_from_module(cls.__module__)
        tag_list = tags or []
        effective_payload_resolver = payload_resolver or (lambda event_data: event_data)

        if event_type not in _SIGNAL_HANDLER_REGISTRY:
            _SIGNAL_HANDLER_REGISTRY[event_type] = []

        _SIGNAL_HANDLER_REGISTRY[event_type].append(
            (
                cls,
                signal_name,
                workflow_id_resolver,
                effective_payload_resolver,
                inferred_domain,
                tag_list,
            )
        )

        return cls

    return decorator


def activity_of_handler(
    domain: Optional[str] = None,
    tags: Optional[List[str]] = None
):
    """Activity 注册装饰器

    将 activity 函数注册到指定域。

    Args:
        domain: 域名，如 "user"，不填则从模块路径推断
        tags: 标签列表，用于过滤，如 ["email", "external-api"]

    Example:
        @activity.defn
        @activity_of_handler()  # 自动推断 domain
        async def send_welcome_email_activity(data: dict):
            ...

        @activity.defn
        @activity_of_handler(tags=["email"])
        async def send_welcome_email_activity(data: dict):
            ...
    """
    def decorator(func: Callable) -> Callable:
        inferred_domain = domain or _infer_domain_from_module(func.__module__)
        tag_list = tags or []

        _ACTIVITY_REGISTRY.append((func, inferred_domain, tag_list))

        logger.debug(
            f"Registered activity: {func.__name__} "
            f"(domain={inferred_domain}, tags={tag_list})"
        )

        return func

    return decorator


# ============ 发现入口 ============

def autodiscover(packages: Optional[List[str]] = None) -> Tuple[Dict, List]:
    """自动发现并导入所有 workflow 和 activity

    扫描指定包列表下的 workflows.py 和 activities.py 文件，
    触发装饰器注册。

    Args:
        packages: 要扫描的包列表，如 ['app.user.event_handler', 'app.blob.event_handler']
                  传 None 时自动扫描 app.*.event_handler

    Returns:
        (workflow_mappings, activities) 元组

    Example:
        autodiscover()  # 自动发现所有包
        autodiscover(['app.user.event_handler', 'app.blob.event_handler'])
    """
    if packages is None:
        packages = _discover_event_handler_packages()

    logger.info(f"Starting autodiscovery for packages: {packages}")

    for package_name in packages:
        try:
            workflows_module = f"{package_name}.workflows"
            try:
                importlib.import_module(workflows_module)
                logger.debug(f"Imported {workflows_module}")
            except ImportError as e:
                logger.debug(f"Skip {workflows_module}: {e}")

            signals_module = f"{package_name}.signals"
            try:
                importlib.import_module(signals_module)
                logger.debug(f"Imported {signals_module}")
            except ImportError as e:
                logger.debug(f"Skip {signals_module}: {e}")

            activities_module = f"{package_name}.activities"
            try:
                importlib.import_module(activities_module)
                logger.debug(f"Imported {activities_module}")
            except ImportError as e:
                logger.debug(f"Skip {activities_module}: {e}")

        except Exception as e:
            logger.warning(f"Error discovering package {package_name}: {e}")

    logger.info(
        f"Autodiscovery complete: {len(_WORKFLOW_REGISTRY)} workflow event types, "
        f"{sum(len(v) for v in _WORKFLOW_REGISTRY.values())} workflows, "
        f"{len(_SIGNAL_HANDLER_REGISTRY)} signal event types, "
        f"{sum(len(v) for v in _SIGNAL_HANDLER_REGISTRY.values())} signal handlers, "
        f"{len(_ACTIVITY_REGISTRY)} activities"
    )

    return get_workflow_mappings(), get_all_activities()


def _discover_event_handler_packages() -> List[str]:
    """自动扫描 app 目录下所有 event_handler 包"""
    packages = []

    try:
        import app
        app_path = Path(app.__file__).parent

        for item in app_path.iterdir():
            if item.is_dir() and not item.name.startswith('_'):
                event_handler_path = item / 'event_handler'
                if event_handler_path.is_dir():
                    package_name = f"app.{item.name}.event_handler"
                    packages.append(package_name)
                    logger.debug(f"Discovered package: {package_name}")

    except Exception as e:
        logger.warning(f"Error discovering packages: {e}")

    return packages


# ============ 查询 API ============

def _match_tags(
    item_tags: List[str],
    include_tags: Optional[List[str]] = None,
    exclude_tags: Optional[List[str]] = None,
    require_all_tags: Optional[List[str]] = None,
) -> bool:
    """检查标签是否满足过滤条件

    Args:
        item_tags: 条目自身的标签列表
        include_tags: 包含任意一个即通过（OR）
        exclude_tags: 包含任意一个即排除（OR）
        require_all_tags: 必须全部包含才通过（AND）

    Returns:
        是否通过过滤
    """
    if exclude_tags:
        if any(tag in item_tags for tag in exclude_tags):
            return False

    if require_all_tags:
        if not all(tag in item_tags for tag in require_all_tags):
            return False

    if include_tags:
        if not any(tag in item_tags for tag in include_tags):
            return False

    return True


def get_workflow_mappings(
    include_tags: Optional[List[str]] = None,
    exclude_tags: Optional[List[str]] = None,
    require_all_tags: Optional[List[str]] = None,
    by_queue: Optional[str] = None,
    by_domain: Optional[str] = None,
) -> Dict[str, Any]:
    """获取 workflow 映射（兼容旧格式）

    返回格式：{event_type: (workflow_class, queue)} 或
              {event_type: [(workflow_class1, queue1), ...]}（多 workflow）
    """
    result = {}

    for event_type, workflow_list in _WORKFLOW_REGISTRY.items():
        matched_workflows = []

        for wf_cls, queue, domain, tags in workflow_list:
            if by_queue and queue != by_queue:
                continue
            if by_domain and domain != by_domain:
                continue
            if not _match_tags(tags, include_tags, exclude_tags, require_all_tags):
                continue
            matched_workflows.append((wf_cls, queue))

        if matched_workflows:
            if len(matched_workflows) == 1:
                result[event_type] = matched_workflows[0]
            else:
                result[event_type] = matched_workflows

    return result


def get_all_activities(
    include_tags: Optional[List[str]] = None,
    exclude_tags: Optional[List[str]] = None,
    require_all_tags: Optional[List[str]] = None,
    by_domain: Optional[str] = None,
) -> List[Callable]:
    """获取所有已注册的 activities"""
    result = []

    for activity_func, domain, tags in _ACTIVITY_REGISTRY:
        if by_domain and domain != by_domain:
            continue
        if not _match_tags(tags, include_tags, exclude_tags, require_all_tags):
            continue
        result.append(activity_func)

    return result


def get_workflows_by_queue(
    queue: str,
    include_tags: Optional[List[str]] = None,
    exclude_tags: Optional[List[str]] = None,
) -> List[type]:
    """获取指定队列下的所有 workflow 类"""
    result = []

    for event_type, workflow_list in _WORKFLOW_REGISTRY.items():
        for wf_cls, wf_queue, domain, tags in workflow_list:
            if wf_queue != queue:
                continue
            if not _match_tags(tags, include_tags, exclude_tags):
                continue
            result.append(wf_cls)

    return result


def get_activities_by_domain(
    domain: str,
    include_tags: Optional[List[str]] = None,
    exclude_tags: Optional[List[str]] = None,
) -> List[Callable]:
    """获取指定域下的所有 activities"""
    return get_all_activities(
        include_tags=include_tags,
        exclude_tags=exclude_tags,
        by_domain=domain,
    )


def get_event_handler_map(
    include_tags: Optional[List[str]] = None,
    exclude_tags: Optional[List[str]] = None,
    by_domain: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """获取 Launcher 格式的事件处理映射

    返回格式：{event_type: {"workflow_class": ..., "task_queue": ...}}
    """
    result = {}

    for event_type, workflow_list in _WORKFLOW_REGISTRY.items():
        matched_workflows = []

        for wf_cls, queue, domain, tags in workflow_list:
            if by_domain and domain != by_domain:
                continue
            if not _match_tags(tags, include_tags, exclude_tags):
                continue
            matched_workflows.append({
                "workflow_class": wf_cls,
                "task_queue": queue,
            })

        if matched_workflows:
            if len(matched_workflows) == 1:
                result[event_type] = matched_workflows[0]
            else:
                result[event_type] = matched_workflows

    return result


def get_signal_handler_map(
    include_tags: Optional[List[str]] = None,
    exclude_tags: Optional[List[str]] = None,
    by_domain: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """获取 Signal Launcher 格式的事件处理映射

    返回格式：
    {event_type: {
        "workflow_class": ...,
        "signal_name": ...,
        "workflow_id_resolver": ...,
        "payload_resolver": ...,
    }}
    """
    result = {}

    for event_type, handler_list in _SIGNAL_HANDLER_REGISTRY.items():
        matched_handlers = []

        for workflow_cls, signal_name, workflow_id_resolver, payload_resolver, domain, tags in handler_list:
            if by_domain and domain != by_domain:
                continue
            if not _match_tags(tags, include_tags, exclude_tags):
                continue
            matched_handlers.append(
                {
                    "workflow_class": workflow_cls,
                    "signal_name": signal_name,
                    "workflow_id_resolver": workflow_id_resolver,
                    "payload_resolver": payload_resolver,
                }
            )

        if matched_handlers:
            if len(matched_handlers) == 1:
                result[event_type] = matched_handlers[0]
            else:
                result[event_type] = matched_handlers

    return result


def get_all_task_queues() -> List[str]:
    """获取所有已注册的 task queue 列表"""
    queues = set()
    for workflow_list in _WORKFLOW_REGISTRY.values():
        for _, queue, _, _ in workflow_list:
            queues.add(queue)
    return sorted(queues)


def get_all_domains() -> List[str]:
    """获取所有已注册的域列表"""
    domains = set()

    for workflow_list in _WORKFLOW_REGISTRY.values():
        for _, _, domain, _ in workflow_list:
            domains.add(domain)

    for handler_list in _SIGNAL_HANDLER_REGISTRY.values():
        for _, _, _, _, domain, _ in handler_list:
            domains.add(domain)

    for _, domain, _ in _ACTIVITY_REGISTRY:
        domains.add(domain)

    return sorted(domains)


# ============ 调试工具 ============

def print_registry():
    """打印注册表内容（用于调试）"""
    print("\n=== Workflow Registry ===")
    for event_type, workflow_list in _WORKFLOW_REGISTRY.items():
        print(f"\n{event_type}:")
        for wf_cls, queue, domain, tags in workflow_list:
            print(f"  - {wf_cls.__name__} @ {queue} (domain={domain}, tags={tags})")

    print("\n=== Signal Handler Registry ===")
    for event_type, handler_list in _SIGNAL_HANDLER_REGISTRY.items():
        print(f"\n{event_type}:")
        for wf_cls, signal_name, _, _, domain, tags in handler_list:
            print(f"  - {wf_cls.__name__}.{signal_name} (domain={domain}, tags={tags})")

    print("\n=== Activity Registry ===")
    for activity_func, domain, tags in _ACTIVITY_REGISTRY:
        print(f"  - {activity_func.__name__} (domain={domain}, tags={tags})")

    print(
        f"\nTotal: {sum(len(v) for v in _WORKFLOW_REGISTRY.values())} workflows, "
        f"{sum(len(v) for v in _SIGNAL_HANDLER_REGISTRY.values())} signal handlers, "
        f"{len(_ACTIVITY_REGISTRY)} activities\n"
    )
