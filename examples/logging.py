"""
Logging examples for mtaio library.

This example demonstrates:
- Async logger setup and usage
- Different log handlers
- Structured logging
- Log rotation
"""

import asyncio
from typing import Dict, Any, Optional
from mtaio.logging import (
    AsyncLogger,
    AsyncFileHandler,
    AsyncRotatingFileHandler,
    AsyncJsonFileHandler,
)


async def basic_logging_example() -> None:
    """
    Demonstrates basic async logging setup and usage.
    """
    # Create logger
    logger = AsyncLogger("app")

    # Add console handler
    handler = AsyncFileHandler("app.log")
    await logger.add_handler(handler)

    # Log different levels
    await logger.debug("Debug message")
    await logger.info("Information message")
    await logger.warning("Warning message")
    await logger.error("Error message")
    await logger.critical("Critical message")

    # Log with extra context
    await logger.info(
        "User action",
        extra={"user_id": "user123", "action": "login", "ip": "127.0.0.1"},
    )


class StructuredLogger:
    """
    Example of structured logging implementation.
    """

    def __init__(self, name: str):
        """
        Initialize structured logger.

        :param name: Logger name
        """
        self.logger = AsyncLogger(name)
        self.setup_handlers()

    async def setup_handlers(self) -> None:
        """Set up log handlers."""
        # JSON handler for structured logging
        json_handler = AsyncJsonFileHandler("structured.log.json")
        await self.logger.add_handler(json_handler)

    async def log_event(
        self, event_type: str, message: str, data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log structured event.

        :param event_type: Type of event
        :param message: Event message
        :param data: Additional event data
        """
        await self.logger.info(
            message, extra={"event_type": event_type, "event_data": data or {}}
        )


async def structured_logging_example() -> None:
    """
    Demonstrates structured logging usage.
    """
    logger = StructuredLogger("structured")

    # Log different types of events
    await logger.log_event(
        "user_login",
        "User logged in",
        {"user_id": "user123", "ip": "127.0.0.1", "device": "mobile"},
    )

    await logger.log_event(
        "api_request",
        "API request processed",
        {"method": "GET", "path": "/api/users", "status": 200, "duration_ms": 45},
    )


async def rotating_logs_example() -> None:
    """
    Demonstrates log rotation functionality.
    """
    logger = AsyncLogger("rotating")

    # Add rotating file handler
    handler = AsyncRotatingFileHandler(
        "rotating.log",
        max_bytes=1024,  # Rotate at 1KB
        backup_count=3,  # Keep 3 backup files
    )
    await logger.add_handler(handler)

    # Generate some log entries
    for i in range(100):
        await logger.info(f"Log entry {i}: " + "x" * 20)


class RequestLogger:
    """
    Example of context-aware request logger.
    """

    def __init__(self, name: str):
        """
        Initialize request logger.

        :param name: Logger name
        """
        self.logger = AsyncLogger(name)
        self.setup_handlers()

    async def setup_handlers(self) -> None:
        """Set up log handlers."""
        handler = AsyncJsonFileHandler("requests.log.json")
        await self.logger.add_handler(handler)

    async def log_request(
        self, request_id: str, method: str, path: str, **kwargs: Any
    ) -> None:
        """
        Log HTTP request details.

        :param request_id: Request identifier
        :param method: HTTP method
        :param path: Request path
        :param kwargs: Additional request details
        """
        await self.logger.info(
            f"{method} {path}",
            extra={"request_id": request_id, "method": method, "path": path, **kwargs},
        )


async def request_logging_example() -> None:
    """
    Demonstrates request logging usage.
    """
    logger = RequestLogger("requests")

    # Log some example requests
    await logger.log_request(
        request_id="req-123",
        method="GET",
        path="/api/users",
        duration_ms=50,
        status_code=200,
        user_agent="Mozilla/5.0",
    )

    await logger.log_request(
        request_id="req-124",
        method="POST",
        path="/api/users",
        duration_ms=150,
        status_code=201,
        user_agent="curl/7.64.1",
        body_size=1024,
    )


async def main() -> None:
    """
    Run all logging examples.
    """
    print("=== Basic Logging Example ===")
    await basic_logging_example()

    print("\n=== Structured Logging Example ===")
    await structured_logging_example()

    print("\n=== Rotating Logs Example ===")
    await rotating_logs_example()

    print("\n=== Request Logging Example ===")
    await request_logging_example()


if __name__ == "__main__":
    asyncio.run(main())
