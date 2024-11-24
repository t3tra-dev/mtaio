"""
Resource monitoring implementation modules.

This module provides components for monitoring system resources:

* ResourceMonitor: Main monitoring class
* SystemStats: System statistics container
* ResourceMetrics: Resource metrics collection
* AlertManager: Resource alert management
"""

from typing import Dict, List, Set, Optional, Callable, Awaitable
from dataclasses import dataclass
import asyncio
import time
import os
import sys
import platform
import logging
import threading

logger = logging.getLogger(__name__)


@dataclass
class CPUStats:
    """
    CPU statistics container.

    :param usage_percent: CPU usage percentage
    :type usage_percent: float
    :param load_average: System load average
    :type load_average: List[float]
    :param thread_count: Number of threads
    :type thread_count: int
    """

    usage_percent: float
    load_average: List[float]
    thread_count: int


@dataclass
class MemoryStats:
    """
    Memory statistics container.

    :param total: Total system memory in bytes
    :type total: int
    :param available: Available memory in bytes
    :type available: int
    :param used: Used memory in bytes
    :type used: int
    :param percent: Memory usage percentage
    :type percent: float
    """

    total: int
    available: int
    used: int
    percent: float


@dataclass
class IOStats:
    """
    I/O statistics container.

    :param read_bytes: Bytes read
    :type read_bytes: int
    :param write_bytes: Bytes written
    :type write_bytes: int
    :param read_count: Number of read operations
    :type read_count: int
    :param write_count: Number of write operations
    :type write_count: int
    """

    read_bytes: int
    write_bytes: int
    read_count: int
    write_count: int


@dataclass
class SystemStats:
    """
    System statistics container.

    :param timestamp: Statistics timestamp
    :type timestamp: float
    :param cpu: CPU statistics
    :type cpu: CPUStats
    :param memory: Memory statistics
    :type memory: MemoryStats
    :param io: I/O statistics
    :type io: IOStats
    """

    timestamp: float
    cpu: CPUStats
    memory: MemoryStats
    io: IOStats


