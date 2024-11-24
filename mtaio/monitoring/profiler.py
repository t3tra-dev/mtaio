"""
Asynchronous profiler implementation.

This module provides components for profiling async operations:

* Profiler: Main profiler class
* Profile: Profile data container
* ProfileTrace: Trace data for individual operations
* ProfileMetrics: Performance metrics collection
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
)
from dataclasses import dataclass, field
import asyncio
import time
import functools
import contextvars
import statistics
import sys
import traceback
from contextlib import asynccontextmanager
from ..exceptions import ProfilerError

T = TypeVar("T")


@dataclass
class ProfileTrace:
    """
    Container for trace data of an operation.

    :param name: Operation name
    :type name: str
    :param start_time: Start timestamp
    :type start_time: float
    :param end_time: End timestamp
    :type end_time: float
    :param metadata: Additional trace metadata
    :type metadata: Dict[str, Any]
    """

    name: str
    start_time: float
    end_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[int] = None
    async_task_id: Optional[int] = None
    stack_trace: Optional[str] = None
    memory_start: int = 0
    memory_end: int = 0

    @property
    def duration(self) -> float:
        """Get operation duration in seconds."""
        return self.end_time - self.start_time

    @property
    def memory_delta(self) -> int:
        """Get memory usage delta."""
        return self.memory_end - self.memory_start


@dataclass
class ProfileMetrics:
    """
    Container for profile metrics.

    :param total_time: Total execution time
    :type total_time: float
    :param avg_time: Average execution time
    :type avg_time: float
    :param min_time: Minimum execution time
    :type min_time: float
    :param max_time: Maximum execution time
    :type max_time: float
    """

    total_time: float = 0.0
    avg_time: float = 0.0
    min_time: float = float("inf")
    max_time: float = 0.0
    call_count: int = 0
    memory_total: int = 0
    memory_avg: float = 0.0
    percentiles: Dict[int, float] = field(default_factory=dict)


class Profile:
    """
    Container for profile data.

    Example::

        profile = await profiler.get_profile()
        print(f"Total execution time: {profile.total_time:.2f}s")
        for trace in profile.traces:
            print(f"{trace.name}: {trace.duration:.2f}s")
    """

    def __init__(self):
        """Initialize the profile."""
        self.traces: List[ProfileTrace] = []
        self.start_time: float = time.time()
        self.end_time: Optional[float] = None
        self._metrics_cache: Dict[str, ProfileMetrics] = {}

    @property
    def total_time(self) -> float:
        """Get total profile duration."""
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time

    def add_trace(self, trace: ProfileTrace) -> None:
        """
        Add a trace to the profile.

        :param trace: Trace to add
        :type trace: ProfileTrace
        """
        self.traces.append(trace)
        self._metrics_cache.clear()

    def get_metrics(self, operation_name: Optional[str] = None) -> ProfileMetrics:
        """
        Get metrics for an operation.

        :param operation_name: Optional operation name filter
        :type operation_name: Optional[str]
        :return: Operation metrics
        :rtype: ProfileMetrics
        """
        cache_key = operation_name or "*"
        if cache_key in self._metrics_cache:
            return self._metrics_cache[cache_key]

        filtered_traces = [
            t for t in self.traces if operation_name is None or t.name == operation_name
        ]

        if not filtered_traces:
            return ProfileMetrics()

        durations = [t.duration for t in filtered_traces]
        memory_deltas = [t.memory_delta for t in filtered_traces]

        metrics = ProfileMetrics(
            total_time=sum(durations),
            avg_time=statistics.mean(durations),
            min_time=min(durations),
            max_time=max(durations),
            call_count=len(filtered_traces),
            memory_total=sum(memory_deltas),
            memory_avg=statistics.mean(memory_deltas),
            percentiles={
                50: statistics.median(durations),
                90: statistics.quantiles(durations, n=10)[-1],
                95: statistics.quantiles(durations, n=20)[-1],
                99: statistics.quantiles(durations, n=100)[-1],
            },
        )

        self._metrics_cache[cache_key] = metrics
        return metrics


class Profiler:
    """
    Async operation profiler.

    Example::

        profiler = Profiler()

        @profiler.trace
        async def operation():
            await asyncio.sleep(1)

        async with profiler.trace_context("block"):
            await operation()

        profile = await profiler.get_profile()
    """

    def __init__(
        self,
        *,
        enabled: bool = True,
        trace_async_tasks: bool = True,
        collect_stack_trace: bool = False,
    ):
        """
        Initialize the profiler.

        :param enabled: Whether profiling is enabled
        :type enabled: bool
        :param trace_async_tasks: Whether to trace async tasks
        :type trace_async_tasks: bool
        :param collect_stack_trace: Whether to collect stack traces
        :type collect_stack_trace: bool
        """
        self.enabled = enabled
        self.trace_async_tasks = trace_async_tasks
        self.collect_stack_trace = collect_stack_trace
        self._current_profile = Profile()
        self._trace_stack: List[ProfileTrace] = []
        self._task_traces: Dict[int, ProfileTrace] = {}
        self._trace_context = contextvars.ContextVar("trace_context")

    def trace(
        self,
        func: Optional[Callable[..., Awaitable[T]]] = None,
        *,
        name: Optional[str] = None,
    ) -> Union[
        Callable[..., Awaitable[T]],
        Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]],
    ]:
        """
        Decorator to trace async functions.

        :param func: Function to trace
        :type func: Optional[Callable[..., Awaitable[T]]]
        :param name: Optional operation name
        :type name: Optional[str]
        :return: Decorated function
        :rtype: Union[Callable[..., Awaitable[T]], Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]]
        """

        def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
            if not self.enabled:
                return func

            operation_name = name or func.__qualname__

            @functools.wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> T:
                async with self.trace_context(operation_name):
                    return await func(*args, **kwargs)

            return wrapper

        if func is None:
            return decorator
        return decorator(func)

    @asynccontextmanager
    async def trace_context(self, name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Context manager for tracing code blocks.

        :param name: Operation name
        :type name: str
        :param metadata: Optional trace metadata
        :type metadata: Optional[Dict[str, Any]]
        """
        if not self.enabled:
            yield
            return

        trace = ProfileTrace(
            name=name,
            start_time=time.time(),
            end_time=0.0,
            metadata=metadata or {},
            parent_id=id(self._trace_stack[-1]) if self._trace_stack else None,
            async_task_id=(
                id(asyncio.current_task()) if self.trace_async_tasks else None
            ),
            stack_trace=traceback.extract_stack() if self.collect_stack_trace else None,
            memory_start=sys.getsizeof(sys.modules),
        )

        self._trace_stack.append(trace)
        if self.trace_async_tasks:
            self._task_traces[id(asyncio.current_task())] = trace

        try:
            yield trace
        finally:
            if self._trace_stack and self._trace_stack[-1] is trace:
                trace.end_time = time.time()
                trace.memory_end = sys.getsizeof(sys.modules)
                self._current_profile.add_trace(trace)
                self._trace_stack.pop()
                if self.trace_async_tasks:
                    task_id = id(asyncio.current_task())
                    self._task_traces.pop(task_id, None)

    async def get_profile(self) -> Profile:
        """
        Get the current profile.

        :return: Current profile
        :rtype: Profile
        """
        return self._current_profile

    async def reset(self) -> None:
        """Reset the profiler."""
        self._current_profile = Profile()
        self._trace_stack.clear()
        self._task_traces.clear()

    async def start_trace(
        self, name: str, metadata: Optional[Dict[str, Any]] = None
    ) -> ProfileTrace:
        """
        Start a new trace manually.

        :param name: Operation name
        :type name: str
        :param metadata: Optional trace metadata
        :type metadata: Optional[Dict[str, Any]]
        :return: New trace
        :rtype: ProfileTrace
        """
        trace = ProfileTrace(
            name=name,
            start_time=time.time(),
            end_time=0.0,
            metadata=metadata or {},
            parent_id=id(self._trace_stack[-1]) if self._trace_stack else None,
            async_task_id=(
                id(asyncio.current_task()) if self.trace_async_tasks else None
            ),
            stack_trace=traceback.extract_stack() if self.collect_stack_trace else None,
            memory_start=sys.getsizeof(sys.modules),
        )

        self._trace_stack.append(trace)
        return trace

    async def end_trace(self, trace: ProfileTrace) -> None:
        """
        End a trace manually.

        :param trace: Trace to end
        :type trace: ProfileTrace
        """
        if trace in self._trace_stack:
            trace.end_time = time.time()
            trace.memory_end = sys.getsizeof(sys.modules)
            self._current_profile.add_trace(trace)
            self._trace_stack.remove(trace)

    async def export_profile(self, format: str = "json") -> str:
        """
        Export profile data in various formats.

        :param format: Export format ('json' or 'chrome-trace')
        :type format: str
        :return: Formatted profile data
        :rtype: str
        """
        if format == "json":
            return self._export_json()
        elif format == "chrome-trace":
            return self._export_chrome_trace()
        else:
            raise ProfilerError(f"Unsupported export format: {format}")

    def _export_json(self) -> str:
        """Export profile as JSON."""
        import json

        def trace_to_dict(trace: ProfileTrace) -> Dict[str, Any]:
            return {
                "name": trace.name,
                "start_time": trace.start_time,
                "end_time": trace.end_time,
                "duration": trace.duration,
                "metadata": trace.metadata,
                "parent_id": trace.parent_id,
                "async_task_id": trace.async_task_id,
                "memory_delta": trace.memory_delta,
            }

        data = {
            "start_time": self._current_profile.start_time,
            "end_time": self._current_profile.end_time,
            "total_time": self._current_profile.total_time,
            "traces": [trace_to_dict(t) for t in self._current_profile.traces],
        }

        return json.dumps(data, indent=2)

    def _export_chrome_trace(self) -> str:
        """Export profile in Chrome tracing format."""
        import json

        events = []
        for trace in self._current_profile.traces:
            events.extend(
                [
                    {
                        "name": trace.name,
                        "cat": "async",
                        "ph": "B",  # Begin
                        "pid": 1,
                        "tid": trace.async_task_id or 1,
                        "ts": trace.start_time * 1_000_000,  # Convert to microseconds
                        "args": trace.metadata,
                    },
                    {
                        "name": trace.name,
                        "cat": "async",
                        "ph": "E",  # End
                        "pid": 1,
                        "tid": trace.async_task_id or 1,
                        "ts": trace.end_time * 1_000_000,
                        "args": {"duration": trace.duration},
                    },
                ]
            )

        return json.dumps({"traceEvents": events}, indent=2)
