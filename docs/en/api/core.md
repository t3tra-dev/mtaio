# Core API Reference

The `mtaio.core` module provides fundamental components for asynchronous operations, including task execution, queues, and primitive data structures.

## Task Execution

### TaskExecutor

The `TaskExecutor` class provides controlled execution of asynchronous tasks with concurrency limits and resource management.

#### Basic Usage

```python
from mtaio.core import TaskExecutor

async def process_item(item: str) -> str:
    return f"Processed: {item}"

# Basic execution
async with TaskExecutor() as executor:
    # Single task
    result = await executor.run(process_item("data"))
    
    # Multiple tasks with concurrency limit
    items = ["item1", "item2", "item3"]
    results = await executor.gather(
        *(process_item(item) for item in items),
        limit=2  # Maximum 2 concurrent tasks
    )
```

#### Class Reference

```python
class TaskExecutor:
    def __init__(
        self,
        thread_pool: Optional[concurrent.futures.ThreadPoolExecutor] = None
    ):
        """
        Initialize task executor.

        Args:
            thread_pool: Optional thread pool for executing synchronous functions
        """

    async def run(
        self,
        coro: Awaitable[T],
        *,
        timeout: Optional[float] = None
    ) -> T:
        """
        Run a single coroutine with optional timeout.

        Args:
            coro: Coroutine to execute
            timeout: Optional timeout in seconds

        Returns:
            Result of the coroutine

        Raises:
            TimeoutError: If operation times out
            ExecutionError: If execution fails
        """

    async def gather(
        self,
        *coroutines: Coroutine[Any, Any, T],
        limit: Optional[int] = None,
        return_exceptions: bool = False,
    ) -> List[T]:
        """
        Execute multiple coroutines with optional concurrency limit.

        Args:
            *coroutines: Coroutines to execute
            limit: Maximum number of concurrent executions
            return_exceptions: Whether to return exceptions instead of raising

        Returns:
            List of results in the order of input coroutines

        Raises:
            ExecutionError: If execution fails and return_exceptions is False
        """

    async def map(
        self,
        func: AsyncCallable[T],
        *iterables: Any,
        limit: Optional[int] = None,
        return_exceptions: bool = False,
    ) -> List[T]:
        """
        Apply function to every item of iterables concurrently.

        Args:
            func: Async function to apply
            *iterables: Input iterables
            limit: Maximum number of concurrent executions
            return_exceptions: Whether to return exceptions instead of raising

        Returns:
            List of results
        """
```

### Advanced Usage

#### Thread Pool Execution

```python
from mtaio.core import TaskExecutor

async def process_with_thread_pool():
    async with TaskExecutor() as executor:
        # Run CPU-bound function in thread pool
        result = await executor.run_in_thread(
            cpu_intensive_function,
            arg1,
            arg2
        )
```

#### Error Handling

```python
from mtaio.exceptions import ExecutionError, TimeoutError

async def handle_execution_errors():
    try:
        async with TaskExecutor() as executor:
            results = await executor.gather(
                *tasks,
                return_exceptions=True
            )
            
            for result in results:
                if isinstance(result, Exception):
                    print(f"Task failed: {result}")
    except ExecutionError as e:
        print(f"Execution failed: {e}")
```

## Queues

### AsyncQueue

Generic asynchronous queue implementation.

#### Basic Usage

```python
from mtaio.core import AsyncQueue

async def producer_consumer():
    queue: AsyncQueue[str] = AsyncQueue(maxsize=10)
    
    # Producer
    await queue.put("item")
    
    # Consumer
    item = await queue.get()
    queue.task_done()
    
    # Wait for queue to be empty
    await queue.join()
```

#### Class Reference

