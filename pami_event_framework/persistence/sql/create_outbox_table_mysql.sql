-- MySQL Outbox表创建脚本

CREATE TABLE IF NOT EXISTS outbox_events (
    event_id VARCHAR(36) PRIMARY KEY COMMENT '事件ID',
    event_type VARCHAR(100) NOT NULL COMMENT '事件类型',
    event_data TEXT NOT NULL COMMENT '事件数据JSON',
    aggregate_id VARCHAR(36) NOT NULL COMMENT '聚合根ID',
    aggregate_type VARCHAR(50) NOT NULL COMMENT '聚合根类型',
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING' COMMENT '状态: PENDING/PUBLISHED/FAILED',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    last_error TEXT COMMENT '最后一次错误信息',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    published_at DATETIME DEFAULT NULL COMMENT '发布时间',
    INDEX idx_status_created (status, created_at),
    INDEX idx_aggregate (aggregate_type, aggregate_id),
    INDEX idx_event_type (event_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Outbox事件表，用于保证事件至少被发送一次';
