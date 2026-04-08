"""
全局测试配置：仅做环境变量设置，不初始化任何 DB 相关资源。

- 单测 (unit_tests)            → tests/unit_tests/conftest.py
- 集成测试 (integration_tests) → tests/integration_tests/conftest.py
- 系统测试 (system_tests)      → tests/system_tests/conftest.py

env 文件加载优先级（高 → 低）：
  .env.test   测试专用配置（覆盖 .env 中的同名字段）
  .env        本地开发默认值
"""

import os

import pytest
from dotenv import load_dotenv

# .env.test 优先，override=True 确保覆盖 .env 中同名字段
load_dotenv(".env.test", override=True)
load_dotenv(".env")

os.environ.setdefault("ENV", "test")

# 安全保障：强制数据库名包含 'test'，防止误操作生产库
try:
    from sqlalchemy.engine import make_url, URL

    def _ensure_test_db(url_key: str) -> None:
        raw = os.environ.get(url_key)
        if not raw:
            return
        u = make_url(raw)
        db = u.database or ""
        if db and "test" not in db.lower():
            u2 = URL.create(
                drivername=u.drivername,
                username=u.username,
                password=u.password,
                host=u.host,
                port=u.port,
                database=f"{db}_test",
                query=u.query,
            )
            os.environ[url_key] = u2.render_as_string(hide_password=False)

    _ensure_test_db("DB__WRITER_DB_URL")
    _ensure_test_db("DB__READER_DB_URL")
except Exception:
    pass

