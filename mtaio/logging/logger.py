"""
Asynchronous logging implementation.

This module provides components for asynchronous logging:

* AsyncLogger: Main async logger class
* AsyncLogHandler: Base class for async log handlers
* AsyncFileHandler: Async file logging handler
* AsyncQueueHandler: Async queue-based handler
* AsyncRotatingFileHandler: Async rotating file handler
"""

from typing import Optional, Dict, List, Any, Union, TextIO
from dataclasses import dataclass
import asyncio
import logging
import sys
import os
import time
import json
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager
from ..exceptions import LoggingError


@dataclass
class LogRecord:
    """
    Container for log record data.

    :param level: Log level
    :type level: int
    :param message: Log message
    :type message: str
    :param timestamp: Timestamp of the log
    :type timestamp: float
    :param logger_name: Name of the logger
    :type logger_name: str
    :param extra: Additional log data
    :type extra: Dict[str, Any]
    """

    level: int
    message: str
    timestamp: float
    logger_name: str
    extra: Dict[str, Any]
    exc_info: Optional[tuple] = None
    stack_info: Optional[str] = None

    @property
    def levelname(self) -> str:
        """Get the name of the log level."""
        return logging.getLevelName(self.level)


class AsyncLogHandler:
    """
    Base class for async log handlers.

    :param level: Minimum log level to handle
    :type level: int
    :param formatter: Optional log formatter
    :type formatter: Optional[logging.Formatter]
    """

    def __init__(
        self, level: int = logging.NOTSET, formatter: Optional[logging.Formatter] = None
    ):
        """Initialize the handler."""
        self.level = level
        self.formatter = formatter or logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        self._closed = False
        self._queue: asyncio.Queue[Optional[LogRecord]] = asyncio.Queue()
        self._task: Optional[asyncio.Task] = None

    async def handle(self, record: LogRecord) -> None:
        """
        Handle a log record.

        :param record: Log record to handle
        :type record: LogRecord
        """
        if self._closed or record.level < self.level:
            return
        await self._queue.put(record)

    async def _processor(self) -> None:
        """Process queued log records."""
        while True:
            record = await self._queue.get()
            if record is None:
                break
            try:
                await self._handle(record)
            except Exception as e:
                sys.stderr.write(f"Error in log handler: {str(e)}\n")
            finally:
                self._queue.task_done()

    async def _handle(self, record: LogRecord) -> None:
        """
        Handle a single log record.

        :param record: Log record to handle
        :type record: LogRecord
        """
        raise NotImplementedError

    def start(self) -> None:
        """Start the handler processor."""
        if not self._task:
            self._task = asyncio.create_task(self._processor())

    async def stop(self) -> None:
        """Stop the handler processor."""
        if self._task:
            await self._queue.put(None)
            await self._task
            self._task = None
            self._closed = True


class AsyncFileHandler(AsyncLogHandler):
    """
    Async file log handler.

    :param filename: Path to log file
    :type filename: Union[str, Path]
    :param mode: File open mode
    :type mode: str
    :param encoding: File encoding
    :type encoding: str
    """

    def __init__(
        self,
        filename: Union[str, Path],
        mode: str = "a",
        encoding: str = "utf-8",
        level: int = logging.NOTSET,
        formatter: Optional[logging.Formatter] = None,
    ):
        """Initialize the file handler."""
        super().__init__(level, formatter)
        self.filename = Path(filename)
        self.mode = mode
        self.encoding = encoding
        self.file: Optional[TextIO] = None

    async def _handle(self, record: LogRecord) -> None:
        """Handle a log record by writing to file."""
        if not self.file:
            self.file = open(self.filename, self.mode, encoding=self.encoding)

        try:
            message = self.formatter.format(
                {
                    "levelname": record.levelname,
                    "name": record.logger_name,
                    "message": record.message,
                    "created": record.timestamp,
                    "exc_info": record.exc_info,
                    "stack_info": record.stack_info,
                    **record.extra,
                }
            )
            print(message, file=self.file, flush=True)
        except Exception as e:
            raise LoggingError(f"Error writing to log file: {str(e)}") from e

    async def stop(self) -> None:
        """Stop the handler and close the file."""
        await super().stop()
        if self.file:
            self.file.close()
            self.file = None


class AsyncRotatingFileHandler(AsyncFileHandler):
    """
    Async rotating file handler.

    :param filename: Base filename
    :type filename: Union[str, Path]
    :param max_bytes: Maximum file size in bytes
    :type max_bytes: int
    :param backup_count: Number of backup files to keep
    :type backup_count: int
    """

    def __init__(
        self,
        filename: Union[str, Path],
        max_bytes: int = 0,
        backup_count: int = 0,
        **kwargs: Any,
    ):
        """Initialize the rotating file handler."""
        super().__init__(filename, **kwargs)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self._current_size = 0

    def _rotate(self) -> None:
        """Rotate log files."""
        if self.file:
            self.file.close()
            self.file = None

        for i in range(self.backup_count - 1, 0, -1):
            sfn = f"{self.filename}.{i}"
            dfn = f"{self.filename}.{i + 1}"
            if os.path.exists(sfn):
                if os.path.exists(dfn):
                    os.remove(dfn)
                os.rename(sfn, dfn)

        if os.path.exists(self.filename):
            os.rename(self.filename, f"{self.filename}.1")

        self.file = open(self.filename, self.mode, encoding=self.encoding)
        self._current_size = 0

    async def _handle(self, record: LogRecord) -> None:
        """Handle a log record with rotation."""
        try:
            message = self.formatter.format(
                {
                    "levelname": record.levelname,
                    "name": record.logger_name,
                    "message": record.message,
                    "created": record.timestamp,
                    "exc_info": record.exc_info,
                    "stack_info": record.stack_info,
                    **record.extra,
                }
            )
            message_size = len(message.encode(self.encoding)) + 1

            if (
                self.max_bytes > 0
                and message_size + self._current_size > self.max_bytes
            ):
                self._rotate()

            if not self.file:
                self.file = open(self.filename, self.mode, encoding=self.encoding)

            print(message, file=self.file, flush=True)
            self._current_size += message_size

        except Exception as e:
            raise LoggingError(f"Error writing to rotating log file: {str(e)}") from e


