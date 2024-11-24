"""
ASGI protocol implementation.

This module provides components for handling ASGI applications:

* ASGIApplication: Base ASGI application class
* Request: ASGI request wrapper
* Response: ASGI response wrapper
* Middleware: ASGI middleware base
"""

from typing import (
    Dict,
    List,
    Optional,
    Any,
    Callable,
    Awaitable,
    Union,
    TypeVar,
    AsyncIterator,
)
from dataclasses import dataclass
import json
import urllib.parse
from enum import Enum
from ..exceptions import ASGIError

T = TypeVar("T")


Scope = TypeVar("Scope", bound=Dict[str, Any])
Message = TypeVar("Message", bound=Dict[str, Any])


class HTTPMethod(str, Enum):
    """HTTP methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    PATCH = "PATCH"
    TRACE = "TRACE"


@dataclass
class Request:
    """
    ASGI request wrapper.

    :param scope: ASGI scope dictionary
    :type scope: Dict[str, Any]
    :param receive: ASGI receive function
    :type receive: Callable[[], Awaitable[Message]]
    """

    scope: Dict[str, Any]
    receive: Callable[[], Awaitable[Message]]
    _body: Optional[bytes] = None

    @property
    def method(self) -> str:
        """Get HTTP method."""
        return self.scope["method"]

    @property
    def path(self) -> str:
        """Get request path."""
        return self.scope["path"]

    @property
    def query_string(self) -> bytes:
        """Get raw query string."""
        return self.scope["query_string"]

    @property
    def headers(self) -> Dict[str, str]:
        """Get request headers."""
        return {
            k.decode("latin1"): v.decode("latin1") for k, v in self.scope["headers"]
        }

    @property
    def query_params(self) -> Dict[str, str]:
        """Get parsed query parameters."""
        return dict(urllib.parse.parse_qsl(self.query_string.decode("latin1")))

    async def body(self) -> bytes:
        """Get request body."""
        if self._body is None:
            chunks = []
            more_body = True

            while more_body:
                message = await self.receive()
                chunk = message.get("body", b"")
                chunks.append(chunk)
                more_body = message.get("more_body", False)

            self._body = b"".join(chunks)

        return self._body

    async def json(self) -> Any:
        """Get JSON-decoded body."""
        body = await self.body()
        return json.loads(body)

    async def form(self) -> Dict[str, str]:
        """Get parsed form data."""
        body = await self.body()
        return dict(urllib.parse.parse_qsl(body.decode("latin1")))


class Response:
    """
    ASGI response wrapper.

    :param status_code: HTTP status code
    :type status_code: int
    :param content: Response content
    :type content: Union[str, bytes]
    :param headers: Response headers
    :type headers: Optional[Dict[str, str]]
    """

    def __init__(
        self,
        status_code: int = 200,
        content: Union[str, bytes] = b"",
        headers: Optional[Dict[str, str]] = None,
    ):
        """Initialize the response."""
        self.status_code = status_code
        self.headers = headers or {}

        if isinstance(content, str):
            content = content.encode("utf-8")
            self.headers.setdefault("content-type", "text/plain; charset=utf-8")
        self._content = content

    @classmethod
    def text(
        cls,
        content: str,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ) -> "Response":
        """Create text response."""
        headers = headers or {}
        headers.setdefault("content-type", "text/plain; charset=utf-8")
        return cls(status_code, content, headers)

    @classmethod
    def json(
        cls,
        content: Any,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ) -> "Response":
        """Create JSON response."""
        headers = headers or {}
        headers.setdefault("content-type", "application/json")
        return cls(status_code, json.dumps(content), headers)

    @classmethod
    def html(
        cls,
        content: str,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ) -> "Response":
        """Create HTML response."""
        headers = headers or {}
        headers.setdefault("content-type", "text/html; charset=utf-8")
        return cls(status_code, content, headers)

    @classmethod
    def redirect(
        cls,
        location: str,
        status_code: int = 302,
        headers: Optional[Dict[str, str]] = None,
    ) -> "Response":
        """Create redirect response."""
        headers = headers or {}
        headers["location"] = location
        return cls(status_code, "", headers)

    async def __call__(self, send: Callable[[Message], Awaitable[None]]) -> None:
        """Send the response."""
        headers = [
            (k.lower().encode("latin1"), v.encode("latin1"))
            for k, v in self.headers.items()
        ]

        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": headers,
            }
        )

        await send({"type": "http.response.body", "body": self._content})


class StreamingResponse(Response):
    """
    Streaming response wrapper.

    :param content: Async iterator of response chunks
    :type content: AsyncIterator[Union[str, bytes]]
    :param status_code: HTTP status code
    :type status_code: int
    :param headers: Response headers
    :type headers: Optional[Dict[str, str]]
    """

    def __init__(
        self,
        content: AsyncIterator[Union[str, bytes]],
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ):
        """Initialize the streaming response."""
        super().__init__(status_code, b"", headers)
        self._iterator = content

    async def __call__(self, send: Callable[[Message], Awaitable[None]]) -> None:
        """Send the streaming response."""
        headers = [
            (k.lower().encode("latin1"), v.encode("latin1"))
            for k, v in self.headers.items()
        ]

        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": headers,
            }
        )

        async for chunk in self._iterator:
            if isinstance(chunk, str):
                chunk = chunk.encode("utf-8")

            await send({"type": "http.response.body", "body": chunk, "more_body": True})

        await send({"type": "http.response.body", "body": b"", "more_body": False})


class ASGIMiddleware:
    """
    Base ASGI middleware class.

    :param app: ASGI application to wrap
    :type app: ASGIApplication
    """

    def __init__(self, app: "ASGIApplication"):
        """Initialize the middleware."""
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Callable[[], Awaitable[Message]],
        send: Callable[[Message], Awaitable[None]],
    ) -> None:
        """Process the request."""
        await self.app(scope, receive, send)


class ASGIApplication:
    """
    Base ASGI application class.

    Example::

        class App(ASGIApplication):
            async def handle_request(self, request):
                return Response.text("Hello, World!")

        app = App()
    """

    def __init__(self):
        """Initialize the application."""
        self.middleware: List[ASGIMiddleware] = []

    def add_middleware(self, middleware_class: type, **kwargs: Any) -> None:
        """
        Add middleware to the application.

        :param middleware_class: Middleware class to add
        :type middleware_class: type
        :param kwargs: Middleware initialization parameters
        :type kwargs: Any
        """
        self.middleware.insert(0, middleware_class(self, **kwargs))

    async def __call__(
        self,
        scope: Scope,
        receive: Callable[[], Awaitable[Message]],
        send: Callable[[Message], Awaitable[None]],
    ) -> None:
        """Process the ASGI request."""
        if scope["type"] != "http":
            raise ASGIError(f"Unsupported scope type: {scope['type']}")

        try:
            request = Request(scope, receive)
            response = await self.handle_request(request)
            await response(send)
        except Exception as e:
            await self.handle_error(e, send)

    async def handle_request(self, request: Request) -> Response:
        """
        Handle an HTTP request.

        :param request: Request to handle
        :type request: Request
        :return: Response
        :rtype: Response
        """
        raise NotImplementedError

    async def handle_error(
        self, error: Exception, send: Callable[[Message], Awaitable[None]]
    ) -> None:
        """
        Handle an error.

        :param error: Error that occurred
        :type error: Exception
        :param send: ASGI send function
        :type send: Callable[[Message], Awaitable[None]]
        """
        status_code = getattr(error, "status_code", 500)
        response = Response.json(
            {"error": str(error), "status_code": status_code}, status_code
        )
        await response(send)


class Router:
    """
    URL router for ASGI applications.

    Example::

        router = Router()

        @router.route("/users/{user_id}")
        async def get_user(request, user_id):
            return Response.json({"user_id": user_id})
    """

    def __init__(self):
        """Initialize the router."""
        self.routes: Dict[str, Dict[str, Callable]] = {}

    def route(self, path: str, methods: Optional[List[str]] = None) -> Callable:
        """
        Route decorator.

        :param path: URL path pattern
        :type path: str
        :param methods: Allowed HTTP methods
        :type methods: Optional[List[str]]
        :return: Decorator function
        :rtype: Callable
        """

        def decorator(handler: Callable) -> Callable:
            if path not in self.routes:
                self.routes[path] = {}

            for method in methods or ["GET"]:
                self.routes[path][method] = handler
            return handler

        return decorator

    def url_for(self, name: str, **params: str) -> str:
        """
        Generate URL for named route.

        :param name: Route name
        :type name: str
        :param params: URL parameters
        :type params: str
        :return: Generated URL
        :rtype: str
        """
        for path in self.routes:
            if path == name:
                result = path
                for key, value in params.items():
                    result = result.replace(f"{{{key}}}", value)
                return result
        raise ASGIError(f"Route not found: {name}")

    async def dispatch(self, request: Request, **params: str) -> Response:
        """
        Dispatch request to appropriate handler.

        :param request: Request to dispatch
        :type request: Request
        :param params: URL parameters
        :type params: str
        :return: Handler response
        :rtype: Response
        """
        if request.path in self.routes:
            handlers = self.routes[request.path]
            if request.method in handlers:
                handler = handlers[request.method]
                return await handler(request, **params)

        raise ASGIError(
            f"No handler found for {request.method} {request.path}", status_code=404
        )
