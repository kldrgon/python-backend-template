import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock

from pami_event_framework.fastapi import sqlalchemy_middleware as sa_mw
from pami_event_framework.fastapi.sqlalchemy_middleware import SQLAlchemyMiddleware
from starlette.types import Receive, Scope, Send


async def app(scope: Scope, receive: Receive, send: Send) -> None:
    await receive()
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"Content-Type", b"application/json")],
        },
    )
    await send({"type": "http.response.body", "body": b"test"})


async def exception_app(scope: Scope, receive: Receive, send: Send) -> None:
    await receive()
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"Content-Type", b"application/json")],
        },
    )
    await send({"type": "http.response.body", "body": b"test"})
    raise Exception


@pytest.mark.asyncio
@patch.object(sa_mw, "get_session")
async def test_sqlalchemy_middleware(get_session_mock):
    mock_session = AsyncMock()
    get_session_mock.return_value = mock_session

    test_app = SQLAlchemyMiddleware(app=app)

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://127.0.0.1"
    ) as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert mock_session.remove.called


@pytest.mark.asyncio
@patch.object(sa_mw, "get_session")
async def test_sqlalchemy_middleware_exception(get_session_mock):
    mock_session = AsyncMock()
    get_session_mock.return_value = mock_session

    test_app = SQLAlchemyMiddleware(app=exception_app)

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://127.0.0.1"
    ) as client:
        with pytest.raises(Exception):
            response = await client.get("/")
            assert response.status_code == 200
            assert mock_session.remove.called
