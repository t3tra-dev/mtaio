"""
Monitoring examples for mtaio library.

This example demonstrates:
- Resource monitoring
- Performance profiling
- Custom metrics collection
- System statistics
"""

import asyncio
import time
from typing import Dict, Any
from mtaio.monitoring import (
    ResourceMonitor,
    Profiler,
)


async def resource_monitoring_example() -> None:
    """
    Demonstrates basic resource monitoring.
    """
    # Create monitor with 1-second interval
    monitor = ResourceMonitor(interval=1.0)

    # Set up alert handlers
    @monitor.on_threshold_exceeded
    async def handle_alert(metric: str, value: float, threshold: float) -> None:
        print(f"Alert: {metric} exceeded threshold " f"({value:.1f} > {threshold:.1f})")

    # Configure thresholds
    monitor.set_threshold("cpu_usage", 80.0)  # 80% CPU usage
    monitor.set_threshold("memory_usage", 90.0)  # 90% memory usage

    # Start monitoring
    await monitor.start()

    # Simulate some load
    for _ in range(3):
        stats = await monitor.get_current_stats()
        print(f"CPU Usage: {stats.cpu.usage_percent:.1f}%")
        print(f"Memory Usage: {stats.memory.percent:.1f}%")
        await asyncio.sleep(1)

    await monitor.stop()


async def simulate_operation(name: str, duration: float) -> None:
    """
    Simulate time-consuming operation.

    :param name: Operation name
    :param duration: Operation duration in seconds
    """
    await asyncio.sleep(duration)


async def profiling_example() -> None:
    """
    Demonstrates performance profiling.
    """
    profiler = Profiler(trace_async_tasks=True)

    # Profile individual function
    @profiler.trace
    async def operation1() -> None:
        await simulate_operation("op1", 0.5)

    # Profile code block
    async with profiler.trace_context("operation2"):
        await simulate_operation("op2", 0.3)

    # Run profiled operations
    await operation1()
    await asyncio.gather(operation1(), profiler.trace(simulate_operation)("op3", 0.2))

    # Get and display profile
    profile = await profiler.get_profile()
    for trace in profile.traces:
        print(f"Operation: {trace.name}")
        print(f"Duration: {trace.duration:.3f}s")
        if trace.memory_delta > 0:
            print(f"Memory delta: {trace.memory_delta} bytes")


class CustomMetrics:
    """Example of custom metrics collection."""

    def __init__(self):
        """Initialize metrics."""
        self.request_count: int = 0
        self.error_count: int = 0
        self.total_duration: float = 0.0

    @property
    def average_duration(self) -> float:
        """Calculate average request duration."""
        if self.request_count == 0:
            return 0.0
        return self.total_duration / self.request_count


class ApplicationMonitor(ResourceMonitor):
    """
    Custom application monitor implementation.
    """

    def __init__(self):
        """Initialize application monitor."""
        super().__init__()
        self.metrics = CustomMetrics()

    async def record_request(self, duration: float, error: bool = False) -> None:
        """
        Record request metrics.

        :param duration: Request duration in seconds
        :param error: Whether request resulted in error
        """
        self.metrics.request_count += 1
        self.metrics.total_duration += duration
        if error:
            self.metrics.error_count += 1

        # Check thresholds
        error_rate = (
            self.metrics.error_count / self.metrics.request_count
            if self.metrics.request_count > 0
            else 0.0
        )

        if error_rate > 0.1:  # 10% error rate threshold
            await self.alert("high_error_rate", error_rate, "Error rate exceeded 10%")


async def custom_monitoring_example() -> None:
    """
    Demonstrates custom monitoring implementation.
    """
    monitor = ApplicationMonitor()

    # Simulate some requests
    for i in range(5):
        start_time = time.monotonic()
        try:
            if i == 2:  # Simulate error on third request
                raise ValueError("Simulated error")
            await simulate_operation(f"request-{i}", 0.1)
        except Exception:
            await monitor.record_request(time.monotonic() - start_time, error=True)
        else:
            await monitor.record_request(time.monotonic() - start_time)

    # Display metrics
    print(f"Total requests: {monitor.metrics.request_count}")
    print(f"Error count: {monitor.metrics.error_count}")
    print(f"Average duration: {monitor.metrics.average_duration:.3f}s")


class PerformanceMonitor:
    """
    Example of performance monitoring implementation.
    """

    def __init__(self):
        """Initialize performance monitor."""
        self.profiler = Profiler()
        self.thresholds: Dict[str, float] = {}

    def set_threshold(self, operation: str, max_duration: float) -> None:
        """
        Set performance threshold.

        :param operation: Operation name
        :param max_duration: Maximum allowed duration in seconds
        """
        self.thresholds[operation] = max_duration

    async def monitor_operation(
        self, name: str, operation: callable, *args: Any, **kwargs: Any
    ) -> Any:
        """
        Monitor operation performance.

        :param name: Operation name
        :param operation: Operation to monitor
        :param args: Operation arguments
        :param kwargs: Operation keyword arguments
        :return: Operation result
        """
        trace = await self.profiler.start_trace(name)
        try:
            result = await operation(*args, **kwargs)
            return result
        finally:
            await self.profiler.end_trace(trace)
            threshold = self.thresholds.get(name)
            if threshold and trace.duration > threshold:
                print(
                    f"Warning: {name} exceeded threshold "
                    f"({trace.duration:.3f}s > {threshold:.3f}s)"
                )


async def performance_monitoring_example() -> None:
    """
    Demonstrates performance monitoring usage.
    """
    monitor = PerformanceMonitor()

    # Set thresholds
    monitor.set_threshold("fast_operation", 0.2)
    monitor.set_threshold("slow_operation", 0.5)

    # Monitor some operations
    await monitor.monitor_operation("fast_operation", simulate_operation, "fast", 0.1)

    await monitor.monitor_operation(
        "slow_operation", simulate_operation, "slow", 0.6  # This will exceed threshold
    )


async def main() -> None:
    """
    Run all monitoring examples.
    """
    print("=== Resource Monitoring Example ===")
    await resource_monitoring_example()

    print("\n=== Profiling Example ===")
    await profiling_example()

    print("\n=== Custom Monitoring Example ===")
    await custom_monitoring_example()

    print("\n=== Performance Monitoring Example ===")
    await performance_monitoring_example()


if __name__ == "__main__":
    asyncio.run(main())
