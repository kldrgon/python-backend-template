from datetime import datetime, timedelta, timezone

import jwt

from core.config import config
from core.exceptions import DecodeTokenException, ExpiredTokenException


class TokenHelper:
    @staticmethod
    def encode(payload: dict, expire_period: int = 3600) -> str:
        token = jwt.encode(
            payload={
                **payload,
                "exp": datetime.now(timezone.utc) + timedelta(seconds=expire_period),
            },
            key=config.jwt.secret_key,
            algorithm=config.jwt.algorithm,
        )
        return token

    @staticmethod
    def decode(token: str) -> dict:
        try:
            return jwt.decode(
                token,
                config.jwt.secret_key,
                algorithms=[config.jwt.algorithm],
            )
        except jwt.exceptions.DecodeError:
            raise DecodeTokenException
        except jwt.exceptions.ExpiredSignatureError:
            raise ExpiredTokenException

    @staticmethod
    def decode_expired_token(token: str) -> dict:
        try:
            return jwt.decode(
                token,
                config.jwt.secret_key,
                algorithms=[config.jwt.algorithm],
                options={"verify_exp": False},
            )
        except jwt.exceptions.DecodeError:
            raise DecodeTokenException
