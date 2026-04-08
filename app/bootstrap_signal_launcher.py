"""Signal Launcher Bootstrap - 初始化 Signal Launcher 组件"""

import asyncio
from typing import Any, Dict

import structlog
from temporalio.client import Client as TemporalClient

from pami_event_framework.config import EventFrameworkConfig, LauncherConfig
from pami_event_framework.launcher.signal_launcher import SignalLauncher

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


async def start_signal_launcher(
    config: EventFrameworkConfig,
    launcher_config: LauncherConfig,
    signal_handler_map: Dict[str, Dict[str, Any]],
):
    """启动 Signal Launcher"""
    while True:
        try:
            logger.info("Connecting to Temporal for Signal Launcher...")

            temporal_client = await TemporalClient.connect(
                config.temporal.server_url,
                namespace=config.temporal.namespace,
                tls=config.temporal.tls_config,
            )
            logger.info("Temporal Client connected for Signal Launcher")

            logger.info("Creating Signal Launcher...")
            launcher = SignalLauncher(
                kafka_config=config.kafka,
                temporal_client=temporal_client,
                signal_handler_map=signal_handler_map,
                consumer_group_id=launcher_config.consumer_group_id,
                temporal_config=config.temporal,
            )

            logger.info("signal_launcher_created", event_type_count=len(signal_handler_map))

            logger.info("Starting Signal Launcher...")
            await launcher.start()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("signal_launcher_runtime_error_retrying", error=str(e), exc_info=True)
            await asyncio.sleep(3)
