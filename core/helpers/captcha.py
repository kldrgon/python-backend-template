# -*- coding: utf-8 -*-
"""
验证码服务
提供验证码生成、存储、验证、删除功能
"""
import random
import string
from typing import Optional
import structlog

from core.helpers.redis import get_redis_client

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class CaptchaService:
    """验证码服务"""

    # 验证码过期时间（秒）
    CAPTCHA_EXPIRE_TIME = 300  # 5分钟

    # 验证码长度
    CAPTCHA_LENGTH = 6

    # Redis key 前缀
    REDIS_KEY_PREFIX = "captcha:"

    @staticmethod
    def generate_code() -> str:
        """生成随机验证码（6位数字）"""
        return ''.join(random.choices(string.digits, k=CaptchaService.CAPTCHA_LENGTH))

    @staticmethod
    async def store_code(email: str, code: str) -> bool:
        """
        存储验证码到 Redis

        Args:
            email: 邮箱地址
            code: 验证码

        Returns:
            是否存储成功
        """
        try:
            redis_client = get_redis_client()
            key = f"{CaptchaService.REDIS_KEY_PREFIX}{email}"
            await redis_client.setex(
                key,
                CaptchaService.CAPTCHA_EXPIRE_TIME,
                code
            )
            logger.info("captcha_stored", email=email, expires=CaptchaService.CAPTCHA_EXPIRE_TIME)
            return True
        except Exception as e:
            logger.error("captcha_store_failed", email=email, error=str(e))
            return False

    @staticmethod
    async def verify_code(email: str, code: str, delete: bool = True) -> bool:
        """
        验证验证码

        Args:
            email: 邮箱地址
            code: 待验证的验证码
            delete: 验证成功后是否删除验证码

        Returns:
            验证码是否正确
        """
        try:
            redis_client = get_redis_client()
            key = f"{CaptchaService.REDIS_KEY_PREFIX}{email}"
            stored_code = await redis_client.get(key)

            if stored_code is None:
                logger.warning("captcha_not_found_or_expired", email=email)
                return False

            if isinstance(stored_code, bytes):
                stored_code = stored_code.decode('utf-8')
            stored_code = str(stored_code).strip()
            code = str(code).strip()

            if stored_code == code:
                if delete:
                    await redis_client.delete(key)
                    logger.info("captcha_verified_and_deleted", email=email)
                else:
                    logger.info("captcha_verified_kept", email=email)
                return True
            else:
                logger.warning("captcha_mismatch", email=email)
                return False
        except Exception as e:
            logger.error("captcha_verify_failed", email=email, error=str(e))
            return False

    @staticmethod
    async def delete_code(email: str) -> bool:
        """
        删除验证码

        Args:
            email: 邮箱地址

        Returns:
            是否删除成功
        """
        try:
            redis_client = get_redis_client()
            key = f"{CaptchaService.REDIS_KEY_PREFIX}{email}"
            await redis_client.delete(key)
            logger.info("captcha_manually_deleted", email=email)
            return True
        except Exception as e:
            logger.error("captcha_delete_failed", email=email, error=str(e))
            return False

    @staticmethod
    async def get_remaining_time(email: str) -> Optional[int]:
        """
        获取验证码剩余有效时间（秒）

        Args:
            email: 邮箱地址

        Returns:
            剩余时间（秒），验证码不存在则返回 None
        """
        try:
            redis_client = get_redis_client()
            key = f"{CaptchaService.REDIS_KEY_PREFIX}{email}"
            ttl = await redis_client.ttl(key)
            return ttl if ttl > 0 else None
        except Exception as e:
            logger.error("captcha_get_ttl_failed", email=email, error=str(e))
            return None
