"""
统一的日志配置模块

使用 Structlog 实现结构化日志：
- 开发环境：彩色输出
- 生产环境：JSON 格式
- 自动集成标准 logging 和 structlog
"""
import logging
import sys

import structlog
from structlog.types import EventDict, Processor

from core.config import config


def drop_color_message_key(_, __, event_dict: EventDict) -> EventDict:
    """移除 uvicorn 的 color_message 字段"""
    event_dict.pop("color_message", None)
    return event_dict


def setup_logging(json_logs: bool = False, log_level: str = "INFO") -> None:
    """
    配置 Structlog 和标准 logging
    
    Args:
        json_logs: 是否输出 JSON 格式（生产环境）
        log_level: 日志级别
    """
    timestamper = structlog.processors.TimeStamper(fmt="iso")
    
    # 共享处理器：同时用于 structlog 和 stdlib logging
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,  # 合并上下文变量（request_id等）
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.stdlib.ExtraAdder(),
        drop_color_message_key,
        timestamper,
        structlog.processors.StackInfoRenderer(),
    ]
    
    if json_logs:
        # JSON 格式时才格式化异常（彩色输出时由 ConsoleRenderer 处理）
        shared_processors.append(structlog.processors.format_exc_info)
    
    # 配置 Structlog
    structlog.configure(
        processors=shared_processors + [
            # 准备传递给 ProcessorFormatter
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # 选择输出格式
    log_renderer: structlog.types.Processor
    if json_logs:
        log_renderer = structlog.processors.JSONRenderer()
    else:
        log_renderer = structlog.dev.ConsoleRenderer()
    
    # 配置标准 logging 的格式化器
    formatter = structlog.stdlib.ProcessorFormatter(
        # 处理非 structlog 的日志（如第三方库）
        foreign_pre_chain=shared_processors,
        # 最终处理所有日志
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            log_renderer,
        ],
    )
    
    # 配置 root logger
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.handlers.clear()  # 清除已有 handler（避免重复）
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level.upper())
    
    # 配置 uvicorn 日志
    for log_name in ["uvicorn", "uvicorn.error"]:
        uvicorn_logger = logging.getLogger(log_name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
    
    # 禁用 uvicorn.access（由我们的中间件记录）
    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.access").propagate = False
    
    # 配置全局异常捕获
    def handle_exception(exc_type, exc_value, exc_traceback):
        """捕获未处理的异常并记录"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        root_logger.error(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
    
    sys.excepthook = handle_exception


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """获取 structlog BoundLogger"""
    return structlog.get_logger(name)


# 初始化日志系统
_json_logs = config.app.env == "prod" or config.app.log_json_format
_log_level = config.app.log_level
setup_logging(json_logs=_json_logs, log_level=_log_level)

# 预定义常用 logger（保留供已有代码引用，推荐各模块自行 structlog.get_logger(__name__)）
events_logger = get_logger("events")
consumer_logger = get_logger("events.consumer")
publisher_logger = get_logger("events.publisher")
api_logger = get_logger("api")
