import pytest

from core.helpers.cache.redis_backend import RedisBackend
from core.helpers.redis import get_redis_client

redis_backend = RedisBackend()


@pytest.mark.asyncio
async def test_get_empty():
    # Given
    key = "hide"

    # When
    sut = await redis_backend.get(key=key)

    # Then
    assert sut is None


@pytest.mark.asyncio
async def test_get():
    # Given
    key = "hide"
    await get_redis_client().set(key, 1)

    # When
    sut = await redis_backend.get(key=key)

    # Then
    assert sut == 1
    await get_redis_client().delete(key)


@pytest.mark.asyncio
async def test_set_dict():
    # Given
    data = {"name": "hide"}
    key = "hide"

    # When
    await redis_backend.set(response=data, key=key)

    # Then
    sut: dict[str, str] = await redis_backend.get(key=key)
    assert sut == data
    await get_redis_client().delete(key)


class Test:
    ...


@pytest.mark.asyncio
async def test_set_object():
    # Given
    data = Test()
    key = "hide"

    # When
    await redis_backend.set(response=data, key=key)

    # Then
    sut = await get_redis_client().exists(key)
    assert sut == 1
    await get_redis_client().delete(key)


@pytest.mark.asyncio
async def test_delete_startswith():
    # Given
    await get_redis_client().set("data1", "b")
    await get_redis_client().set("data2", "a")

    # When
    await redis_backend.delete_startswith(value="data")

    # Then
    assert await get_redis_client().get("data1") is None
    assert await get_redis_client().get("data2") is None
