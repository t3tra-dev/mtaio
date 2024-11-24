# mtaio Documentation

mtaio (Multi-threaded Async I/O) is a comprehensive Python framework for building efficient asynchronous applications. It provides a robust set of tools and utilities for handling async I/O operations, event processing, caching, monitoring, and more.

## Key Features

- **Async-First Design**: Built from the ground up with Python's `asyncio` for optimal performance
- **Resource Management**: Efficient handling of system resources with built-in rate limiting and timeout controls
- **Event Processing**: Robust event emitter and handler system for building event-driven applications
- **Caching System**: Flexible caching mechanisms including TTL and distributed caching support
- **Protocol Support**: Built-in support for ASGI, MQTT, and mail protocols
- **Monitoring & Profiling**: Comprehensive tools for system monitoring and performance profiling
- **Type Safety**: Full type hints support with mypy compatibility
- **Extensible Architecture**: Easy to extend and customize for your specific needs

## Quick Example

```python
from mtaio.core import TaskExecutor
from mtaio.cache import TTLCache
from mtaio.events import EventEmitter

# Task execution with concurrency control
async with TaskExecutor() as executor:
    results = await executor.gather(
        task1(), 
        task2(),
        limit=5  # Maximum concurrent tasks
    )

# Caching with TTL
cache = TTLCache[str](
    default_ttl=300.0,  # 5 minutes
    max_size=1000
)
await cache.set("key", "value")
value = await cache.get("key")

# Event handling
emitter = EventEmitter()

@emitter.on("user_login")
async def handle_login(event):
    user = event.data
    print(f"User {user.name} logged in")

await emitter.emit("user_login", user_data)
```

## Documentation Structure

This documentation is organized into several sections:

- **[Getting Started](guides/getting-started.md)**: Quick introduction to mtaio
- **[Installation](guides/installation.md)**: Installation instructions and requirements
- **[Basic Usage](guides/basic-usage.md)**: Essential concepts and basic usage patterns
- **[Advanced Usage](guides/advanced-usage.md)**: In-depth guides and advanced features
- **[API Reference](api/cache.md)**: Complete API documentation
- **[Deployment](guides/deployment.md)**: Production deployment guidelines
- **[Troubleshooting](guides/troubleshooting.md)**: Common issues and solutions

## Getting Help

- **GitHub Issues**: Report bugs and request features on our [GitHub repository](https://github.com/t3tra-dev/mtaio)
- **Documentation**: Browse the comprehensive documentation sections listed above
- **Examples**: Check out the [examples directory](https://github.com/t3tra-dev/mtaio/tree/main/examples) in our repository

## Requirements

- Python 3.11 or later
- Operating System: Platform independent

## License

mtaio is released under the MIT License. See the [LICENSE](https://github.com/t3tra-dev/mtaio/blob/main/LICENSE) file for details.
