"""
Observable pattern implementation for asynchronous data monitoring.

This module provides tools for implementing the Observer pattern in an asynchronous context:

* Observable: Base class for objects that can be observed
* Observer: Protocol defining the observer interface
* Change: Data class representing a change in the observable
"""

from contextlib import contextmanager
from typing import (
    List,
    TypeVar,
    Generic,
    Protocol,
    Set,
    Dict,
    Optional,
    Callable,
    Awaitable,
    Union,
    runtime_checkable,
)
from dataclasses import dataclass
from enum import Enum
import asyncio
import weakref
from ..exceptions import ObservableError

T = TypeVar("T")
V = TypeVar("V")


class ChangeType(Enum):
    """
    Enumeration of possible change types.
    """

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RESET = "reset"


@dataclass
class Change(Generic[T]):
    """
    Represents a change in an observable value.

    :param type: Type of change that occurred
    :type type: ChangeType
    :param path: Path to the changed value (e.g., "users.0.name")
    :type path: str
    :param value: New value (None for deletions)
    :type value: Optional[T]
    :param old_value: Previous value (None for creations)
    :type old_value: Optional[T]
    """

    type: ChangeType
    path: str
    value: Optional[T] = None
    old_value: Optional[T] = None


@runtime_checkable
class Observer(Protocol[T]):
    """
    Protocol defining the interface for observers.

    Observers must implement either a synchronous or asynchronous on_change method.
    """

    def on_change(self, change: Change[T]) -> Union[None, Awaitable[None]]:
        """
        Called when an observed value changes.

        :param change: Description of what changed
        :type change: Change[T]
        """
        ...


class Observable(Generic[T]):
    """
    Base class for objects that can be observed for changes.

    Example::

        class UserData(Observable[dict]):
            def __init__(self):
                super().__init__()
                self._data = {}

            async def update_user(self, user_id: str, data: dict) -> None:
                old_data = self._data.get(user_id)
                self._data[user_id] = data
                await self.notify(Change(
                    type=ChangeType.UPDATE,
                    path=f"users.{user_id}",
                    value=data,
                    old_value=old_data
                ))
    """

    def __init__(self):
        """
        Initialize the observable object.
        """
        self._observers: Set[weakref.ref[Observer[T]]] = set()
        self._lock = asyncio.Lock()
        self._batch_changes: List[Change[T]] = []
        self._in_batch = False

    def add_observer(self, observer: Observer[T]) -> None:
        """
        Add an observer to this observable.

        :param observer: Observer to add
        :type observer: Observer[T]
        """
        self._observers.add(weakref.ref(observer, self._cleanup_observer))

    def remove_observer(self, observer: Observer[T]) -> None:
        """
        Remove an observer from this observable.

        :param observer: Observer to remove
        :type observer: Observer[T]
        """
        ref = next((ref for ref in self._observers if ref() == observer), None)
        if ref is not None:
            self._observers.remove(ref)

    def _cleanup_observer(self, ref: weakref.ref) -> None:
        """
        Clean up observer reference when the observer is garbage collected.

        :param ref: Weak reference to clean up
        :type ref: weakref.ref
        """
        self._observers.discard(ref)

    async def notify(self, change: Change[T]) -> None:
        """
        Notify all observers of a change.

        :param change: Change that occurred
        :type change: Change[T]
        :raises ObservableError: If notification fails
        """
        if self._in_batch:
            self._batch_changes.append(change)
            return

        async with self._lock:
            tasks = []
            for ref in list(self._observers):
                observer = ref()
                if observer is not None:
                    try:
                        result = observer.on_change(change)
                        if asyncio.iscoroutine(result):
                            tasks.append(asyncio.create_task(result))
                    except Exception as e:
                        raise ObservableError(
                            f"Observer notification failed: {e}"
                        ) from e

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def notify_all(self, changes: list[Change[T]]) -> None:
        """
        Notify all observers of multiple changes at once.

        :param changes: List of changes that occurred
        :type changes: list[Change[T]]
        :raises ObservableError: If notification fails
        """
        async with self._lock:
            tasks = []
            for ref in list(self._observers):
                observer = ref()
                if observer is not None:
                    for change in changes:
                        try:
                            result = observer.on_change(change)
                            if asyncio.iscoroutine(result):
                                tasks.append(asyncio.create_task(result))
                        except Exception as e:
                            raise ObservableError(
                                f"Observer notification failed: {e}"
                            ) from e

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    @contextmanager
    async def batch_operations(self):
        """
        Context manager for batching multiple changes into a single notification.

        Example::

            async with observable.batch_operations():
                await observable.update_value("x", 1)
                await observable.update_value("y", 2)
                # Observers will be notified once with both changes
        """
        self._in_batch = True
        self._batch_changes = []
        try:
            yield
        finally:
            self._in_batch = False
            if self._batch_changes:
                await self.notify_all(self._batch_changes)
            self._batch_changes = []


