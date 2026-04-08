"""事件框架配置。

模板默认保留 user/blob 两个基础域的 event_handler 自动发现。
"""

EVENT_HANDLER_PACKAGES = [
    "app.user.event_handler",
    "app.blob.event_handler",
]
