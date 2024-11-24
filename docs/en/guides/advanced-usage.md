# Advanced Usage

This guide covers advanced features and patterns in mtaio for building sophisticated asynchronous applications.

## Advanced Event Patterns

### Event Pipelines

Combine events with data pipelines for complex workflows:

```python
from mtaio.events import EventEmitter
from mtaio.data import Pipeline, Stage

class ValidationStage(Stage[dict, dict]):
    async def process(self, data: dict) -> dict:
        if "user_id" not in data:
            raise ValueError("Missing user_id")
        return data

class EnrichmentStage(Stage[dict, dict]):
    async def process(self, data: dict) -> dict:
        data["timestamp"] = time.time()
        return data

async def setup_event_pipeline():
    pipeline = Pipeline()
    emitter = EventEmitter()
    
    # Configure pipeline
    pipeline.add_stage(ValidationStage())
    pipeline.add_stage(EnrichmentStage())
    
    @emitter.on("user_action")
    async def handle_user_action(event):
        async with pipeline:
            processed_data = await pipeline.process(event.data)
            await emitter.emit("processed_action", processed_data)

    return emitter
```

### Event Filtering and Transformation

```python
from mtaio.events import EventEmitter, Event

async def setup_event_processing():
    emitter = EventEmitter()
    
    # Filter events
    filtered = emitter.filter(
        lambda event: event.data.get("priority") == "high"
    )
    
    # Transform events
    transformed = emitter.map(
        lambda event: Event(
            event.name,
            {**event.data, "processed": True}
        )
    )
    
    # Chain multiple emitters
    emitter.pipe(filtered)
    filtered.pipe(transformed)
```

## Advanced Caching Strategies

### Cache Layering

Implement multi-level caching for optimal performance:

```python
from mtaio.cache import TTLCache, DistributedCache
from typing import Optional, TypeVar, Generic

T = TypeVar("T")

class LayeredCache(Generic[T]):
    def __init__(self):
        self.local = TTLCache[T](default_ttl=60.0)  # 1 minute local cache
        self.distributed = DistributedCache[T]([
            ("localhost", 5000),
            ("localhost", 5001)
        ])
    
    async def get(self, key: str) -> Optional[T]:
        # Try local cache first
        value = await self.local.get(key)
        if value is not None:
            return value
        
        # Try distributed cache
        value = await self.distributed.get(key)
        if value is not None:
            # Update local cache
            await self.local.set(key, value)
            return value
        
        return None
    
    async def set(self, key: str, value: T) -> None:
        # Update both caches
        await self.local.set(key, value)
        await self.distributed.set(key, value)
```

### Cache Invalidation Patterns

```python
from mtaio.cache import TTLCache
from mtaio.events import EventEmitter

class CacheInvalidator:
    def __init__(self):
        self.cache = TTLCache[str]()
        self.emitter = EventEmitter()
        
        @self.emitter.on("data_updated")
        async def invalidate_cache(event):
            keys = event.data.get("affected_keys", [])
            for key in keys:
                await self.cache.delete(key)
            
            if event.data.get("clear_all", False):
                await self.cache.clear()
    
    async def update_data(self, key: str, value: str) -> None:
        await self.cache.set(key, value)
        await self.emitter.emit("data_updated", {
            "affected_keys": [key]
        })
```

## Advanced Resource Management

### Custom Resource Limiters

Create specialized resource limiters for specific needs:

```python
from mtaio.resources import ResourceLimiter
from mtaio.typing import AsyncFunc
from typing import Dict

class AdaptiveRateLimiter(ResourceLimiter):
    def __init__(self):
        self.rates: Dict[str, float] = {}
        self._current_load = 0.0
    
    async def acquire(self, resource_id: str) -> None:
        rate = self.rates.get(resource_id, 1.0)
        if self._current_load > 0.8:  # 80% load
            rate *= 0.5  # Reduce rate
        await super().acquire(tokens=1/rate)
    
    def adjust_rate(self, resource_id: str, load: float) -> None:
        self._current_load = load
        if load > 0.9:  # High load
            self.rates[resource_id] *= 0.8
        elif load < 0.5:  # Low load
            self.rates[resource_id] *= 1.2
```

### Complex Timeout Patterns

