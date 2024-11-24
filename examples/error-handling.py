"""
Error handling examples for mtaio library.

This example demonstrates:
- Exception hierarchy usage
- Error recovery patterns
- Custom error handling
"""

import asyncio
from typing import Optional
from mtaio.exceptions import (
    MTAIOError,
    ExecutionError,
    TimeoutError,
    CacheError,
)


async def basic_error_handling() -> None:
    """
    Demonstrates basic error handling patterns.
    """
    try:
        # Simulate operation that might fail
        raise ExecutionError("Task execution failed")

    except ExecutionError as e:
        print(f"Execution error: {e}")
    except TimeoutError as e:
        print(f"Timeout error: {e}")
    except MTAIOError as e:
        print(f"Generic MTAIO error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


async def retry_pattern(max_attempts: int = 3) -> Optional[str]:
    """
    Demonstrates retry pattern with exponential backoff.

    :param max_attempts: Maximum number of retry attempts
    :return: Operation result or None on failure
    """
    attempt = 0
    while attempt < max_attempts:
        try:
            # Simulate unstable operation
            if attempt < 2:  # Fail first two attempts
                raise ConnectionError("Connection failed")
            return "Operation succeeded"

        except ConnectionError as e:
            attempt += 1
            if attempt == max_attempts:
                print(f"Failed after {attempt} attempts: {e}")
                return None

            # Exponential backoff
            wait_time = 2**attempt
            print(f"Attempt {attempt} failed, retrying in {wait_time}s")
            await asyncio.sleep(wait_time)


async def error_recovery() -> None:
    """
    Demonstrates error recovery patterns.
    """

    async def primary_operation() -> str:
        raise CacheError("Primary cache unavailable")

    async def fallback_operation() -> str:
        return "Fallback value"

    try:
        result = await primary_operation()
    except CacheError:
        try:
            result = await fallback_operation()
            print(f"Recovered using fallback: {result}")
        except Exception as e:
            print(f"Fallback also failed: {e}")


class ErrorBoundary:
    """
    Error boundary pattern implementation.
    """

    def __init__(self, handler: Optional[callable] = None):
        """
        Initialize error boundary.

        :param handler: Optional error handler function
        """
        self.handler = handler or self.default_handler

    async def default_handler(self, error: Exception) -> None:
        """
        Default error handler.

        :param error: Error to handle
        """
        print(f"Error boundary caught: {error}")

    async def __aenter__(self) -> "ErrorBoundary":
        """Enter error boundary context."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """
        Exit error boundary context.

        :return: True if error was handled
        """
        if exc_val is not None:
            await self.handler(exc_val)
            return True
        return False


async def error_boundary_example() -> None:
    """
    Demonstrates error boundary pattern usage.
    """

    async def risky_operation() -> None:
        raise ValueError("Something went wrong")

    # Using default handler
    async with ErrorBoundary():
        await risky_operation()

    # Using custom handler
    async def custom_handler(error: Exception) -> None:
        print(f"Custom handler: {error}")

    async with ErrorBoundary(custom_handler):
        await risky_operation()


async def main() -> None:
    """
    Run all error handling examples.
    """
    print("=== Basic Error Handling ===")
    await basic_error_handling()

    print("\n=== Retry Pattern ===")
    await retry_pattern()

    print("\n=== Error Recovery ===")
    await error_recovery()

    print("\n=== Error Boundary ===")
    await error_boundary_example()


if __name__ == "__main__":
    asyncio.run(main())
