"""
Core functionality examples for mtaio library.

This example demonstrates:
- Task execution with concurrency control
- Async queue usage
- Primitive synchronization tools
"""

import asyncio
from mtaio.core import (
    TaskExecutor,
    AsyncQueue,
    Latch,
    PriorityQueue,
)


async def simulate_task(task_id: int, duration: float) -> str:
    """
    Simulate a time-consuming task.

    :param task_id: Task identifier
    :param duration: Task duration in seconds
    :return: Task result message
    """
    await asyncio.sleep(duration)
    return f"Task {task_id} completed in {duration:.1f}s"


async def task_executor_example() -> None:
    """
    Demonstrates TaskExecutor usage for concurrent task execution.
    """
    async with TaskExecutor() as executor:
        # Single task execution
        result = await executor.run(simulate_task(1, 0.5))
        print(result)

        # Concurrent task execution with limit
        tasks = [simulate_task(i, 0.5) for i in range(2, 6)]
        results = await executor.gather(*tasks, limit=2)  # Maximum 2 concurrent tasks
        for result in results:
            print(result)


async def queue_example() -> None:
    """
    Demonstrates async queue usage for producer-consumer pattern.
    """
    queue: AsyncQueue[str] = AsyncQueue(maxsize=3)

    async def producer() -> None:
        """Produce items and put them in the queue."""
        for i in range(5):
            item = f"Item {i}"
            await queue.put(item)
            print(f"Produced: {item}")
            await asyncio.sleep(0.5)

    async def consumer() -> None:
        """Consume items from the queue."""
        while True:
            item = await queue.get()
            print(f"Consumed: {item}")
            queue.task_done()
            await asyncio.sleep(1.0)

    # Run producer and consumer
    consumer_task = asyncio.create_task(consumer())
    await producer()
    await queue.join()
    consumer_task.cancel()


async def priority_queue_example() -> None:
    """
    Demonstrates priority queue usage.
    """
    pq = PriorityQueue[str]()

    # Add items with different priorities
    items = [("Low priority", 3), ("High priority", 1), ("Medium priority", 2)]

    for item, priority in items:
        await pq.put(item, priority)
        print(f"Added: {item} (priority: {priority})")

    # Get items (will come out in priority order)
    while not pq.empty():
        item = await pq.get()
        print(f"Got: {item}")


async def latch_example() -> None:
    """
    Demonstrates countdown latch for synchronization.
    """
    # Create latch with count of 3
    latch = Latch(3)

    async def worker(worker_id: int) -> None:
        """
        Simulate worker task.

        :param worker_id: Worker identifier
        """
        await asyncio.sleep(0.5 * worker_id)
        print(f"Worker {worker_id} completed")
        await latch.count_down()

    # Start workers
    workers = [worker(i) for i in range(3)]
    await asyncio.gather(*workers)

    # Wait for all workers
    await latch.wait()
    print("All workers completed")


async def main() -> None:
    """
    Run all core functionality examples.
    """
    print("=== Task Executor Example ===")
    await task_executor_example()

    print("\n=== Queue Example ===")
    await queue_example()

    print("\n=== Priority Queue Example ===")
    await priority_queue_example()

    print("\n=== Latch Example ===")
    await latch_example()


if __name__ == "__main__":
    asyncio.run(main())
