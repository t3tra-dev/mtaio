# Logging API Reference

The `mtaio.logging` module provides asynchronous logging functionality with support for various handlers and formatters.

## AsyncLogger

The main logging class that provides asynchronous logging capabilities.

### Basic Usage

```python
from mtaio.logging import AsyncLogger, AsyncFileHandler

# Create logger
logger = AsyncLogger("app")

# Add handler
handler = AsyncFileHandler("app.log")
await logger.add_handler(handler)

# Log messages
await logger.info("Application started")
await logger.error("An error occurred", extra={"details": "error info"})
```

### Class Reference

```python
class AsyncLogger:
    def __init__(
        self,
        name: str,
        level: int = logging.NOTSET,
        handlers: Optional[List[AsyncLogHandler]] = None
    ):
        """
        Initialize async logger.

        Args:
            name: Logger name
            level: Minimum log level
            handlers: Optional list of handlers
        """

    async def debug(
        self,
        message: str,
        *,
        exc_info: Optional[tuple] = None,
        stack_info: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log debug message."""

    async def info(self, message: str, **kwargs) -> None:
        """Log info message."""

    async def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""

    async def error(self, message: str, **kwargs) -> None:
        """Log error message."""

    async def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
```

## Handlers

### AsyncFileHandler

File-based log handler with async I/O.

```python
from mtaio.logging import AsyncFileHandler

handler = AsyncFileHandler(
    filename="app.log",
    mode="a",
    encoding="utf-8",
    max_bytes=10_000_000,  # 10MB
    backup_count=5
)

# Add formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
```

### AsyncRotatingFileHandler

File handler with rotation support.

```python
from mtaio.logging import AsyncRotatingFileHandler

handler = AsyncRotatingFileHandler(
    filename="app.log",
    max_bytes=1_000_000,  # 1MB
    backup_count=3,
    encoding="utf-8"
)
```

### AsyncJsonFileHandler

JSON-formatted log file handler.

```python
from mtaio.logging import AsyncJsonFileHandler

handler = AsyncJsonFileHandler(
    filename="app.log.json",
    encoder_cls=json.JSONEncoder
)

# Log entries will be written as JSON
await logger.info(
    "User action",
    extra={
        "user_id": "123",
        "action": "login"
    }
)
```

## Log Records

### LogRecord

Container for log record data.

```python
@dataclass
class LogRecord:
    level: int
    message: str
    timestamp: float
    logger_name: str
    extra: Dict[str, Any]
    exc_info: Optional[tuple] = None
    stack_info: Optional[str] = None

    @property
    def levelname(self) -> str:
        """Get level name."""
        return logging.getLevelName(self.level)
```

## Advanced Features

### Transaction Logging

Group related log messages in a transaction:

```python
async with logger.transaction(exc_level=logging.ERROR):
    # All logs in this block are grouped
    await logger.info("Starting transaction")
    await process_data()
    await logger.info("Transaction complete")
```

### Batch Logging

Log multiple messages efficiently:

```python
messages = [
    "Starting process",
    "Step 1 complete",
    "Step 2 complete",
    "Process finished"
]

await logger.batch(logging.INFO, messages)
```

### Error Logging

Comprehensive error logging with context:

```python
try:
    await operation()
except Exception as e:
    await logger.error(
        "Operation failed",
        exc_info=True,
        extra={
            "operation_id": "123",
            "details": str(e)
        }
    )
```

## Best Practices

### Handler Configuration

```python
async def setup_logging():
    # Create logger
    logger = AsyncLogger("app", level=logging.INFO)
    
    # File handler for all logs
    file_handler = AsyncRotatingFileHandler(
        "app.log",
        max_bytes=10_000_000,
        backup_count=5
    )
    file_handler.setLevel(logging.DEBUG)
    
    # JSON handler for important logs
    json_handler = AsyncJsonFileHandler("important.log.json")
    json_handler.setLevel(logging.ERROR)
    
    # Add handlers
    await logger.add_handler(file_handler)
    await logger.add_handler(json_handler)
    
    return logger
```

### Contextual Logging

```python
class RequestLogger:
    def __init__(self, logger: AsyncLogger):
        self.logger = logger
    
    async def log_request(
        self,
        request_id: str,
        message: str,
        **kwargs
    ) -> None:
        await self.logger.info(
            message,
            extra={
                "request_id": request_id,
                **kwargs
            }
        )
```

### Structured Logging

```python
class StructuredLogger:
    def __init__(self, logger: AsyncLogger):
        self.logger = logger
    
    async def log_event(
        self,
        event_name: str,
        **data: Any
    ) -> None:
        await self.logger.info(
            f"Event: {event_name}",
            extra={
                "event_type": event_name,
                "event_data": data,
                "timestamp": time.time()
            }
        )
```

## Performance Considerations

1. **Batch Processing**
   ```python
   # Efficient batch logging
   async def log_operations(operations: List[str]):
       await logger.batch(
           logging.INFO,
           [f"Operation: {op}" for op in operations]
       )
   ```

2. **Log Level Filtering**
   ```python
   # Set appropriate log levels
   logger.setLevel(logging.INFO)  # Production
   handler.setLevel(logging.ERROR)  # Important errors only
   ```

3. **Async Handler Management**
   ```python
   # Clean up handlers properly
   async def cleanup_logging():
       for handler in logger.handlers:
           await handler.stop()
           await handler.close()
   ```

## Error Handling

```python
from mtaio.exceptions import LoggingError

try:
    await logger.info("Message")
except LoggingError as e:
    print(f"Logging failed: {e}")
    # Fall back to standard logging
    import logging
    logging.error("Fallback log message")
```

## Integration Examples

### Web Application Logging

```python
class WebAppLogger:
    def __init__(self):
        self.logger = AsyncLogger("webapp")
        self.setup_handlers()
    
    async def log_request(self, request, response):
        await self.logger.info(
            f"Request: {request.method} {request.path}",
            extra={
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration": response.duration
            }
        )
```

### Task Monitoring

```python
class TaskLogger:
    def __init__(self, logger: AsyncLogger):
        self.logger = logger
    
    @contextmanager
    async def track_task(self, task_id: str):
        start_time = time.time()
        try:
            await self.logger.info(f"Task {task_id} started")
            yield
            duration = time.time() - start_time
            await self.logger.info(
                f"Task {task_id} completed",
                extra={"duration": duration}
            )
        except Exception as e:
            await self.logger.error(
                f"Task {task_id} failed",
                exc_info=True,
                extra={"duration": time.time() - start_time}
            )
```

## See Also

- [Core API Reference](core.md) for base functionality
- [Exceptions API Reference](exceptions.md) for error handling
- [Examples Repository](https://github.com/t3tra-dev/mtaio/tree/main/examples/logging.py)
