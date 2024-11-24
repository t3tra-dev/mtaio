"""
mtaio exception class hierarchy.

This module defines all exceptions that can be raised by the mtaio framework components.
Each component has its own specific exception types inheriting from MTAIOError.
"""

from typing import Any, Optional
import asyncio


class MTAIOError(Exception):
    """Base exception class for mtaio framework."""

    def __init__(self, message: str, *args: Any, **kwargs: Any) -> None:
        """
        Initialize exception.

        :param message: Error message
        :type message: str
        """
        self.message = message
        super().__init__(message, *args)


class ExecutionError(MTAIOError):
    """Raised when task execution fails."""

    pass


class TimeoutError(MTAIOError, asyncio.TimeoutError):
    """Raised when an operation times out."""

    pass


class RetryError(MTAIOError):
    """Raised when retry attempts are exhausted."""

    def __init__(
        self,
        message: str,
        attempts: Optional[int] = None,
        last_error: Optional[Exception] = None,
    ) -> None:
        """
        Initialize retry error.

        :param message: Error message
        :type message: str
        :param attempts: Number of attempts made
        :type attempts: Optional[int]
        :param last_error: Last error encountered
        :type last_error: Optional[Exception]
        """
        super().__init__(message)
        self.attempts = attempts
        self.last_error = last_error


class RateLimitError(MTAIOError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        limit: Optional[float] = None,
        remaining: Optional[float] = None,
    ) -> None:
        """
        Initialize rate limit error.

        :param message: Error message
        :type message: str
        :param limit: Rate limit value
        :type limit: Optional[float]
        :param remaining: Time until reset
        :type remaining: Optional[float]
        """
        super().__init__(message)
        self.limit = limit
        self.remaining = remaining


class CircuitBreakerError(MTAIOError):
    """Raised when circuit breaker is open."""

    def __init__(
        self,
        message: str,
        failures: Optional[int] = None,
        reset_timeout: Optional[float] = None,
    ) -> None:
        """
        Initialize circuit breaker error.

        :param message: Error message
        :type message: str
        :param failures: Number of failures
        :type failures: Optional[int]
        :param reset_timeout: Reset timeout
        :type reset_timeout: Optional[float]
        """
        super().__init__(message)
        self.failures = failures
        self.reset_timeout = reset_timeout


class FallbackError(MTAIOError):
    """Raised when all fallback attempts fail."""

    pass


# Cache Exceptions
class CacheError(MTAIOError):
    """Base exception for cache operations."""

    pass


class CacheKeyError(CacheError):
    """Raised when a cache key is invalid or not found."""

    pass


class CacheConnectionError(CacheError):
    """Raised when cache connection fails."""

    pass


class CacheSerializationError(CacheError):
    """Raised when cache serialization/deserialization fails."""

    pass


# Event Exceptions
class EventError(MTAIOError):
    """Base exception for event operations."""

    pass


class EventEmitError(EventError):
    """Raised when event emission fails."""

    pass


class EventHandlerError(EventError):
    """Raised when event handler fails."""

    pass


# Channel Exceptions
class ChannelError(MTAIOError):
    """Base exception for channel operations."""

    pass


class ChannelClosedError(ChannelError):
    """Raised when attempting to use a closed channel."""

    pass


class ChannelFullError(ChannelError):
    """Raised when channel buffer is full."""

    pass


# Protocol Exceptions
class ProtocolError(MTAIOError):
    """Base exception for protocol operations."""

    pass


class ASGIError(ProtocolError):
    """Raised when ASGI protocol error occurs."""

    pass


class MQTTError(ProtocolError):
    """Raised when MQTT protocol error occurs."""

    pass


class MailError(ProtocolError):
    """Raised when mail protocol error occurs."""

    pass


# Resource Exceptions
class ResourceError(MTAIOError):
    """Base exception for resource operations."""

    pass


class ResourceLimitError(ResourceError):
    """Raised when resource limit is exceeded."""

    pass


class ResourceLockError(ResourceError):
    """Raised when resource lock operation fails."""

    pass