class ObservableValue(Observable[T]):
    """
    A simple observable value container.

    Example::

        value = ObservableValue[int](0)

        @value.on_change
        async def handle_change(change: Change[int]):
            print(f"Value changed from {change.old_value} to {change.value}")

        await value.set(42)
    """

    def __init__(self, initial_value: T):
        """
        Initialize with an initial value.

        :param initial_value: Initial value to store
        :type initial_value: T
        """
        super().__init__()
        self._value = initial_value

    def get(self) -> T:
        """
        Get the current value.

        :return: Current value
        :rtype: T
        """
        return self._value

    async def set(self, value: T) -> None:
        """
        Set a new value and notify observers.

        :param value: New value to set
        :type value: T
        """
        if value != self._value:
            old_value = self._value
            self._value = value
            await self.notify(
                Change(
                    type=ChangeType.UPDATE,
                    path="value",
                    value=value,
                    old_value=old_value,
                )
            )

    def on_change(
        self, callback: Callable[[Change[T]], Union[None, Awaitable[None]]]
    ) -> Callable:
        """
        Decorator for registering a change callback.

        :param callback: Function to call on changes
        :type callback: Callable[[Change[T]], Union[None, Awaitable[None]]]
        :return: The original callback function
        :rtype: Callable

        Example::

            @value.on_change
            async def handle_change(change: Change[int]):
                print(f"Value changed to {change.value}")
        """

        class CallbackObserver:
            def __init__(self, callback):
                self.callback = callback

            def on_change(self, change: Change[T]) -> Union[None, Awaitable[None]]:
                return self.callback(change)

        self.add_observer(CallbackObserver(callback))
        return callback


class ObservableDict(Observable[Dict[str, V]], Dict[str, V]):
    """
    An observable dictionary implementation.

    Example::

        data = ObservableDict[str]()

        @data.on_change
        async def handle_change(change: Change[Dict[str, str]]):
            print(f"Dictionary changed: {change}")

        await data.aset("key", "value")
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the observable dictionary.
        """
        Observable.__init__(self)
        Dict.__init__(self, *args, **kwargs)

    async def aset(self, key: str, value: V) -> None:
        """
        Asynchronously set a dictionary value and notify observers.

        :param key: Key to set
        :type key: str
        :param value: Value to set
        :type value: V
        """
        old_value = self.get(key)
        self[key] = value
        await self.notify(
            Change(
                type=ChangeType.UPDATE if old_value is not None else ChangeType.CREATE,
                path=key,
                value=value,
                old_value=old_value,
            )
        )

    async def adelete(self, key: str) -> None:
        """
        Asynchronously delete a dictionary value and notify observers.

        :param key: Key to delete
        :type key: str
        :raises KeyError: If the key doesn't exist
        """
        if key in self:
            old_value = self[key]
            del self[key]
            await self.notify(
                Change(type=ChangeType.DELETE, path=key, old_value=old_value)
            )
        else:
            raise KeyError(key)

    def on_change(
        self, callback: Callable[[Change[Dict[str, V]]], Union[None, Awaitable[None]]]
    ) -> Callable:
        """
        Decorator for registering a change callback.

        :param callback: Function to call on changes
        :type callback: Callable[[Change[Dict[str, V]]], Union[None, Awaitable[None]]]
        :return: The original callback function
        :rtype: Callable
        """

        class CallbackObserver:
            def __init__(self, callback):
                self.callback = callback

            def on_change(
                self, change: Change[Dict[str, V]]
            ) -> Union[None, Awaitable[None]]:
                return self.callback(change)

        self.add_observer(CallbackObserver(callback))
        return callback
