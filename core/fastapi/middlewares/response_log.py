from pydantic import BaseModel, Field, ConfigDict
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class ResponseInfo(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    headers: Headers | None = Field(default=None, title="Response header")
    body: str = Field(default="", title="응답 바디")
    status_code: int | None = Field(default=None, title="Status code")
    is_text: bool = Field(default=True, title="Whether response body is text-like")


class ResponseLogMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        response_info = ResponseInfo()

        async def _logging_send(message: Message) -> None:
            if message.get("type") == "http.response.start":
                response_info.headers = Headers(raw=message.get("headers"))
                response_info.status_code = message.get("status")
                # detect content type to decide whether to decode body
                content_type = response_info.headers.get("content-type", "") if response_info.headers else ""
                is_text_like = content_type.startswith("text/") or "application/json" in content_type or "+json" in content_type
                response_info.is_text = is_text_like
            elif message.get("type") == "http.response.body":
                if body := message.get("body"):
                    if response_info.is_text:
                        # try to honor charset if provided
                        charset = "utf-8"
                        if response_info.headers:
                            ct = response_info.headers.get("content-type", "")
                            if "charset=" in ct:
                                try:
                                    charset = ct.split("charset=")[-1].split(";")[0].strip()
                                except Exception:
                                    charset = "utf-8"
                        try:
                            response_info.body += body.decode(charset, errors="replace")
                        except Exception:
                            response_info.body += body.decode("utf-8", errors="replace")
                    else:
                        if not response_info.body:
                            response_info.body = "[binary body omitted]"

            await send(message)

        await self.app(scope, receive, _logging_send)
