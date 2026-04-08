from typing import Any

import jwt
import pytest

from core.config import config
from core.exceptions import DecodeTokenException, ExpiredTokenException
from core.helpers.token import TokenHelper
from tests.support.token import EXPIRED_TOKEN


@pytest.mark.asyncio
async def test_encode():
    # Given
    payload = {"user_id": 1}

    # When
    sut = TokenHelper.encode(payload=payload)

    # Then
    decoded_token: dict[str, Any] = jwt.decode(
        sut, config.jwt.secret_key, config.jwt.algorithm
    )
    assert decoded_token["user_id"] == 1


@pytest.mark.asyncio
async def test_decode():
    # Given
    token = jwt.encode({"user_id": 1}, config.jwt.secret_key, config.jwt.algorithm)

    # When
    sut = TokenHelper.decode(token=token)

    # Then
    assert sut == {"user_id": 1}


@pytest.mark.asyncio
async def test_decode_expired_decode_error():
    # Given
    token = "invalid"

    # When, Then
    with pytest.raises(DecodeTokenException):
        TokenHelper.decode(token=token)


@pytest.mark.asyncio
async def test_decode_expired_signature_error():
    # Given
    token = EXPIRED_TOKEN

    # When, Then
    with pytest.raises(ExpiredTokenException):
        TokenHelper.decode(token=token)


@pytest.mark.asyncio
async def test_decode_expired_token():
    # Given
    token = EXPIRED_TOKEN

    # When
    sut: dict[str, Any] = TokenHelper.decode_expired_token(token=token)

    # Then
    assert sut["user_id"] == 1


@pytest.mark.asyncio
async def test_decode_expired_token_decode_error():
    # Given
    token = "invalid"

    # When, Then
    with pytest.raises(DecodeTokenException):
        TokenHelper.decode_expired_token(token=token)