class ResourceMonitor:
    """
    Resource monitoring implementation.

    Example::

        monitor = ResourceMonitor()

        @monitor.on_threshold_exceeded
        async def handle_alert(metric: str, value: float, threshold: float):
            print(f"Alert: {metric} exceeded threshold ({value} > {threshold})")

        await monitor.start()
    """

    def __init__(self, interval: float = 1.0, history_size: int = 3600):
        """
        Initialize the monitor.

        :param interval: Monitoring interval in seconds
        :type interval: float
        :param history_size: Number of historical stats to keep
        :type history_size: int
        """
        self.interval = interval
        self.history_size = history_size
        self._history: List[SystemStats] = []
        self._thresholds: Dict[str, float] = {}
        self._alerts: Set[Callable[[str, float, float], Awaitable[None]]] = set()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

        # Platform specific initializations
        self._platform = platform.system().lower()
        self._last_cpu_times: Optional[tuple] = None
        self._last_io_stats: Optional[IOStats] = None

    def on_threshold_exceeded(
        self, callback: Callable[[str, float, float], Awaitable[None]]
    ) -> Callable[[str, float, float], Awaitable[None]]:
        """
        Register a threshold exceeded callback.

        :param callback: Callback function
        :type callback: Callable[[str, float, float], Awaitable[None]]
        :return: Registered callback
        :rtype: Callable[[str, float, float], Awaitable[None]]
        """
        self._alerts.add(callback)
        return callback

    def set_threshold(self, metric: str, value: float) -> None:
        """
        Set a threshold for a metric.

        :param metric: Metric name
        :type metric: str
        :param value: Threshold value
        :type value: float
        """
        self._thresholds[metric] = value

    async def start(self) -> None:
        """Start monitoring."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor())

    async def stop(self) -> None:
        """Stop monitoring."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def get_current_stats(self) -> SystemStats:
        """
        Get current system statistics.

        :return: Current system statistics
        :rtype: SystemStats
        """
        return await self._collect_stats()

    async def get_history(
        self, start_time: Optional[float] = None, end_time: Optional[float] = None
    ) -> List[SystemStats]:
        """
        Get historical statistics.

        :param start_time: Start timestamp
        :type start_time: Optional[float]
        :param end_time: End timestamp
        :type end_time: Optional[float]
        :return: List of historical statistics
        :rtype: List[SystemStats]
        """
        async with self._lock:
            if start_time is None and end_time is None:
                return self._history.copy()

            filtered = []
            for stats in self._history:
                if (start_time is None or stats.timestamp >= start_time) and (
                    end_time is None or stats.timestamp <= end_time
                ):
                    filtered.append(stats)
            return filtered

    async def _monitor(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                stats = await self._collect_stats()
                await self._process_stats(stats)
                await asyncio.sleep(self.interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(self.interval)

    async def _collect_stats(self) -> SystemStats:
        """Collect system statistics."""
        cpu_stats = await self._collect_cpu_stats()
        memory_stats = await self._collect_memory_stats()
        io_stats = await self._collect_io_stats()

        return SystemStats(
            timestamp=time.time(), cpu=cpu_stats, memory=memory_stats, io=io_stats
        )

    async def _collect_cpu_stats(self) -> CPUStats:
        """Collect CPU statistics."""
        # Get CPU times
        if self._platform == "windows":
            times = await self._get_windows_cpu_times()
        elif self._platform in ("linux", "darwin"):
            times = await self._get_unix_cpu_times()
        else:
            times = (0, 0)  # Fallback for unsupported platforms

        # Calculate CPU usage
        usage_percent = 0.0
        if self._last_cpu_times is not None:
            prev_total = sum(self._last_cpu_times)
            prev_idle = self._last_cpu_times[1]
            total = sum(times)
            idle = times[1]

            if total - prev_total > 0:
                usage_percent = (1.0 - (idle - prev_idle) / (total - prev_total)) * 100

        self._last_cpu_times = times

        # Get load average
        try:
            load_average = os.getloadavg()
        except (AttributeError, OSError):
            load_average = [0.0, 0.0, 0.0]

        return CPUStats(
            usage_percent=usage_percent,
            load_average=list(load_average),
            thread_count=threading.active_count(),
        )

    async def _collect_memory_stats(self) -> MemoryStats:
        """Collect memory statistics."""
        if self._platform == "windows":
            stats = await self._get_windows_memory_stats()
        elif self._platform in ("linux", "darwin"):
            stats = await self._get_unix_memory_stats()
        else:
            # Fallback using Python's memory info
            total = 1
            used = sys.getsizeof(None)
            available = total - used
            stats = (total, available, used)

        total, available, used = stats
        percent = (used / total * 100) if total > 0 else 0.0

        return MemoryStats(total=total, available=available, used=used, percent=percent)

    async def _collect_io_stats(self) -> IOStats:
        """Collect I/O statistics."""
        current = await self._get_io_stats()

        if self._last_io_stats is None:
            self._last_io_stats = current
            return current

        # Calculate differential
        stats = IOStats(
            read_bytes=max(0, current.read_bytes - self._last_io_stats.read_bytes),
            write_bytes=max(0, current.write_bytes - self._last_io_stats.write_bytes),
            read_count=max(0, current.read_count - self._last_io_stats.read_count),
            write_count=max(0, current.write_count - self._last_io_stats.write_count),
        )

        self._last_io_stats = current
        return stats

    async def _get_windows_cpu_times(self) -> tuple:
        """Get CPU times on Windows."""
        # This is a simplified implementation
        return (time.time(), time.time() * 0.05)

    async def _get_unix_cpu_times(self) -> tuple:
        """Get CPU times on Unix-like systems."""
        try:
            with open("/proc/stat", "r") as f:
                cpu_line = f.readline()
                if cpu_line.startswith("cpu"):
                    times = [float(x) for x in cpu_line.strip().split()[1:]]
                    idle_time = times[3]
                    total_time = sum(times)
                    return (total_time, idle_time)
        except Exception:
            pass
        return (time.time(), time.time() * 0.05)

    async def _get_windows_memory_stats(self) -> tuple:
        """Get memory statistics on Windows."""
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            status = ctypes.c_ulong()
            kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            total = status.ullTotalPhys
            available = status.ullAvailPhys
            return (total, available, total - available)
        except Exception:
            return (0, 0, 0)

    async def _get_unix_memory_stats(self) -> tuple:
        """Get memory statistics on Unix-like systems."""
        try:
            with open("/proc/meminfo", "r") as f:
                content = f.read()
                total = available = used = 0

                for line in content.split("\n"):
                    if line.startswith("MemTotal:"):
                        total = int(line.split()[1]) * 1024
                    elif line.startswith("MemAvailable:"):
                        available = int(line.split()[1]) * 1024

                used = total - available
                return (total, available, used)
        except Exception:
            return (0, 0, 0)

    async def _get_io_stats(self) -> IOStats:
        """Get I/O statistics."""
        # This is a simplified implementation that tracks Python's file operations
        stats = IOStats(0, 0, 0, 0)

        # Try to get system-wide I/O stats if available
        if self._platform == "linux":
            try:
                with open("/proc/diskstats", "r") as f:
                    for line in f:
                        fields = line.strip().split()
                        if len(fields) >= 14:
                            stats.read_count += int(fields[3])
                            stats.read_bytes += int(fields[5]) * 512
                            stats.write_count += int(fields[7])
                            stats.write_bytes += int(fields[9]) * 512
            except Exception:
                pass

        return stats

    async def _process_stats(self, stats: SystemStats) -> None:
        """
        Process collected statistics.

        :param stats: Collected statistics
        :type stats: SystemStats
        """
        async with self._lock:
            self._history.append(stats)
            while len(self._history) > self.history_size:
                self._history.pop(0)

        # Check thresholds
        await self._check_thresholds(stats)

    async def _check_thresholds(self, stats: SystemStats) -> None:
        """
        Check if any thresholds are exceeded.

        :param stats: Statistics to check
        :type stats: SystemStats
        """
        checks = {
            "cpu_usage": stats.cpu.usage_percent,
            "memory_usage": stats.memory.percent,
            "load_average": stats.cpu.load_average[0],
            "thread_count": float(stats.cpu.thread_count),
        }

        for metric, value in checks.items():
            threshold = self._thresholds.get(metric)
            if threshold is not None and value > threshold:
                await self._trigger_alerts(metric, value, threshold)

    async def _trigger_alerts(
        self, metric: str, value: float, threshold: float
    ) -> None:
        """
        Trigger alert callbacks.

        :param metric: Metric name
        :type metric: str
        :param value: Current value
        :type value: float
        :param threshold: Threshold value
        :type threshold: float
        """
        for callback in self._alerts:
            try:
                await callback(metric, value, threshold)
            except Exception as e:
                logger.error(f"Error in alert callback: {str(e)}")
