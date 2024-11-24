"""
Decorators for adapting synchronous functions and iterables to asynchronous equivalents.

This module provides decorators for:

* Converting synchronous functions to asynchronous functions
* Converting synchronous iterables to asynchronous iterables
* Converting synchronous context managers to asynchronous context managers
* Adapting callback-based APIs to async/await style
"""

import itertools
from typing import (
    TypeVar,
    Generic,
    Callable,
    AsyncIterator,
    AsyncIterable,
    Awaitable,
    Optional,
    Union,
    Any,
    Type,
    Iterable,
    cast,
    ContextManager,
)
import asyncio
import functools
import inspect
from concurrent.futures import ThreadPoolExecutor
from ..exceptions import AdapterError

T = TypeVar("T")
U = TypeVar("U")
R = TypeVar("R")


def async_adapter(
    func: Optional[Callable[..., R]] = None,
    *,
    executor: Optional[ThreadPoolExecutor] = None,
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> Union[
    Callable[..., Awaitable[R]],
    Callable[[Callable[..., R]], Callable[..., Awaitable[R]]],
]:
    """
    Convert a synchronous function to an asynchronous function.

    Can be used as a decorator with or without parameters.

    :param func: Function to convert
    :type func: Optional[Callable[..., R]]
    :param executor: ThreadPoolExecutor to use for running the function
    :type executor: Optional[ThreadPoolExecutor]
    :param loop: Event loop to use
    :type loop: Optional[asyncio.AbstractEventLoop]
    :return: Async version of the function
    :rtype: Union[Callable[..., Awaitable[R]], Callable[[Callable[..., R]], Callable[..., Awaitable[R]]]]

    Example::

        @async_adapter
        def slow_operation(x: int) -> int:
            time.sleep(1)
            return x * 2

        # With parameters
        @async_adapter(executor=ThreadPoolExecutor())
        def another_operation(x: int) -> int:
            time.sleep(1)
            return x * 3
    """

    def decorator(func: Callable[..., R]) -> Callable[..., Awaitable[R]]:
        if asyncio.iscoroutinefunction(func):
            return func

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> R:
            loop = asyncio.get_running_loop()
            if inspect.isgeneratorfunction(func):
                raise AdapterError(
                    "Cannot adapt generator function. Use async_iterator instead."
                )
            try:
                return await loop.run_in_executor(
                    executor, functools.partial(func, *args, **kwargs)
                )
            except Exception as e:
                raise AdapterError(f"Error in adapted function: {str(e)}") from e

        return wrapper

    if func is None:
        return decorator
    return decorator(func)


def async_iterator(
    func: Optional[Union[Callable[..., Iterable[T]], Iterable[T]]] = None,
    *,
    chunk_size: int = 1,
    executor: Optional[ThreadPoolExecutor] = None,
) -> Union[
    AsyncIterator[T],
    Callable[[Union[Callable[..., Iterable[T]], Iterable[T]]], AsyncIterator[T]],
]:
    """
    Convert a synchronous iterable or iterable-returning function to an async iterator.

    :param func: Iterable or function returning an iterable
    :type func: Optional[Union[Callable[..., Iterable[T]], Iterable[T]]]
    :param chunk_size: Number of items to process at once
    :type chunk_size: int
    :param executor: ThreadPoolExecutor to use
    :type executor: Optional[ThreadPoolExecutor]
    :return: Async iterator
    :rtype: Union[AsyncIterator[T], Callable[[Union[Callable[..., Iterable[T]], Iterable[T]]], AsyncIterator[T]]]

    Example::

        @async_iterator(chunk_size=10)
        def generate_data() -> Iterable[int]:
            return range(100)

        # Or directly with an iterable
        async_iter = async_iterator(range(100))
    """

    def decorator(
        obj: Union[Callable[..., Iterable[T]], Iterable[T]]
    ) -> AsyncIterator[T]:
        if isinstance(obj, AsyncIterable):
            return obj.__aiter__()

        if isinstance(obj, Iterable):
            iterable = obj
        elif callable(obj):
            iterable = obj()
        else:
            raise AdapterError(f"Cannot adapt {type(obj)} to async iterator")

        class AsyncIteratorWrapper:
            def __init__(self):
                self._iterator = iter(iterable)
                self._executor = executor or ThreadPoolExecutor()

            def __aiter__(self):
                return self

            async def __anext__(self) -> T:
                try:
                    loop = asyncio.get_running_loop()
                    chunk = await loop.run_in_executor(
                        self._executor,
                        lambda: list(itertools.islice(self._iterator, chunk_size)),
                    )
                    if not chunk:
                        raise StopAsyncIteration
                    return chunk[0] if chunk_size == 1 else chunk
                except StopIteration:
                    raise StopAsyncIteration
                except Exception as e:
                    raise AdapterError(f"Error in async iterator: {str(e)}") from e

        return AsyncIteratorWrapper()

    if func is None:
        return decorator
    return decorator(func)


class async_context_adapter:
    """
    Convert a synchronous context manager to an asynchronous context manager.

    Example::

        @async_context_adapter
        @contextmanager
        def managed_resource():
            resource = acquire_resource()
            try:
                yield resource
            finally:
                release_resource(resource)
    """

    def __init__(
        self,
        context_manager: Union[
            Type[ContextManager[T]], Callable[..., ContextManager[T]]
        ],
        executor: Optional[ThreadPoolExecutor] = None,
    ):
        """
        Initialize the adapter.

        :param context_manager: Context manager to adapt
        :type context_manager: Union[Type[ContextManager[T]], Callable[..., ContextManager[T]]]
        :param executor: ThreadPoolExecutor to use
        :type executor: Optional[ThreadPoolExecutor]
        """
        self.context_manager = context_manager
        self.executor = executor
        functools.update_wrapper(self, context_manager)

    async def __aenter__(self) -> T:
        """
        Enter the async context.

        :return: Context value
        :rtype: T
        """
        loop = asyncio.get_running_loop()
        try:
            self.cm = self.context_manager()
            return await loop.run_in_executor(self.executor, self.cm.__enter__)
        except Exception as e:
            raise AdapterError(f"Error entering context: {str(e)}") from e

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> Optional[bool]:
        """
        Exit the async context.

        :param exc_type: Exception type if an error occurred
        :type exc_type: Optional[Type[BaseException]]
        :param exc_val: Exception value if an error occurred
        :type exc_val: Optional[BaseException]
        :param exc_tb: Exception traceback if an error occurred
        :type exc_tb: Optional[Any]
        :return: True if exception was handled
        :rtype: Optional[bool]
        """
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(
                self.executor, lambda: self.cm.__exit__(exc_type, exc_val, exc_tb)
            )
        except Exception as e:
            raise AdapterError(f"Error exiting context: {str(e)}") from e


class CallbackAdapter(Generic[T]):
    """
    Adapt callback-based APIs to async/await style.

    Example::

        def legacy_api(callback):
            # Simulate async operation
            threading.Timer(1.0, lambda: callback(42)).start()

        async def modern_api():
            adapter = CallbackAdapter[int]()
            legacy_api(adapter.callback)
            return await adapter.wait()
    """

    def __init__(self, timeout: Optional[float] = None):
        """
        Initialize the adapter.

        :param timeout: Maximum time to wait for callback
        :type timeout: Optional[float]
        """
        self._future: asyncio.Future[T] = asyncio.Future()
        self._timeout = timeout

    def callback(self, *args: Any, **kwargs: Any) -> None:
        """
        Callback function to be passed to the API.

        :param args: Positional arguments from callback
        :type args: Any
        :param kwargs: Keyword arguments from callback
        :type kwargs: Any
        """
        if not self._future.done():
            if len(args) == 1 and not kwargs:
                self._future.set_result(args[0])
            else:
                self._future.set_result(cast(T, (args, kwargs)))

    def error_callback(self, error: Exception) -> None:
        """
        Error callback function.

        :param error: Error that occurred
        :type error: Exception
        """
        if not self._future.done():
            self._future.set_exception(error)

    async def wait(self) -> T:
        """
        Wait for the callback to be called.

        :return: Result from callback
        :rtype: T
        :raises asyncio.TimeoutError: If timeout occurs
        """
        try:
            return await asyncio.wait_for(self._future, self._timeout)
        except asyncio.TimeoutError as e:
            raise AdapterError("Callback timeout") from e


def async_retry(
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Union[Type[Exception], tuple[Type[Exception], ...]] = Exception,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Retry an async function on failure.

    :param retries: Number of retries
    :type retries: int
    :param delay: Initial delay between retries
    :type delay: float
    :param backoff: Backoff multiplier
    :type backoff: float
    :param exceptions: Exception types to catch
    :type exceptions: Union[Type[Exception], tuple[Type[Exception], ...]]
    :return: Decorated function
    :rtype: Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]

    Example::

        @async_retry(retries=3, delay=1.0, exceptions=(ConnectionError,))
        async def fetch_data():
            # ... potentially failing operation
            pass
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            current_delay = delay
            last_exception: Optional[Exception] = None

            for attempt in range(retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == retries:
                        break
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

            raise AdapterError(
                f"Function failed after {retries} retries"
            ) from last_exception

        return wrapper

    return decorator


def async_timeout(
    timeout: float, message: Optional[str] = None
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Add timeout to an async function.

    :param timeout: Timeout in seconds
    :type timeout: float
    :param message: Custom timeout message
    :type message: Optional[str]
    :return: Decorated function
    :rtype: Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]

    Example::

        @async_timeout(5.0, "Operation timed out")
        async def slow_operation():
            # ... potentially slow operation
            pass
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
            except asyncio.TimeoutError as e:
                raise AdapterError(
                    message or f"Operation timed out after {timeout} seconds"
                ) from e

        return wrapper

    return decorator
