"""
Asynchronous data pipeline implementation for data processing and transformation.

This module provides components for building asynchronous data processing pipelines:

* Pipeline: Main pipeline class for sequential data processing
* Stage: Protocol defining the pipeline stage interface
* BatchStage: Base class for batch processing stages
* FilterStage: Stage for filtering data
* MapStage: Stage for transforming data
"""

from typing import (
    TypeVar,
    Generic,
    Protocol,
    Callable,
    Awaitable,
    List,
    Optional,
    Union,
    Iterable,
    AsyncIterable,
    runtime_checkable,
)
import asyncio
from collections import deque
from ..exceptions import PipelineError, StageError

T = TypeVar("T")
U = TypeVar("U")


@runtime_checkable
class Stage(Protocol[T, U]):
    """
    Protocol defining the interface for pipeline stages.

    Pipeline stages must implement an asynchronous process method.
    """

    async def process(self, data: T) -> U:
        """
        Process a single item of data.

        :param data: Input data to process
        :type data: T
        :return: Processed data
        :rtype: U
        :raises StageError: If processing fails
        """
        ...

    async def setup(self) -> None:
        """
        Set up the stage before processing begins.

        :raises StageError: If setup fails
        """
        ...

    async def cleanup(self) -> None:
        """
        Clean up the stage after processing is complete.

        :raises StageError: If cleanup fails
        """
        ...


class Pipeline(Generic[T, U]):
    """
    Main pipeline class for sequential data processing.

    Example::

        pipeline = Pipeline()
        pipeline.add_stage(MapStage(lambda x: x * 2))
        pipeline.add_stage(FilterStage(lambda x: x > 5))

        async with pipeline:
            result = await pipeline.process(3)
    """

    def __init__(self, buffer_size: int = 0):
        """
        Initialize the pipeline.

        :param buffer_size: Size of the buffer between stages (0 for unbuffered)
        :type buffer_size: int
        """
        self._stages: List[Stage] = []
        self._buffer_size = buffer_size
        self._running = False

    def add_stage(self, stage: Stage) -> "Pipeline":
        """
        Add a processing stage to the pipeline.

        :param stage: Stage to add
        :type stage: Stage
        :return: Self for method chaining
        :rtype: Pipeline
        :raises PipelineError: If pipeline is already running
        """
        if self._running:
            raise PipelineError("Cannot add stages while pipeline is running")
        self._stages.append(stage)
        return self

    async def process(self, data: T) -> U:
        """
        Process data through the pipeline.

        :param data: Input data to process
        :type data: T
        :return: Processed data
        :rtype: U
        :raises PipelineError: If processing fails
        """
        if not self._running:
            raise PipelineError("Pipeline is not running")

        current = data
        try:
            for stage in self._stages:
                current = await stage.process(current)
            return current
        except Exception as e:
            raise PipelineError(f"Pipeline processing failed: {e}") from e

    async def process_many(
        self, items: Union[Iterable[T], AsyncIterable[T]]
    ) -> List[U]:
        """
        Process multiple items through the pipeline.

        :param items: Input items to process
        :type items: Union[Iterable[T], AsyncIterable[T]]
        :return: List of processed items
        :rtype: List[U]
        :raises PipelineError: If processing fails
        """
        results = []
        if isinstance(items, AsyncIterable):
            async for item in items:
                result = await self.process(item)
                results.append(result)
        else:
            for item in items:
                result = await self.process(item)
                results.append(result)
        return results

    async def __aenter__(self) -> "Pipeline[T, U]":
        """
        Set up the pipeline and all stages.

        :return: Self
        :rtype: Pipeline[T, U]
        :raises PipelineError: If setup fails
        """
        try:
            for stage in self._stages:
                await stage.setup()
            self._running = True
            return self
        except Exception as e:
            raise PipelineError(f"Pipeline setup failed: {e}") from e

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Clean up the pipeline and all stages.

        :raises PipelineError: If cleanup fails
        """
        self._running = False
        try:
            for stage in reversed(self._stages):
                await stage.cleanup()
        except Exception as e:
            raise PipelineError(f"Pipeline cleanup failed: {e}") from e


class BatchStage(Stage[T, U]):
    """
    Base class for stages that process data in batches.

    Example::

        class AverageBatchStage(BatchStage[float, float]):
            async def process_batch(self, batch):
                return sum(batch) / len(batch)
    """

    def __init__(self, batch_size: int):
        """
        Initialize the batch stage.

        :param batch_size: Size of batches to process
        :type batch_size: int
        """
        self.batch_size = batch_size
        self._batch: List[T] = []
        self._results: deque[U] = deque()

    async def process(self, data: T) -> Optional[U]:
        """
        Process a single item, potentially as part of a batch.

        :param data: Input data to process
        :type data: T
        :return: Processed data if batch is complete, None otherwise
        :rtype: Optional[U]
        """
        self._batch.append(data)

        if len(self._batch) >= self.batch_size:
            result = await self.process_batch(self._batch)
            self._batch = []
            return result
        return None

    async def process_batch(self, batch: List[T]) -> U:
        """
        Process a complete batch of data.

        :param batch: Batch of data to process
        :type batch: List[T]
        :return: Processed batch result
        :rtype: U
        :raises NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError

    async def cleanup(self) -> None:
        """
        Process any remaining items in the final batch.
        """
        if self._batch:
            await self.process_batch(self._batch)
            self._batch = []