```python
class AsyncQueue[T]:
    def __init__(self, maxsize: int = 0):
        """
        Initialize async queue.

        Args:
            maxsize: Maximum queue size (0 for unlimited)
        """

    async def put(self, item: T) -> None:
        """Put an item into the queue."""

    async def get(self) -> T:
        """Remove and return an item from the queue."""

    def task_done(self) -> None:
        """Indicate that a formerly enqueued task is complete."""

    async def join(self) -> None:
        """Wait until all items in the queue have been processed."""

    def qsize(self) -> int:
        """Return the current size of the queue."""

    def empty(self) -> bool:
        """Return True if the queue is empty."""

    def full(self) -> bool:
        """Return True if the queue is full."""
```

### Specialized Queues

#### PriorityQueue

Queue that retrieves items based on priority.

```python
from mtaio.core import PriorityQueue

async def priority_queue_example():
    queue: PriorityQueue[str] = PriorityQueue()
    
    # Add items with priority (lower number = higher priority)
    await queue.put("normal task", priority=2)
    await queue.put("urgent task", priority=1)
    
    # Items are retrieved in priority order
    item = await queue.get()  # Returns "urgent task"
```

#### LIFOQueue

Last-In-First-Out queue implementation.

```python
from mtaio.core import LIFOQueue

async def lifo_queue_example():
    stack: LIFOQueue[str] = LIFOQueue()
    
    await stack.put("first")
    await stack.put("second")
    
    item = await stack.get()  # Returns "second"
```

## Synchronization Primitives

### Latch

Countdown latch implementation for synchronization.

```python
from mtaio.core import Latch

async def latch_example():
    # Create latch with count of 3
    latch = Latch(3)
    
    # Decrease count
    await latch.count_down()
    
    # Wait for count to reach 0
    await latch.wait(timeout=5.0)  # Optional timeout
```

#### Class Reference

```python
class Latch:
    def __init__(self, count: int):
        """
        Initialize latch.

        Args:
            count: Initial count
        """

    async def count_down(self) -> None:
        """Decrease the count by one."""

    async def wait(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for count to reach zero.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if count reached zero, False if timeout occurred
        """

    def get_count(self) -> int:
        """Get current count."""
```

## Best Practices

### Resource Management

```python
# Always use async context managers for cleanup
async with TaskExecutor() as executor:
    # Resources are automatically cleaned up
    pass

# Handle queue cleanup
queue = AsyncQueue[str]()
try:
    await queue.put("item")
    item = await queue.get()
finally:
    # Clean up any remaining items
    while not queue.empty():
        await queue.get()
```

### Concurrency Control

```python
# Limit concurrent tasks
async with TaskExecutor() as executor:
    results = await executor.gather(
        *long_running_tasks,
        limit=5  # Prevent too many concurrent tasks
    )

# Control queue size
queue = AsyncQueue[str](maxsize=100)  # Prevent unbounded growth
```

### Error Handling

```python
from mtaio.exceptions import ExecutionError

async def handle_execution():
    try:
        async with TaskExecutor() as executor:
            await executor.run(risky_operation())
    except ExecutionError as e:
        # Handle execution error
        logger.error(f"Execution failed: {e}")
    except TimeoutError as e:
        # Handle timeout
        logger.error(f"Operation timed out: {e}")
```

## Performance Tips

1. **Task Batching**
   ```python
   # Process tasks in batches for better throughput
   async with TaskExecutor() as executor:
       for batch in chunks(tasks, size=10):
           await executor.gather(*batch, limit=5)
   ```

2. **Queue Sizing**
   ```python
   # Set appropriate queue sizes
   queue = AsyncQueue[str](
       maxsize=1000  # Prevent memory issues
   )
   ```

3. **Resource Limits**
   ```python
   # Control resource usage
   executor = TaskExecutor(
       thread_pool=ThreadPoolExecutor(max_workers=4)
   )
   ```

## See Also

- [Cache API Reference](cache.md) for caching functionality
- [Events API Reference](events.md) for event handling
- [Resources API Reference](resources.md) for resource management
- [Examples Repository](https://github.com/t3tra-dev/mtaio/tree/main/examples/core.py)