class ResourceTimeoutError(ResourceError, TimeoutError):
    """Raised when resource operation times out."""

    pass


# Monitoring Exceptions
class MonitoringError(MTAIOError):
    """Base exception for monitoring operations."""

    pass


class MetricError(MonitoringError):
    """Raised when metric operation fails."""

    pass


class AlertError(MonitoringError):
    """Raised when alert operation fails."""

    pass


# Optimization Exceptions
class OptimizationError(MTAIOError):
    """Base exception for optimization operations."""

    pass


class ParameterError(OptimizationError):
    """Raised when optimization parameter is invalid."""

    pass


class ConvergenceError(OptimizationError):
    """Raised when optimization fails to converge."""

    pass


# Profile Exceptions
class ProfilerError(MTAIOError):
    """Base exception for profiler operations."""

    pass


class TraceError(ProfilerError):
    """Raised when trace operation fails."""

    pass


class MetricsError(ProfilerError):
    """Raised when metrics collection fails."""

    pass


# Stream Exceptions
class StreamError(MTAIOError):
    """Base exception for stream operations."""

    pass


class StreamClosedError(StreamError):
    """Raised when stream is closed."""

    pass


class StreamTimeoutError(StreamError, TimeoutError):
    """Raised when stream operation times out."""

    pass


# Pipeline Exceptions
class PipelineError(MTAIOError):
    """Base exception for pipeline operations."""

    pass


class StageError(PipelineError):
    """Raised when pipeline stage fails."""

    pass


class InvalidStageError(PipelineError):
    """Raised when pipeline stage is invalid."""

    pass


# Observable Exceptions
class ObservableError(MTAIOError):
    """Base exception for observable operations."""

    pass


class ObserverError(ObservableError):
    """Raised when observer operation fails."""

    pass


class SubjectError(ObservableError):
    """Raised when subject operation fails."""

    pass


# Adapter Exceptions
class AdapterError(MTAIOError):
    """Base exception for adapter operations."""

    pass


class ConversionError(AdapterError):
    """Raised when type conversion fails."""

    pass


class CompatibilityError(AdapterError):
    """Raised when compatibility check fails."""

    pass


# Logging Exceptions
class LoggingError(MTAIOError):
    """Base exception for logging operations."""

    pass


class HandlerError(LoggingError):
    """Raised when log handler fails."""

    pass


class FormatterError(LoggingError):
    """Raised when log formatter fails."""

    pass


# Group Exceptions
class GroupError(MTAIOError):
    """Base exception for group operations."""

    pass


class TimeoutGroupError(GroupError, TimeoutError):
    """Raised when group operation times out."""

    pass


class CacheGroupError(GroupError):
    """Raised when cache group operation fails."""

    pass


# Batch Exceptions
class BatchError(MTAIOError):
    """Base exception for batch operations."""

    pass


class BatchProcessError(BatchError):
    """Raised when batch processing fails."""

    pass


class BatchTimeoutError(BatchError, TimeoutError):
    """Raised when batch operation times out."""

    pass


def format_exception(exc: Exception) -> str:
    """
    Format exception with details.

    :param exc: Exception to format
    :type exc: Exception
    :return: Formatted exception string
    :rtype: str
    """
    if isinstance(exc, MTAIOError):
        details = []
        for attr in dir(exc):
            if not attr.startswith("_") and attr not in ("args", "message"):
                value = getattr(exc, attr)
                if value is not None:
                    details.append(f"{attr}={value}")

        if details:
            return f"{exc.__class__.__name__}: {exc.message} ({', '.join(details)})"
        return f"{exc.__class__.__name__}: {exc.message}"

    return str(exc)


def wrap_exception(
    exc: Exception, new_type: type, message: Optional[str] = None
) -> Exception:
    """
    Wrap exception in new type.

    :param exc: Exception to wrap
    :type exc: Exception
    :param new_type: New exception type
    :type new_type: type
    :param message: Optional new message
    :type message: Optional[str]
    :return: Wrapped exception
    :rtype: Exception
    """
    if message is None:
        message = str(exc)

    wrapped = new_type(message)
    raise wrapped from exc
