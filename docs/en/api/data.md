# Data API Reference

The `mtaio.data` module provides components for data processing and transformation, including pipelines, streams, and observables.

## Pipeline Processing

### Pipeline

The `Pipeline` class provides a framework for sequential data processing through configurable stages.

#### Basic Usage

```python
from mtaio.data import Pipeline, Stage

# Define processing stages
class ValidationStage(Stage[dict, dict]):
    async def process(self, data: dict) -> dict:
        if "id" not in data:
            raise ValueError("Missing id field")
        return data

class EnrichmentStage(Stage[dict, dict]):
    async def process(self, data: dict) -> dict:
        data["timestamp"] = time.time()
        return data

# Create and use pipeline
async def process_data():
    pipeline = Pipeline()
    pipeline.add_stage(ValidationStage())
    pipeline.add_stage(EnrichmentStage())
    
    async with pipeline:
        result = await pipeline.process({"id": "123"})
```

#### Class Reference

```python
class Pipeline[T, U]:
    def __init__(self, buffer_size: int = 0):
        """
        Initialize pipeline.

        Args:
            buffer_size: Size of the buffer between stages
        """

    def add_stage(self, stage: Stage) -> "Pipeline":
        """Add a processing stage."""
        
    async def process(self, data: T) -> U:
        """Process a single item through the pipeline."""

    async def process_many(
        self,
        items: Union[Iterable[T], AsyncIterable[T]]
    ) -> List[U]:
        """Process multiple items through the pipeline."""
```

### Stage

Base class for pipeline stages.

```python
from mtaio.data import Stage

class CustomStage(Stage[T, U]):
    async def process(self, data: T) -> U:
        """Process a single item."""
        return processed_data

    async def setup(self) -> None:
        """Called when pipeline starts."""
        pass

    async def cleanup(self) -> None:
        """Called when pipeline ends."""
        pass
```

### Provided Stages

#### BatchStage

Processes data in batches.

```python
from mtaio.data import BatchStage

class AverageBatchStage(BatchStage[float, float]):
    def __init__(self, batch_size: int = 10):
        super().__init__(batch_size)
    
    async def process_batch(self, batch: List[float]) -> float:
        return sum(batch) / len(batch)
```

#### FilterStage

Filters data based on a predicate.

```python
from mtaio.data import FilterStage

# Create filter stage
filter_stage = FilterStage(lambda x: x > 0)

# Or with async predicate
async def async_predicate(x):
    return x > await get_threshold()

filter_stage = FilterStage(async_predicate)
```

#### MapStage

Transforms data using a mapping function.

```python
from mtaio.data import MapStage

# Create map stage
map_stage = MapStage(lambda x: x * 2)

# Or with async mapping
async def async_transform(x):
    return await process_value(x)

map_stage = MapStage(async_transform)
```

## Stream Processing

### Stream

The `Stream` class provides a fluent interface for processing sequences of data.

#### Basic Usage

```python
from mtaio.data import Stream

async def process_stream():
    stream = Stream.from_iterable([1, 2, 3, 4, 5])
    
    result = await (stream
        .map(lambda x: x * 2)
        .filter(lambda x: x > 5)
        .reduce(lambda acc, x: acc + x))
```

#### Class Reference

```python
class Stream[T]:
    @classmethod
    def from_iterable(
        cls,
        iterable: Union[Iterable[T], AsyncIterable[T]]
    ) -> "Stream[T]":
        """Create stream from iterable."""

    def map(
        self,
        func: Union[Callable[[T], U], Callable[[T], Awaitable[U]]]
    ) -> "Stream[U]":
        """Transform items using mapping function."""

    def filter(
        self,
        predicate: Union[Callable[[T], bool], Callable[[T], Awaitable[bool]]]
    ) -> "Stream[T]":
        """Filter items using predicate."""

    async def reduce(
        self,
        func: Union[Callable[[U, T], U], Callable[[U, T], Awaitable[U]]],
        initial: Optional[U] = None,
    ) -> U:
        """Reduce stream to single value."""
```

### Stream Operations

#### Windowing

```python
from mtaio.data import Stream

async def window_example():
    stream = Stream.from_iterable(range(10))
    
    # Sliding window
    async for window in stream.window(size=3, step=1):
        print(f"Window: {window}")  # [0,1,2], [1,2,3], ...
```

#### Batching

```python
from mtaio.data import Stream

async def batch_example():
    stream = Stream.from_iterable(range(10))
    
    # Process in batches
    async for batch in stream.batch(size=3):
        print(f"Batch: {batch}")  # [0,1,2], [3,4,5], ...
```

## Observable Pattern

### Observable

The `Observable` class implements the observer pattern for reactive data processing.

#### Basic Usage

```python
from mtaio.data import Observable, Change, ChangeType

class DataStore(Observable[dict]):
    def __init__(self):
        super().__init__()
        self._data = {}
    
    async def update(self, key: str, value: Any) -> None:
        old_value = self._data.get(key)
        self._data[key] = value
        
        await self.notify(Change(
            type=ChangeType.UPDATE,
            path=f"data.{key}",
            value=value,
            old_value=old_value
        ))
```

#### Observers

```python
# Add observer
@data_store.on_change
async def handle_change(change: Change[dict]):
    print(f"Value changed: {change.value}")

# One-time observer
@data_store.once
async def handle_first_change(change: Change[dict]):
    print("First change only")
```

### Batch Operations

```python
from mtaio.data import Observable

async def batch_updates():
    store = DataStore()
    
    async with store.batch_operations():
        await store.update("key1", "value1")
        await store.update("key2", "value2")
        # Observers notified once with all changes
```

## Best Practices

### Pipeline Design

```python
# Use type hints for clarity
class ProcessingPipeline(Pipeline[dict, dict]):
    def __init__(self):
        super().__init__()
        self.add_stage(ValidationStage())
        self.add_stage(TransformationStage())
        self.add_stage(EnrichmentStage())

# Handle cleanup properly
async with ProcessingPipeline() as pipeline:
    results = await pipeline.process_many(items)
```

### Stream Processing

```python
# Chain operations efficiently
result = await (Stream.from_iterable(data)
    .filter(is_valid)
    .map(transform)
    .batch(100)
    .reduce(aggregate))

# Use async predicates when needed
async def is_valid(item: dict) -> bool:
    return await validate(item)
```

### Observable Implementation

```python
# Implement custom observable
class DataManager(Observable[T]):
    def __init__(self):
        super().__init__()
        self._cleanup_handlers = []
    
    async def cleanup(self):
        for handler in self._cleanup_handlers:
            self.remove_observer(handler)
```

## Performance Considerations

1. **Pipeline Buffering**
   ```python
   # Use appropriate buffer sizes
   pipeline = Pipeline(buffer_size=1000)
   ```

2. **Batch Processing**
   ```python
   # Process data in optimal batch sizes
   async for batch in stream.batch(size=optimal_batch_size):
       await process_batch(batch)
   ```

3. **Observer Cleanup**
   ```python
   # Remove observers when no longer needed
   observable.remove_observer(handler)
   ```

## See Also

- [Core API Reference](core.md) for basic functionality
- [Cache API Reference](cache.md) for caching operations
- [Events API Reference](events.md) for event handling
- [Examples Repository](https://github.com/t3tra-dev/mtaio/tree/main/examples/data.py)
