[[Japanese/日本語](README.ja.md)]

# `mtaio` - Multi-threaded Async I/O Framework

#### !! `It works on Python3.11+` !!

`mtaio` is a comprehensive asynchronous I/O framework for Python, providing high-level abstractions for building efficient concurrent applications.

## Features

- **Asynchronous Core**
  - Task execution with concurrency control
  - Flexible queue implementations (Priority, LIFO)
  - Latch synchronization primitive

- **Caching**
  - TTL-based caching with multiple eviction policies (LRU, LFU, FIFO)
  - Distributed cache with node replication
  - Automatic cache cleanup and monitoring

- **Data Processing**
  - Observable pattern for reactive data handling
  - Pipeline processing with customizable stages
  - Stream processing with operators

- **Event Handling**
  - Asynchronous event emitter with priority support
  - Channel-based communication
  - Pub/sub pattern implementation

- **Protocol Support**
  - ASGI application framework
  - MQTT client implementation
  - Async IMAP and SMTP clients

- **Resource Management**
  - Rate limiting with token bucket algorithm
  - Concurrency limiting
  - Timeout management
  - Resource monitoring

## Installation

```bash
pip install mtaio
```

## Quick Start

Here's a simple example that demonstrates some core features:

```python
from mtaio import TaskExecutor, RateLimiter, TimeoutManager

async def main():
    # Create a rate-limited task executor
    executor = TaskExecutor()
    limiter = RateLimiter(rate=10.0)  # 10 operations per second

    @limiter.limit
    async def process_item(item):
        # Process with timeout
        async with TimeoutManager(5.0) as tm:
            result = await tm.run(some_operation(item))
            return result

    # Process multiple items concurrently
    items = range(100)
    results = await executor.map(process_item, items, limit=5)

if __name__ == "__main__":
    asyncio.run(main())
```

## Documentation

### Core Components

#### `TaskExecutor`

The `TaskExecutor` provides methods for executing coroutines with concurrency control:

```python
from mtaio import TaskExecutor

async def example():
    executor = TaskExecutor()
    
    # Run multiple coroutines with concurrency limit
    results = await executor.gather(
        coro1(),
        coro2(),
        limit=5
    )
```

#### Caching

`mtaio` provides flexible caching solutions:

```python
from mtaio.cache import TTLCache, DistributedCache

async def cache_example():
    # Simple TTL cache
    cache = TTLCache[str](
        default_ttl=60.0,
        max_size=1000
    )
    
    # Distributed cache
    dist_cache = DistributedCache[str](
        nodes=[
            ('localhost', 5000),
            ('localhost', 5001)
        ]
    )
```

#### Event Handling

The event system supports prioritized event handling:

```python
from mtaio.events import EventEmitter

async def event_example():
    emitter = EventEmitter()

    @emitter.on("user_login")
    async def handle_login(event):
        user = event.data
        print(f"User {user.name} logged in")

    await emitter.emit("user_login", user_data)
```

### Advanced Features

#### Resource Management

Control resource usage with rate limiting and timeouts:

```python
from mtaio.resources import ResourceLimiter

async def resource_example():
    limiter = ResourceLimiter(
        rate=10.0,      # 10 requests per second
        concurrency=5   # Max 5 concurrent executions
    )

    @limiter.limit
    async def limited_operation():
        await process_request()
```

#### Monitoring

Monitor system resources and application performance:

```python
from mtaio.monitoring import ResourceMonitor

async def monitor_example():
    monitor = ResourceMonitor()

    @monitor.on_threshold_exceeded
    async def handle_alert(metric, value, threshold):
        print(f"Alert: {metric} exceeded threshold")

    await monitor.start()
```

## Contributing

We welcome contributions! Please follow these steps to contribute:

1. Fork the repository: [github.com/t3tra-dev/mtaio](https://github.com/mtaio/pyinit).
2. Create a feature branch: `git checkout -b feat/your-feature`.
3. Commit your changes: `git commit -m 'Add a new feature'`.
4. Push to the branch: `git push origin feat/your-feature`.
5. Open a Pull Request.

For any questions or support, feel free to open an issue in the repository's [Issues section](https://github.com/t3tra-dev/mtaio/issues).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