class AsyncLogger:
    """
    Async logger implementation.

    Example::

        logger = AsyncLogger("app")
        handler = AsyncFileHandler("app.log")
        await logger.add_handler(handler)

        await logger.info("Application started")
    """

    def __init__(
        self,
        name: str,
        level: int = logging.NOTSET,
        handlers: Optional[List[AsyncLogHandler]] = None,
    ):
        """
        Initialize the logger.

        :param name: Logger name
        :type name: str
        :param level: Minimum log level
        :type level: int
        :param handlers: Optional list of handlers
        :type handlers: Optional[List[AsyncLogHandler]]
        """
        self.name = name
        self.level = level
        self._handlers = handlers or []
        for handler in self._handlers:
            handler.start()

    async def add_handler(self, handler: AsyncLogHandler) -> None:
        """
        Add a log handler.

        :param handler: Handler to add
        :type handler: AsyncLogHandler
        """
        self._handlers.append(handler)
        handler.start()

    async def remove_handler(self, handler: AsyncLogHandler) -> None:
        """
        Remove a log handler.

        :param handler: Handler to remove
        :type handler: AsyncLogHandler
        """
        if handler in self._handlers:
            await handler.stop()
            self._handlers.remove(handler)

    async def _log(
        self,
        level: int,
        message: str,
        exc_info: Optional[tuple] = None,
        stack_info: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Internal logging method."""
        if level < self.level:
            return

        record = LogRecord(
            level=level,
            message=message,
            timestamp=time.time(),
            logger_name=self.name,
            exc_info=exc_info,
            stack_info=stack_info,
            extra=extra or {},
        )

        for handler in self._handlers:
            await handler.handle(record)

    async def debug(
        self,
        message: str,
        *,
        exc_info: Optional[tuple] = None,
        stack_info: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a debug message."""
        await self._log(logging.DEBUG, message, exc_info, stack_info, extra)

    async def info(
        self,
        message: str,
        *,
        exc_info: Optional[tuple] = None,
        stack_info: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an info message."""
        await self._log(logging.INFO, message, exc_info, stack_info, extra)

    async def warning(
        self,
        message: str,
        *,
        exc_info: Optional[tuple] = None,
        stack_info: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a warning message."""
        await self._log(logging.WARNING, message, exc_info, stack_info, extra)

    async def error(
        self,
        message: str,
        *,
        exc_info: Optional[tuple] = None,
        stack_info: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an error message."""
        await self._log(logging.ERROR, message, exc_info, stack_info, extra)

    async def critical(
        self,
        message: str,
        *,
        exc_info: Optional[tuple] = None,
        stack_info: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a critical message."""
        await self._log(logging.CRITICAL, message, exc_info, stack_info, extra)

    @asynccontextmanager
    async def transaction(self, *, exc_level: int = logging.ERROR):
        """
        Context manager for transaction logging.

        Example::

            async with logger.transaction():
                # All logs in this block will be grouped
                await perform_operation()
        """
        transaction_id = str(time.time())
        try:
            yield
        except Exception as e:
            await self._log(
                exc_level,
                f"Transaction {transaction_id} failed: {str(e)}",
                exc_info=True,
            )
            raise
        else:
            await self._log(
                logging.INFO, f"Transaction {transaction_id} completed successfully"
            )

    async def batch(self, level: int, messages: List[str]) -> None:
        """
        Log multiple messages in batch.

        :param level: Log level for all messages
        :type level: int
        :param messages: List of messages to log
        :type messages: List[str]
        """
        for message in messages:
            await self._log(level, message)

    async def close(self) -> None:
        """Close the logger and all handlers."""
        for handler in self._handlers:
            await handler.stop()
        self._handlers.clear()


class AsyncJsonFileHandler(AsyncFileHandler):
    """
    JSON file log handler.

    Example::

        handler = AsyncJsonFileHandler("app.log.json")
        await logger.add_handler(handler)
    """

    async def _handle(self, record: LogRecord) -> None:
        """Handle a log record by writing JSON."""
        if not self.file:
            self.file = open(self.filename, self.mode, encoding=self.encoding)

        try:
            log_data = {
                "timestamp": datetime.fromtimestamp(record.timestamp).isoformat(),
                "level": record.levelname,
                "logger": record.logger_name,
                "message": record.message,
                **record.extra,
            }

            if record.exc_info:
                log_data["exception"] = {
                    "type": record.exc_info[0].__name__,
                    "message": str(record.exc_info[1]),
                }

            if record.stack_info:
                log_data["stack_info"] = record.stack_info

            json.dump(log_data, self.file)
            print(file=self.file, flush=True)

        except Exception as e:
            raise LoggingError(f"Error writing JSON log: {str(e)}") from e
