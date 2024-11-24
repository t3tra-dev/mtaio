# Monitoring API Reference

The `mtaio.monitoring` module provides tools for monitoring system resources, application metrics, and performance profiling.

## ResourceMonitor

### Basic Usage

```python
from mtaio.monitoring import ResourceMonitor

# Create monitor
monitor = ResourceMonitor(interval=1.0)  # 1 second interval

# Set up alert handlers
@monitor.on_threshold_exceeded
async def handle_alert(metric: str, value: float, threshold: float):
    print(f"Alert: {metric} exceeded threshold ({value} > {threshold})")

# Configure thresholds
monitor.set_threshold("cpu_usage", 80.0)  # 80% CPU usage
monitor.set_threshold("memory_usage", 90.0)  # 90% memory usage

# Start monitoring
await monitor.start()
```

### Class Reference

```python
class ResourceMonitor:
    def __init__(
        self,
        interval: float = 1.0,
        history_size: int = 3600
    ):
        """
        Initialize resource monitor.

        Args:
            interval: Monitoring interval in seconds
            history_size: Number of historical stats to keep
        """

    async def start(self) -> None:
        """Start monitoring."""

    async def stop(self) -> None:
        """Stop monitoring."""

    def set_threshold(
        self,
        metric: str,
        value: float
    ) -> None:
        """Set threshold for metric."""

    async def get_current_stats(self) -> SystemStats:
        """Get current system statistics."""
```

## System Statistics

### SystemStats

Container for system statistics data.

```python
@dataclass
class SystemStats:
    timestamp: float
    cpu: CPUStats
    memory: MemoryStats
    io: IOStats

@dataclass
class CPUStats:
    usage_percent: float
    load_average: List[float]
    thread_count: int

@dataclass
class MemoryStats:
    total: int
    available: int
    used: int
    percent: float

@dataclass
class IOStats:
    read_bytes: int
    write_bytes: int
    read_count: int
    write_count: int
```

## Profiler

### Basic Usage

```python
from mtaio.monitoring import Profiler

# Create profiler
profiler = Profiler()

# Profile function execution
@profiler.trace
async def monitored_function():
    await perform_operation()

# Profile code block
async with profiler.trace_context("operation"):
    await perform_operation()

# Get profile data
profile = await profiler.get_profile()
print(f"Total execution time: {profile.total_time:.2f}s")
```

### Class Reference

```python
class Profiler:
    def __init__(
        self,
        enabled: bool = True,
        trace_async_tasks: bool = True,
        collect_stack_trace: bool = False
    ):
        """
        Initialize profiler.

        Args:
            enabled: Whether profiling is enabled
            trace_async_tasks: Whether to trace async tasks
            collect_stack_trace: Whether to collect stack traces
        """

    def trace(
        self,
        func: Optional[Callable[..., Awaitable[T]]] = None,
        *,
        name: Optional[str] = None
    ) -> Callable:
        """Decorator to trace async functions."""
```

## Performance Metrics

### Profile Data

```python
@dataclass
class ProfileTrace:
    name: str
    start_time: float
    end_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    memory_start: int = 0
    memory_end: int = 0

    @property
    def duration(self) -> float:
        """Get operation duration."""
        return self.end_time - self.start_time

    @property
    def memory_delta(self) -> int:
        """Get memory usage delta."""
        return self.memory_end - self.memory_start
```

## Advanced Features

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
            # Update metrics
            stats = await self.get_current_stats()
            
            # Process metrics
            if self.metrics.error_count > 100:
                await self.alert("High error rate detected")
            
            await asyncio.sleep(60)
```

### Performance Profiling

```python
from mtaio.monitoring import Profiler

class PerformanceProfiler:
    def __init__(self):
        self.profiler = Profiler(
            trace_async_tasks=True,
            collect_stack_trace=True
        )
    
    async def profile_operation(self):
        async with self.profiler.trace_context("operation"):
            # Monitor memory usage
            await self.profiler.start_trace(
                "memory_usage",
                metadata={"type": "memory"}
            )
            
            # Perform operation
            await perform_operation()
            
            # Get results
            profile = await self.profiler.get_profile()
            return self.analyze_profile(profile)
```

## Integration Examples

### Web Application Monitoring

```python
class WebAppMonitor:
    def __init__(self):
        self.monitor = ResourceMonitor()
        self.profiler = Profiler()
        
    async def monitor_request(self, request):
        async with self.profiler.trace_context("http_request"):
            start_time = time.time()
            
            try:
                response = await process_request(request)
                duration = time.time() - start_time
                
                await self.monitor.record_metric(
                    "request_duration",
                    duration
                )
                
                return response
                
            except Exception as e:
                await self.monitor.record_metric(
                    "request_error",
                    1.0
                )
                raise
```

### Background Task Monitoring

```python
class TaskMonitor:
    def __init__(self):
        self.monitor = ResourceMonitor()
        
    async def monitor_task(self, task_id: str):
        @self.monitor.on_threshold_exceeded
        async def handle_task_alert(metric, value, threshold):
            await self.notify_admin(
                f"Task {task_id} {metric} exceeded threshold"
            )
        
        while True:
            stats = await self.get_task_stats(task_id)
            await self.monitor.record_metrics({
                "task_memory": stats.memory_usage,
                "task_cpu": stats.cpu_usage
            })
            await asyncio.sleep(1)
```

## Best Practices

### Resource Management

```python
# Proper cleanup
async def cleanup_monitoring():
    monitor = ResourceMonitor()
    try:
        await monitor.start()
        yield monitor
    finally:
        await monitor.stop()
```

### Threshold Configuration

```python
# Configure appropriate thresholds
def configure_thresholds(monitor: ResourceMonitor):
    # System resources
    monitor.set_threshold("cpu_usage", 80.0)
    monitor.set_threshold("memory_usage", 90.0)
    
    # Application metrics
    monitor.set_threshold("error_rate", 5.0)
    monitor.set_threshold("response_time", 1.0)
```

### Performance Optimization

```python
# Efficient metric collection
class OptimizedMonitor(ResourceMonitor):
    def __init__(self):
        super().__init__(interval=5.0)  # Reduce collection frequency
        self._metrics_cache = {}
    
    async def get_metric(self, name: str) -> float:
        if name in self._metrics_cache:
            if time.time() - self._metrics_cache[name]["timestamp"] < 1.0:
                return self._metrics_cache[name]["value"]
        
        value = await self._collect_metric(name)
        self._metrics_cache[name] = {
            "value": value,
            "timestamp": time.time()
        }
        return value
```

## See Also

- [Core API Reference](core.md) for base functionality
- [Events API Reference](events.md) for event handling
- [Logging API Reference](logging.md) for logging integration
- [Examples Repository](https://github.com/t3tra-dev/mtaio/tree/main/examples/monitoring.py)
