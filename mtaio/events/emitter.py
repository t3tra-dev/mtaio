"""
Asynchronous event emitter implementation.

This module provides classes for handling asynchronous events:

* EventEmitter: Base event emitter class
* Event: Event data container
* EventListener: Event listener interface
* PrioritizedEventListener: Listener with priority support
"""

from contextlib import asynccontextmanager
import time
from typing import (
    Tuple,
    TypeVar,
    Generic,
    Dict,
    List,
    Optional,
    Any,
    Callable,
    Awaitable,
    Union,
    Protocol,
    runtime_checkable,
)
from dataclasses import dataclass, field
from enum import Enum, auto
import asyncio
import inspect
import logging
from ..exceptions import EventError

T = TypeVar("T")
logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """Event listener priority levels."""

    LOWEST = auto()
    LOW = auto()
    NORMAL = auto()
    HIGH = auto()
    HIGHEST = auto()
    MONITOR = auto()


@dataclass
class Event(Generic[T]):
    """
    Container for event data.

    :param name: Event name
    :type name: str
    :param data: Event data
    :type data: T
    :param propagate: Whether to continue propagation
    :type propagate: bool
    """

    name: str
    data: T
    propagate: bool = True
    timestamp: float = field(default_factory=time.monotonic)
    metadata: Dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class EventListener(Protocol[T]):
    """
    Protocol for event listeners.

    Listeners must implement either __call__ or handle_event.
    """

    async def __call__(self, event: Event[T]) -> None:
        """
        Handle an event.

        :param event: Event to handle
        :type event: Event[T]
        """
        ...


class PrioritizedEventListener(Generic[T]):
    """
    Event listener with priority support.

    :param callback: Listener callback function
    :type callback: Callable[[Event[T]], Awaitable[None]]
    :param priority: Listener priority
    :type priority: EventPriority
    """

    def __init__(
        self,
        callback: Callable[[Event[T]], Awaitable[None]],
        priority: EventPriority = EventPriority.NORMAL,
    ):
        """Initialize the prioritized listener."""
        self.callback = callback
        self.priority = priority

    async def __call__(self, event: Event[T]) -> None:
        """Execute the listener callback."""
        await self.callback(event)