```python
from mtaio.resources import TimeoutManager
from contextlib import asynccontextmanager

class TimeoutController:
    def __init__(self):
        self.timeouts = TimeoutManager()
    
    @asynccontextmanager
    async def cascading_timeout(self, timeouts: list[float]):
        """Implements cascading timeouts with fallback behavior"""
        for timeout in timeouts:
            try:
                async with self.timeouts.timeout(timeout):
                    yield
                break
            except TimeoutError:
                if timeout == timeouts[-1]:
                    raise
                continue
```

## Advanced Data Processing

### Custom Pipeline Stages

Create specialized pipeline stages for complex data transformations:

```python
from mtaio.data import Pipeline, Stage
from typing import Any, AsyncIterator

class BatchProcessingStage(Stage[Any, Any]):
    def __init__(self, batch_size: int):
        self.batch_size = batch_size
        self.batch = []
    
    async def process(self, item: Any) -> AsyncIterator[Any]:
        self.batch.append(item)
        
        if len(self.batch) >= self.batch_size:
            result = await self._process_batch(self.batch)
            self.batch = []
            return result
    
    async def _process_batch(self, batch: list[Any]) -> Any:
        # Implement batch processing logic
        return batch
```

### Stream Processing

Implement complex stream processing patterns:

```python
from mtaio.data import Stream
from typing import TypeVar, AsyncIterator

T = TypeVar("T")

class StreamProcessor(Stream[T]):
    async def window(
        self,
        size: int,
        slide: int = 1
    ) -> AsyncIterator[list[T]]:
        """Sliding window implementation"""
        buffer: list[T] = []
        
        async for item in self:
            buffer.append(item)
            if len(buffer) >= size:
                yield buffer[-size:]
                buffer = buffer[slide:]
    
    async def batch_by_time(
        self,
        seconds: float
    ) -> AsyncIterator[list[T]]:
        """Time-based batching"""
        batch: list[T] = []
        start_time = time.monotonic()
        
        async for item in self:
            batch.append(item)
            if time.monotonic() - start_time >= seconds:
                yield batch
                batch = []
                start_time = time.monotonic()
```

## Advanced Monitoring

### Custom Metrics Collection

```python
from mtaio.monitoring import ResourceMonitor
from dataclasses import dataclass

@dataclass
class CustomMetrics:
    request_count: int = 0
    error_count: int = 0
    average_response_time: float = 0.0

class ApplicationMonitor(ResourceMonitor):
    def __init__(self):
        super().__init__()
        self.metrics = CustomMetrics()
    
    async def collect_metrics(self) -> None:
        while True:
            stats = await self.get_current_stats()
            
            # Update custom metrics
            self.metrics.average_response_time = (
                stats.latency_sum / stats.request_count
                if stats.request_count > 0 else 0.0
            )
            
            # Emit alerts if needed
            if self.metrics.error_count > 100:
                await self.alert("High error rate detected")
            
            await asyncio.sleep(60)  # Collect every minute
```

## Production Best Practices

### Error Recovery

```python
from mtaio.core import TaskExecutor
from mtaio.exceptions import MTAIOError

class ResilientExecutor:
    def __init__(self):
        self.executor = TaskExecutor()
        self.retry_count = 3
    
    async def execute_with_recovery(
        self,
        func: AsyncFunc[T],
        *args: Any,
        **kwargs: Any
    ) -> T:
        for attempt in range(self.retry_count):
            try:
                return await self.executor.run(
                    func(*args, **kwargs)
                )
            except MTAIOError as e:
                if attempt == self.retry_count - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### Resource Cleanup

```python
from mtaio.resources import ResourceManager
from typing import AsyncIterator

class ManagedResources:
    def __init__(self):
        self.resources: list[AsyncCloseable] = []
    
    async def acquire(self, resource: AsyncCloseable) -> None:
        self.resources.append(resource)
    
    async def cleanup(self) -> None:
        while self.resources:
            resource = self.resources.pop()
            await resource.close()
    
    @asynccontextmanager
    async def resource_scope(self) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await self.cleanup()
```

## Next Steps

- Check out our [Example Applications](https://github.com/t3tra-dev/mtaio/tree/main/examples)
- Review the [API Reference](../api/index.md)
- Join our [Community Discussions](https://github.com/t3tra-dev/mtaio/discussions)
