# Events API Reference

The `mtaio.events` module provides a robust event handling system for building event-driven applications.

## EventEmitter

### Basic Usage

```python
from mtaio.events import EventEmitter

# Create emitter
emitter = EventEmitter()

# Define handler
@emitter.on("user_login")
async def handle_login(event):
    user = event.data
    print(f"User {user['name']} logged in")

# Emit event
await emitter.emit("user_login", {
    "name": "John",
    "id": "123"
})
```

### Class Reference

```python
class EventEmitter:
    def __init__(self):
        """Initialize event emitter."""
    
    def on(
        self,
        event_name: str,
        priority: EventPriority = EventPriority.NORMAL
    ) -> Callable:
        """
        Decorator to register an event handler.

        Args:
            event_name: Name of the event to handle
            priority: Handler priority level

        Returns:
            Decorated event handler
        """
    
    def once(
        self,
        event_name: str,
        priority: EventPriority = EventPriority.NORMAL
    ) -> Callable:
        """Register one-time event handler."""
    
    async def emit(
        self,
        event_name: str,
        data: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Emit an event.

        Args:
            event_name: Name of the event
            data: Event data
            metadata: Optional event metadata
        """
```

## Event Types

### Event

Base event container class.

```python
from mtaio.events import Event, ChangeType

@dataclass
class Event[T]:
    name: str              # Event name
    data: T               # Event data
    propagate: bool = True # Whether to continue propagation
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### EventPriority

Priority levels for event handlers.

```python
class EventPriority(Enum):
    LOWEST = auto()   # Lowest priority
    LOW = auto()      # Low priority
    NORMAL = auto()   # Normal priority
    HIGH = auto()     # High priority
    HIGHEST = auto()  # Highest priority
    MONITOR = auto()  # Monitoring only
```

## Advanced Features

### Event Filtering

Filter events based on conditions:

```python
from mtaio.events import EventEmitter

emitter = EventEmitter()

# Create filtered emitter
filtered = emitter.filter(
    lambda event: event.data.get("priority") == "high"
)

@filtered.on("alert")
async def handle_high_priority_alert(event):
    alert = event.data
    print(f"High priority alert: {alert['message']}")
```

### Event Transformation

Transform events before handling:

```python
from mtaio.events import EventEmitter, Event

# Create transformed emitter
transformed = emitter.map(
    lambda event: Event(
        name=event.name,
        data={**event.data, "processed": True}
    )
)

@transformed.on("data_event")
async def handle_processed_data(event):
    # Handle transformed event
    pass
```

### Batch Operations

Group multiple events:

```python
from mtaio.events import EventEmitter

emitter = EventEmitter()

async def batch_operations():
    async with emitter.batch_operations():
        # Events are batched
        await emitter.emit("event1", data1)
        await emitter.emit("event2", data2)
        # Handlers are called once with all events
```

### Event Channels

Create event channels for specific purposes:

```python
from mtaio.events import Channel, Subscriber

async def channel_example():
    channel = Channel[str]("notifications")
    
    # Subscribe to channel
    subscriber = await channel.subscribe()
    
    # Publish message
    await channel.publish("Hello subscribers!")
    
    # Receive message
    message = await subscriber.receive()
```

### Topic-based Events

Handle events by topic:

```python
from mtaio.events import Channel

async def topic_example():
    channel = Channel[str]("events")
    
    # Subscribe to specific topics
    subscriber = await channel.subscribe(["user.*", "system.*"])
    
    # Publish to topic
    await channel.publish(
        "User logged in",
        topic="user.login"
    )
```

## Error Handling

### Event Errors

Handle event-related errors:

```python
from mtaio.exceptions import (
    EventError,
    EventEmitError,
    EventHandlerError
)

async def handle_errors():
    try:
        await emitter.emit("event", data)
    except EventEmitError:
        # Handle emission error
        pass
    except EventHandlerError:
        # Handle handler error
        pass
```

### Error Events

Emit error events:

```python
@emitter.on("error")
async def handle_error(event):
    error = event.data
    print(f"Error occurred: {error}")

# Emit error event
try:
    await process_data()
except Exception as e:
    await emitter.emit("error", e)
```

## Best Practices

### Event Handler Organization

```python
class UserEventHandlers:
    def __init__(self, emitter: EventEmitter):
        self.emitter = emitter
        self.setup_handlers()
    
    def setup_handlers(self):
        @self.emitter.on("user.created")
        async def handle_user_created(event):
            pass
        
        @self.emitter.on("user.updated")
        async def handle_user_updated(event):
            pass

# Usage
handlers = UserEventHandlers(emitter)
```

### Resource Management

```python
class EventManager:
    def __init__(self):
        self.emitter = EventEmitter()
        self._handlers = []
    
    def register_handler(self, event: str, handler: Callable):
        self._handlers.append((event, handler))
        self.emitter.on(event)(handler)
    
    async def cleanup(self):
        for event, handler in self._handlers:
            self.emitter.remove_listener(event, handler)
```

### Performance Optimization

1. **Event Batching**
   ```python
   async with emitter.batch_operations():
       for item in items:
           await emitter.emit("item.processed", item)
   ```

2. **Priority Handling**
   ```python
   @emitter.on("critical", priority=EventPriority.HIGHEST)
   async def handle_critical(event):
       # Handle critical events first
       pass
   ```

3. **Event Filtering**
   ```python
   # Filter events early
   filtered = emitter.filter(lambda e: e.data.get("important"))
   
   @filtered.on("event")
   async def handle_important_events(event):
       pass
   ```

## Examples

### Event-driven Data Processing

```python
from mtaio.events import EventEmitter

class DataProcessor:
    def __init__(self):
        self.emitter = EventEmitter()
    
    async def process(self, data: dict):
        # Emit preprocessing event
        await self.emitter.emit("process.start", data)
        
        try:
            result = await self.process_data(data)
            await self.emitter.emit("process.complete", result)
        except Exception as e:
            await self.emitter.emit("process.error", e)
```

### Event Monitoring

```python
class EventMonitor:
    def __init__(self, emitter: EventEmitter):
        @emitter.on("*", priority=EventPriority.MONITOR)
        async def monitor_all(event):
            await self.log_event(event)
    
    async def log_event(self, event: Event):
        print(f"Event: {event.name}, Data: {event.data}")
```

## See Also

- [Core API Reference](core.md) for base functionality
- [Decorators API Reference](decorators.md) for decorators
- [Examples Repository](https://github.com/t3tra-dev/mtaio/tree/main/examples/events.py)
