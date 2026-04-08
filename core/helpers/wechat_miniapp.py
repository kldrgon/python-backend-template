from __future__ import annotations

from typing import Any

import httpx
import base64
import json
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding


class WechatMiniappApiError(RuntimeError):
    def __init__(self, message: str, *, errcode: int | None = None, raw: dict | None = None):
        super().__init__(message)
        self.errcode = errcode
        self.raw = raw or {}


async def wechat_jscode2session(*, appid: str, secret: str, js_code: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            "https://api.weixin.qq.com/sns/jscode2session",
            params={
                "appid": appid,
                "secret": secret,
                "js_code": js_code,
                "grant_type": "authorization_code",
            },
        )
        data = r.json()
    if int(data.get("errcode") or 0) != 0:
        raise WechatMiniappApiError(
            data.get("errmsg") or "jscode2session failed",
            errcode=int(data.get("errcode") or 0),
            raw=data,
        )
    return data


async def wechat_access_token(*, appid: str, secret: str) -> str:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            "https://api.weixin.qq.com/cgi-bin/token",
            params={
                "grant_type": "client_credential",
                "appid": appid,
                "secret": secret,
            },
        )
        data = r.json()
    if int(data.get("errcode") or 0) != 0:
        raise WechatMiniappApiError(
            data.get("errmsg") or "get access_token failed",
            errcode=int(data.get("errcode") or 0),
            raw=data,
        )
    token = data.get("access_token")
    if not token:
        raise WechatMiniappApiError("missing access_token", raw=data)
    return str(token)


async def wechat_get_user_phone_number(*, access_token: str, phone_code: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            "https://api.weixin.qq.com/wxa/business/getuserphonenumber",
            params={"access_token": access_token},
            json={"code": phone_code},
        )
        data = r.json()
    if int(data.get("errcode") or 0) != 0:
        raise WechatMiniappApiError(
            data.get("errmsg") or "getuserphonenumber failed",
            errcode=int(data.get("errcode") or 0),
            raw=data,
        )
    return data


class WechatCrypto:
    """微信小程序数据解密工具（encryptedData + iv + session_key）"""

    def __init__(self, session_key: str, iv: str):
        self.session_key = base64.b64decode(session_key)
        self.iv = base64.b64decode(iv)

    def decrypt_to_dict(self, encrypted_data: str) -> dict:
        encrypted_bytes = base64.b64decode(encrypted_data)
        cipher = Cipher(
            algorithms.AES(self.session_key),
            modes.CBC(self.iv),
            backend=default_backend(),
        )
        decryptor = cipher.decryptor()
        decrypted_bytes = decryptor.update(encrypted_bytes) + decryptor.finalize()

        unpadder = padding.PKCS7(128).unpadder()
        unpadded_bytes = unpadder.update(decrypted_bytes) + unpadder.finalize()
        decrypted_str = unpadded_bytes.decode("utf-8")
        return json.loads(decrypted_str)


def decrypt_phone_number(*, session_key: str, encrypted_data: str, iv: str) -> dict[str, Any]:
    pc = WechatCrypto(session_key=session_key, iv=iv)
    phone_info = pc.decrypt_to_dict(encrypted_data)
    return phone_info

