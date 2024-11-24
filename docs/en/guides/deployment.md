# Deployment Guide

This guide covers best practices and considerations for deploying mtaio applications in production environments.

## Environment Setup

### System Requirements

- Python 3.11 or later
- Operating System: Any platform that supports Python (Linux, macOS, Windows)
- Memory: Depends on workload, recommended minimum 512MB
- CPU: At least 1 core, recommended 2+ cores for concurrent operations

### Environment Variables

Configure your application using environment variables:

```python
import os
from mtaio.core import TaskExecutor
from mtaio.cache import TTLCache

# Configuration from environment
config = {
    "max_workers": int(os.getenv("MTAIO_MAX_WORKERS", "4")),
    "cache_ttl": float(os.getenv("MTAIO_CACHE_TTL", "300")),
    "cache_size": int(os.getenv("MTAIO_CACHE_SIZE", "1000")),
    "log_level": os.getenv("MTAIO_LOG_LEVEL", "INFO"),
}

# Initialize components with configuration
executor = TaskExecutor(max_workers=config["max_workers"])
cache = TTLCache[str](
    default_ttl=config["cache_ttl"],
    max_size=config["cache_size"]
)
```

## Production Configuration

### Logging Setup

Configure logging for production:

```python
import logging
from mtaio.logging import AsyncFileHandler

async def setup_logging():
    logger = logging.getLogger("mtaio")
    logger.setLevel(logging.INFO)
    
    # File handler with rotation
    handler = AsyncFileHandler(
        filename="app.log",
        max_bytes=10_000_000,  # 10MB
        backup_count=5
    )
    
    # Add formatting
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
```

### Resource Management

Configure resource limits for production:

```python
from mtaio.resources import (
    RateLimiter,
    ConcurrencyLimiter,
    TimeoutManager
)

async def configure_resources():
    # Rate limiting
    rate_limiter = RateLimiter(
        rate=float(os.getenv("MTAIO_RATE_LIMIT", "100")),  # requests per second
        burst=int(os.getenv("MTAIO_BURST_LIMIT", "200"))
    )
    
    # Concurrency limiting
    concurrency_limiter = ConcurrencyLimiter(
        limit=int(os.getenv("MTAIO_CONCURRENCY_LIMIT", "50"))
    )
    
    # Timeout management
    timeout_manager = TimeoutManager(
        default_timeout=float(os.getenv("MTAIO_DEFAULT_TIMEOUT", "30"))
    )
    
    return rate_limiter, concurrency_limiter, timeout_manager
```

## Health Monitoring

Implement health checks and monitoring:

```python
from mtaio.monitoring import ResourceMonitor
from mtaio.events import EventEmitter

class HealthMonitor:
    def __init__(self):
        self.monitor = ResourceMonitor()
        self.emitter = EventEmitter()
        
    async def start(self):
        # Configure monitoring thresholds
        self.monitor.set_threshold("cpu_usage", 80.0)  # 80% CPU
        self.monitor.set_threshold("memory_usage", 90.0)  # 90% memory
        
        @self.monitor.on_threshold_exceeded
        async def handle_threshold(metric, value, threshold):
            await self.emitter.emit("health_alert", {
                "metric": metric,
                "value": value,
                "threshold": threshold
            })
        
        await self.monitor.start()
    
    async def get_health_status(self) -> dict:
        stats = await self.monitor.get_current_stats()
        return {
            "status": "healthy" if stats.cpu.usage_percent < 80 else "degraded",
            "cpu_usage": stats.cpu.usage_percent,
            "memory_usage": stats.memory.percent,
            "uptime": stats.uptime
        }
```

## Error Handling

Implement comprehensive error handling:

```python
from mtaio.exceptions import MTAIOError
from typing import Optional

class ErrorHandler:
    def __init__(self):
        self.logger = logging.getLogger("mtaio.errors")
    
    async def handle_error(
        self,
        error: Exception,
        context: Optional[dict] = None
    ) -> None:
        if isinstance(error, MTAIOError):
            # Handle mtaio-specific errors
            await self._handle_mtaio_error(error, context)
        else:
            # Handle unexpected errors
            await self._handle_unexpected_error(error, context)
    
    async def _handle_mtaio_error(
        self,
        error: MTAIOError,
        context: Optional[dict]
    ) -> None:
        self.logger.error(
            "mtaio error occurred",
            extra={
                "error_type": type(error).__name__,
                "message": str(error),
                "context": context
            }
        )
    
    async def _handle_unexpected_error(
        self,
        error: Exception,
        context: Optional[dict]
    ) -> None:
        self.logger.critical(
            "Unexpected error occurred",
            exc_info=error,
            extra={"context": context}
        )
```

## Deployment Example

Complete deployment setup example:

```python
import asyncio
from contextlib import AsyncExitStack

async def main():
    # Initialize exit stack for resource cleanup
    async with AsyncExitStack() as stack:
        # Setup logging
        await setup_logging()
        logger = logging.getLogger("mtaio")
        
        try:
            # Configure resources
            rate_limiter, concurrency_limiter, timeout_manager = (
                await configure_resources()
            )
            
            # Setup health monitoring
            health_monitor = HealthMonitor()
            await stack.enter_async_context(health_monitor)
            
            # Setup error handling
            error_handler = ErrorHandler()
            
            # Initialize application components
            app = Application(
                rate_limiter=rate_limiter,
                concurrency_limiter=concurrency_limiter,
                timeout_manager=timeout_manager,
                error_handler=error_handler
            )
            
            # Start application
            await app.start()
            logger.info("Application started successfully")
            
            # Wait for shutdown signal
            await asyncio.Event().wait()
            
        except Exception as e:
            logger.critical("Failed to start application", exc_info=e)
            raise

if __name__ == "__main__":
    asyncio.run(main())
```

## Deployment Checklist

Before deploying to production:

1. **Configuration**
    - ✓ Environment variables set correctly
    - ✓ Resource limits configured appropriately
    - ✓ Logging configured with proper levels and rotation

2. **Monitoring**
    - ✓ Health checks implemented
    - ✓ Metrics collection configured
    - ✓ Alert thresholds set

3. **Error Handling**
    - ✓ Comprehensive error handling in place
    - ✓ Error logging configured
    - ✓ Recovery procedures documented

4. **Performance**
    - ✓ Cache settings optimized
    - ✓ Resource limits tuned
    - ✓ Concurrent operation limits set

5. **Security**
    - ✓ Sensitive data properly secured
    - ✓ Access controls implemented
    - ✓ Network security configured

## Next Steps

- Monitor your deployment with the [Monitoring Guide](../api/monitoring.md)
- Review [Troubleshooting](troubleshooting.md) for common issues
- Join our [Community Discussions](https://github.com/t3tra-dev/mtaio/discussions) for support
