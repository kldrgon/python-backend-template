-- PostgreSQL Outbox表创建脚本

CREATE TABLE IF NOT EXISTS outbox_events (
    event_id VARCHAR(36) PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    event_data TEXT NOT NULL,
    aggregate_id VARCHAR(36) NOT NULL,
    aggregate_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    retry_count INTEGER DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP WITH TIME ZONE
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_status_created ON outbox_events(status, created_at);
CREATE INDEX IF NOT EXISTS idx_aggregate ON outbox_events(aggregate_type, aggregate_id);
CREATE INDEX IF NOT EXISTS idx_event_type ON outbox_events(event_type);

-- 注释
COMMENT ON TABLE outbox_events IS 'Outbox事件表，用于保证事件至少被发送一次';
COMMENT ON COLUMN outbox_events.event_id IS '事件ID';
COMMENT ON COLUMN outbox_events.event_type IS '事件类型';
COMMENT ON COLUMN outbox_events.event_data IS '事件数据JSON';
COMMENT ON COLUMN outbox_events.aggregate_id IS '聚合根ID';
COMMENT ON COLUMN outbox_events.aggregate_type IS '聚合根类型';
COMMENT ON COLUMN outbox_events.status IS '状态: PENDING/PUBLISHED/FAILED';
COMMENT ON COLUMN outbox_events.retry_count IS '重试次数';
COMMENT ON COLUMN outbox_events.last_error IS '最后一次错误信息';
COMMENT ON COLUMN outbox_events.created_at IS '创建时间';
COMMENT ON COLUMN outbox_events.published_at IS '发布时间';