class FilterStage(Stage[T, T]):
    """
    Stage that filters items based on a predicate.

    Example::

        pipeline.add_stage(FilterStage(lambda x: x > 0))
    """

    def __init__(
        self, predicate: Union[Callable[[T], bool], Callable[[T], Awaitable[bool]]]
    ):
        """
        Initialize the filter stage.

        :param predicate: Function that returns True for items to keep
        :type predicate: Union[Callable[[T], bool], Callable[[T], Awaitable[bool]]]
        """
        self.predicate = predicate

    async def process(self, data: T) -> Optional[T]:
        """
        Filter an item based on the predicate.

        :param data: Input data to filter
        :type data: T
        :return: Input data if predicate is True, None otherwise
        :rtype: Optional[T]
        """
        result = self.predicate(data)
        if asyncio.iscoroutine(result):
            result = await result
        return data if result else None

    async def setup(self) -> None:
        """No setup required for filter stage."""
        pass

    async def cleanup(self) -> None:
        """No cleanup required for filter stage."""
        pass


class MapStage(Stage[T, U]):
    """
    Stage that transforms items using a mapping function.

    Example::

        pipeline.add_stage(MapStage(lambda x: str(x)))
    """

    def __init__(self, func: Union[Callable[[T], U], Callable[[T], Awaitable[U]]]):
        """
        Initialize the map stage.

        :param func: Function to transform items
        :type func: Union[Callable[[T], U], Callable[[T], Awaitable[U]]]
        """
        self.func = func

    async def process(self, data: T) -> U:
        """
        Transform an item using the mapping function.

        :param data: Input data to transform
        :type data: T
        :return: Transformed data
        :rtype: U
        """
        result = self.func(data)
        if asyncio.iscoroutine(result):
            result = await result
        return result

    async def setup(self) -> None:
        """No setup required for map stage."""
        pass

    async def cleanup(self) -> None:
        """No cleanup required for map stage."""
        pass


class BufferedPipeline(Pipeline[T, U]):
    """
    Pipeline implementation with buffered stages.

    Example::

        pipeline = BufferedPipeline(buffer_size=100)
        pipeline.add_stage(SlowProcessingStage())
        async with pipeline:
            async for result in pipeline.stream([1, 2, 3, 4, 5]):
                print(result)
    """

    def __init__(self, buffer_size: int = 100):
        """
        Initialize the buffered pipeline.

        :param buffer_size: Size of buffers between stages
        :type buffer_size: int
        """
        super().__init__()
        self.buffer_size = buffer_size
        self._queues: List[asyncio.Queue] = []

    def add_stage(self, stage: Stage) -> "BufferedPipeline":
        """
        Add a stage to the pipeline.

        :param stage: Stage to add
        :type stage: Stage
        :return: Self for method chaining
        :rtype: BufferedPipeline
        """
        super().add_stage(stage)
        self._queues.append(asyncio.Queue(maxsize=self.buffer_size))
        return self

    async def _process_stage(
        self, stage: Stage, input_queue: asyncio.Queue, output_queue: asyncio.Queue
    ) -> None:
        """
        Process items through a single stage.

        :param stage: Stage to process through
        :type stage: Stage
        :param input_queue: Queue to read items from
        :type input_queue: asyncio.Queue
        :param output_queue: Queue to write results to
        :type output_queue: asyncio.Queue
        """
        while True:
            try:
                if output_queue.full():
                    await asyncio.sleep(0.1)
                    continue

                item = await input_queue.get()
                if item is None:  # End of stream
                    await output_queue.put(None)
                    break

                result = await stage.process(item)
                if result is not None:
                    await output_queue.put(result)

                input_queue.task_done()
            except Exception as e:
                await output_queue.put(StageError(f"Stage processing failed: {e}", stage=stage))
                break

    async def stream(
        self, items: Union[Iterable[T], AsyncIterable[T]]
    ) -> AsyncIterable[U]:
        """
        Stream items through the pipeline.

        :param items: Input items to process
        :type items: Union[Iterable[T], AsyncIterable[T]]
        :return: AsyncIterable of processed results
        :rtype: AsyncIterable[U]
        :raises PipelineError: If processing fails
        """
        if not self._running:
            raise PipelineError("Pipeline is not running")

        # Create stage processing tasks
        tasks = []
        for i, stage in enumerate(self._stages):
            input_queue = self._queues[i]
            output_queue = (
                self._queues[i + 1] if i < len(self._stages) - 1 else asyncio.Queue()
            )

            task = asyncio.create_task(
                self._process_stage(stage, input_queue, output_queue)
            )
            tasks.append(task)

        # Feed input items
        input_queue = self._queues[0]
        try:
            if isinstance(items, AsyncIterable):
                async for item in items:
                    await input_queue.put(item)
            else:
                for item in items:
                    await input_queue.put(item)
        finally:
            await input_queue.put(None)  # End of stream marker

        # Stream results
        output_queue = self._queues[-1]
        while True:
            result = await output_queue.get()
            if result is None:  # End of stream
                break
            if isinstance(result, Exception):
                raise result
            yield result

        # Clean up tasks
        await asyncio.gather(*tasks)