class EventEmitter:
    """
    Asynchronous event emitter implementation.

    Example::

        emitter = EventEmitter()

        @emitter.on("user_login")
        async def handle_login(event):
            user = event.data
            print(f"User {user.name} logged in")

        await emitter.emit("user_login", user_data)
    """

    def __init__(self):
        """Initialize the event emitter."""
        self._listeners: Dict[str, List[PrioritizedEventListener]] = {}
        self._wildcards: List[PrioritizedEventListener] = []
        self._listener_count = 0
        self._lock = asyncio.Lock()
        self._hooks: Dict[str, List[Callable]] = {
            "before_emit": [],
            "after_emit": [],
            "on_error": [],
        }

    async def emit(
        self, event_name: str, data: Any, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Emit an event.

        :param event_name: Name of the event
        :type event_name: str
        :param data: Event data
        :type data: Any
        :param metadata: Optional event metadata
        :type metadata: Optional[Dict[str, Any]]
        :raises EventError: If event emission fails
        """
        event = Event(event_name, data, metadata=metadata or {})

        try:
            # Execute before_emit hooks
            for hook in self._hooks["before_emit"]:
                await self._execute_hook(hook, event)

            async with self._lock:
                # Get all relevant listeners
                listeners = self._get_listeners(event_name)

                # Execute listeners in priority order
                for listener in listeners:
                    try:
                        if not event.propagate:
                            break
                        await listener(event)
                    except Exception as e:
                        await self._handle_listener_error(e, event, listener)

            # Execute after_emit hooks
            for hook in self._hooks["after_emit"]:
                await self._execute_hook(hook, event)

        except Exception as e:
            # Execute error hooks
            for hook in self._hooks["on_error"]:
                await self._execute_hook(hook, event, error=e)
            raise EventError(f"Error emitting event {event_name}: {str(e)}") from e

    def on(
        self, event_name: str, priority: EventPriority = EventPriority.NORMAL
    ) -> Callable[
        [Callable[[Event], Awaitable[None]]], Callable[[Event], Awaitable[None]]
    ]:
        """
        Decorator to register an event listener.

        :param event_name: Name of the event to listen for
        :type event_name: str
        :param priority: Listener priority
        :type priority: EventPriority
        :return: Decorator function
        :rtype: Callable

        Example::

            @emitter.on("user_login")
            async def handle_login(event):
                print(f"User logged in: {event.data}")
        """

        def decorator(
            func: Callable[[Event], Awaitable[None]]
        ) -> Callable[[Event], Awaitable[None]]:
            self.add_listener(event_name, func, priority)
            return func

        return decorator

    def once(
        self, event_name: str, priority: EventPriority = EventPriority.NORMAL
    ) -> Callable[
        [Callable[[Event], Awaitable[None]]], Callable[[Event], Awaitable[None]]
    ]:
        """
        Decorator to register a one-time event listener.

        :param event_name: Name of the event to listen for
        :type event_name: str
        :param priority: Listener priority
        :type priority: EventPriority
        :return: Decorator function
        :rtype: Callable
        """

        def decorator(
            func: Callable[[Event], Awaitable[None]]
        ) -> Callable[[Event], Awaitable[None]]:
            async def wrapper(event: Event) -> None:
                await func(event)
                self.remove_listener(event_name, wrapper)

            self.add_listener(event_name, wrapper, priority)
            return wrapper

        return decorator

    def add_listener(
        self,
        event_name: str,
        listener: Union[Callable[[Event], Awaitable[None]], EventListener],
        priority: EventPriority = EventPriority.NORMAL,
    ) -> None:
        """
        Add an event listener.

        :param event_name: Name of the event to listen for
        :type event_name: str
        :param listener: Event listener
        :type listener: Union[Callable[[Event], Awaitable[None]], EventListener]
        :param priority: Listener priority
        :type priority: EventPriority
        """
        prioritized_listener = PrioritizedEventListener(listener, priority)

        if event_name == "*":
            self._wildcards.append(prioritized_listener)
            self._wildcards.sort(key=lambda l: l.priority.value, reverse=True)  # noqa
        else:
            if event_name not in self._listeners:
                self._listeners[event_name] = []
            self._listeners[event_name].append(prioritized_listener)
            self._listeners[event_name].sort(
                key=lambda l: l.priority.value, reverse=True  # noqa
            )

        self._listener_count += 1

    def remove_listener(
        self,
        event_name: str,
        listener: Union[Callable[[Event], Awaitable[None]], EventListener],
    ) -> None:
        """
        Remove an event listener.

        :param event_name: Name of the event
        :type event_name: str
        :param listener: Listener to remove
        :type listener: Union[Callable[[Event], Awaitable[None]], EventListener]
        """
        if event_name == "*":
            self._wildcards = [
                l for l in self._wildcards if l.callback != listener  # noqa
            ]  # noqa
        elif event_name in self._listeners:
            self._listeners[event_name] = [
                l for l in self._listeners[event_name] if l.callback != listener  # noqa
            ]
            if not self._listeners[event_name]:
                del self._listeners[event_name]

        self._listener_count -= 1

    def remove_all_listeners(self, event_name: Optional[str] = None) -> None:
        """
        Remove all listeners for an event.

        :param event_name: Name of the event (None for all events)
        :type event_name: Optional[str]
        """
        if event_name is None:
            count = self._listener_count
            self._listeners.clear()
            self._wildcards.clear()
            self._listener_count = 0
            return count

        count = 0
        if event_name == "*":
            count = len(self._wildcards)
            self._wildcards.clear()
        elif event_name in self._listeners:
            count = len(self._listeners[event_name])
            del self._listeners[event_name]

        self._listener_count -= count
        return count

    def listener_count(self, event_name: Optional[str] = None) -> int:
        """
        Get the number of listeners.

        :param event_name: Name of the event (None for all events)
        :type event_name: Optional[str]
        :return: Number of listeners
        :rtype: int
        """
        if event_name is None:
            return self._listener_count

        count = 0
        if event_name == "*":
            count = len(self._wildcards)
        elif event_name in self._listeners:
            count = len(self._listeners[event_name])
        return count

    def add_hook(self, hook_type: str, callback: Callable) -> None:
        """
        Add a hook function.

        :param hook_type: Type of hook ('before_emit', 'after_emit', 'on_error')
        :type hook_type: str
        :param callback: Hook callback function
        :type callback: Callable
        :raises ValueError: If hook_type is invalid
        """
        if hook_type not in self._hooks:
            raise ValueError(f"Invalid hook type: {hook_type}")
        self._hooks[hook_type].append(callback)

    def remove_hook(self, hook_type: str, callback: Callable) -> None:
        """
        Remove a hook function.

        :param hook_type: Type of hook
        :type hook_type: str
        :param callback: Hook callback function
        :type callback: Callable
        """
        if hook_type in self._hooks:
            self._hooks[hook_type] = [
                h for h in self._hooks[hook_type] if h != callback
            ]

    async def wait_for(
        self,
        event_name: str,
        timeout: Optional[float] = None,
        check: Optional[Callable[[Event], bool]] = None,
    ) -> Event:
        """
        Wait for an event to occur.

        :param event_name: Name of the event to wait for
        :type event_name: str
        :param timeout: Maximum time to wait
        :type timeout: Optional[float]
        :param check: Optional predicate to check event
        :type check: Optional[Callable[[Event], bool]]
        :return: Event that occurred
        :rtype: Event
        :raises asyncio.TimeoutError: If timeout occurs
        """
        future = asyncio.Future()

        async def handler(event: Event) -> None:
            if check is None or check(event):
                if not future.done():
                    future.set_result(event)
                    self.remove_listener(event_name, handler)

        self.add_listener(event_name, handler, EventPriority.MONITOR)

        try:
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            self.remove_listener(event_name, handler)
            raise

    def _get_listeners(self, event_name: str) -> List[PrioritizedEventListener]:
        """Get all listeners for an event including wildcards."""
        listeners = []
        if event_name in self._listeners:
            listeners.extend(self._listeners[event_name])
        listeners.extend(self._wildcards)
        return listeners

    async def _handle_listener_error(
        self, error: Exception, event: Event, listener: PrioritizedEventListener
    ) -> None:
        """Handle an error that occurred in a listener."""
        logger.error(
            f"Error in event listener for {event.name}: {str(error)}", exc_info=error
        )
        for hook in self._hooks["on_error"]:
            await self._execute_hook(hook, event, error=error)

    async def _execute_hook(
        self, hook: Callable, event: Event, error: Optional[Exception] = None
    ) -> None:
        """
        Execute a hook function.

        :param hook: Hook function to execute
        :type hook: Callable
        :param event: Event being processed
        :type event: Event
        :param error: Optional error that occurred
        :type error: Optional[Exception]
        """
        try:
            if inspect.iscoroutinefunction(hook):
                await hook(event, error)
            else:
                hook(event, error)
        except Exception as e:
            logger.error(f"Error in event hook: {str(e)}", exc_info=e)

    async def emit_after(
        self,
        delay: float,
        event_name: str,
        data: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> asyncio.Task:
        """
        Emit an event after a delay.

        :param delay: Delay in seconds
        :type delay: float
        :param event_name: Name of the event
        :type event_name: str
        :param data: Event data
        :type data: Any
        :param metadata: Optional event metadata
        :type metadata: Optional[Dict[str, Any]]
        :return: Task that will emit the event
        :rtype: asyncio.Task
        """

        async def delayed_emit():
            await asyncio.sleep(delay)
            await self.emit(event_name, data, metadata)

        return asyncio.create_task(delayed_emit())

    async def emit_periodic(
        self,
        interval: float,
        event_name: str,
        data_provider: Callable[[], Awaitable[Any]],
        metadata_provider: Optional[Callable[[], Awaitable[Dict[str, Any]]]] = None,
        max_count: Optional[int] = None,
    ) -> asyncio.Task:
        """
        Emit an event periodically.

        :param interval: Interval between emissions in seconds
        :type interval: float
        :param event_name: Name of the event
        :type event_name: str
        :param data_provider: Async function that provides event data
        :type data_provider: Callable[[], Awaitable[Any]]
        :param metadata_provider: Optional async function that provides metadata
        :type metadata_provider: Optional[Callable[[], Awaitable[Dict[str, Any]]]]
        :param max_count: Maximum number of emissions (None for unlimited)
        :type max_count: Optional[int]
        :return: Task that will emit the events
        :rtype: asyncio.Task
        """

        async def periodic_emit():
            count = 0
            while max_count is None or count < max_count:
                try:
                    data = await data_provider()
                    metadata = (
                        await metadata_provider()
                        if metadata_provider is not None
                        else None
                    )
                    await self.emit(event_name, data, metadata)
                    count += 1
                    await asyncio.sleep(interval)
                except Exception as e:
                    logger.error(
                        f"Error in periodic event emission: {str(e)}", exc_info=e
                    )
                    await asyncio.sleep(interval)

        return asyncio.create_task(periodic_emit())

    def pipe(self, other: "EventEmitter", event_name: Optional[str] = None) -> None:
        """
        Pipe events from this emitter to another.

        :param other: Target event emitter
        :type other: EventEmitter
        :param event_name: Optional event name to pipe (None for all events)
        :type event_name: Optional[str]
        """

        async def pipe_handler(event: Event) -> None:
            await other.emit(event.name, event.data, event.metadata)

        if event_name is not None:
            self.add_listener(event_name, pipe_handler, EventPriority.MONITOR)
        else:
            self.add_listener("*", pipe_handler, EventPriority.MONITOR)

    def filter(
        self, predicate: Callable[[Event], bool], event_name: Optional[str] = None
    ) -> "EventEmitter":
        """
        Create a new emitter that filters events based on a predicate.

        :param predicate: Function to filter events
        :type predicate: Callable[[Event], bool]
        :param event_name: Optional event name to filter (None for all events)
        :type event_name: Optional[str]
        :return: New filtered event emitter
        :rtype: EventEmitter
        """
        filtered = EventEmitter()

        async def filter_handler(event: Event) -> None:
            if predicate(event):
                await filtered.emit(event.name, event.data, event.metadata)

        if event_name is not None:
            self.add_listener(event_name, filter_handler, EventPriority.MONITOR)
        else:
            self.add_listener("*", filter_handler, EventPriority.MONITOR)

        return filtered

    def map(
        self, transform: Callable[[Event], Event], event_name: Optional[str] = None
    ) -> "EventEmitter":
        """
        Create a new emitter that transforms events.

        :param transform: Function to transform events
        :type transform: Callable[[Event], Event]
        :param event_name: Optional event name to transform (None for all events)
        :type event_name: Optional[str]
        :return: New transformed event emitter
        :rtype: EventEmitter
        """
        transformed = EventEmitter()

        async def map_handler(event: Event) -> None:
            transformed_event = transform(event)
            await transformed.emit(
                transformed_event.name,
                transformed_event.data,
                transformed_event.metadata,
            )

        if event_name is not None:
            self.add_listener(event_name, map_handler, EventPriority.MONITOR)
        else:
            self.add_listener("*", map_handler, EventPriority.MONITOR)

        return transformed

    def buffer(self, size: int, event_name: Optional[str] = None) -> "EventEmitter":
        """
        Create a new emitter that buffers events.

        :param size: Buffer size
        :type size: int
        :param event_name: Optional event name to buffer (None for all events)
        :type event_name: Optional[str]
        :return: New buffered event emitter
        :rtype: EventEmitter
        """
        buffered = EventEmitter()
        buffer: List[Event] = []

        async def buffer_handler(event: Event) -> None:
            buffer.append(event)
            if len(buffer) >= size:
                events = buffer.copy()
                buffer.clear()
                for buffered_event in events:
                    await buffered.emit(
                        buffered_event.name,
                        buffered_event.data,
                        buffered_event.metadata,
                    )

        if event_name is not None:
            self.add_listener(event_name, buffer_handler, EventPriority.MONITOR)
        else:
            self.add_listener("*", buffer_handler, EventPriority.MONITOR)

        return buffered

    @asynccontextmanager
    async def suppress_events(self, event_name: Optional[str] = None):
        """
        Context manager to temporarily suppress events.

        :param event_name: Optional event name to suppress (None for all events)
        :type event_name: Optional[str]

        Example::

            async with emitter.suppress_events("user_login"):
                # Events of type "user_login" will not be emitted
                await perform_operations()
        """
        suppressed_events: List[Tuple[str, Any, Dict[str, Any]]] = []

        async def suppress_handler(event: Event) -> None:
            suppressed_events.append((event.name, event.data, event.metadata))
            event.propagate = False

        if event_name is not None:
            self.add_listener(event_name, suppress_handler, EventPriority.HIGHEST)
        else:
            self.add_listener("*", suppress_handler, EventPriority.HIGHEST)

        try:
            yield suppressed_events
        finally:
            self.remove_listener(event_name or "*", suppress_handler)

    async def replay_events(
        self, events: List[Tuple[str, Any, Dict[str, Any]]]
    ) -> None:
        """
        Replay a list of suppressed events.

        :param events: List of events to replay
        :type events: List[Tuple[str, Any, Dict[str, Any]]]
        """
        for event_name, data, metadata in events:
            await self.emit(event_name, data, metadata)

    def shutdown(self) -> None:
        """Clean up the event emitter."""
        self.remove_all_listeners()
        self._hooks.clear()
