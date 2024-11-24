"""
Event handling examples for mtaio library.

This example demonstrates:
- Basic event emitting and handling
- Event filtering and transformation
- Event channels
"""

import asyncio
from typing import Dict, Any, List
from mtaio.events import (
    EventEmitter,
    Event,
    Channel,
    EventPriority,
)


# Define custom event types
class UserEvent:
    """User-related event data."""

    def __init__(self, user_id: str, action: str):
        """
        Initialize user event.

        :param user_id: User identifier
        :param action: Action performed
        """
        self.user_id = user_id
        self.action = action


class SystemEvent:
    """System-related event data."""

    def __init__(self, component: str, status: str):
        """
        Initialize system event.

        :param component: System component name
        :param status: Component status
        """
        self.component = component
        self.status = status


async def basic_events_example() -> None:
    """
    Demonstrates basic event emission and handling.
    """
    emitter = EventEmitter()

    # Register event handlers
    @emitter.on("user_login")
    async def handle_login(event: Event[UserEvent]) -> None:
        user = event.data
        print(f"User {user.user_id} logged in")

    @emitter.on("user_logout")
    async def handle_logout(event: Event[UserEvent]) -> None:
        user = event.data
        print(f"User {user.user_id} logged out")

    # Emit events
    await emitter.emit("user_login", UserEvent("user123", "login"))
    await emitter.emit("user_logout", UserEvent("user123", "logout"))


async def priority_events_example() -> None:
    """
    Demonstrates event handlers with different priorities.
    """
    emitter = EventEmitter()

    @emitter.on("system_status", priority=EventPriority.HIGH)
    async def high_priority_handler(event: Event[SystemEvent]) -> None:
        status = event.data
        print(f"[HIGH] {status.component} status: {status.status}")

    @emitter.on("system_status", priority=EventPriority.NORMAL)
    async def normal_priority_handler(event: Event[SystemEvent]) -> None:
        status = event.data
        print(f"[NORMAL] {status.component} status: {status.status}")

    # Emit system event
    await emitter.emit("system_status", SystemEvent("database", "connected"))


async def filtered_events_example() -> None:
    """
    Demonstrates event filtering.
    """
    emitter = EventEmitter()

    # Create filtered emitter for error events
    error_emitter = emitter.filter(
        lambda e: isinstance(e.data, SystemEvent) and e.data.status == "error"
    )

    @error_emitter.on("system_status")
    async def handle_error(event: Event[SystemEvent]) -> None:
        status = event.data
        print(f"Error in component {status.component}")

    # Emit various events
    await emitter.emit("system_status", SystemEvent("cache", "ok"))
    await emitter.emit("system_status", SystemEvent("network", "error"))


async def channel_example() -> None:
    """
    Demonstrates event channel usage.
    """
    # Create channel for notifications
    channel = Channel[str]("notifications")

    # Create subscriber
    subscriber = await channel.subscribe(["user.*", "system.*"])

    # Start receiving messages in background
    async def receive_messages() -> None:
        async for message in subscriber:
            print(f"Received message on {message.topic}: {message.data}")

    receive_task = asyncio.create_task(receive_messages())

    # Publish messages
    await channel.publish("Hello subscribers!", topic="user.greeting")
    await channel.publish("System starting...", topic="system.startup")

    # Wait a bit and cleanup
    await asyncio.sleep(1)
    receive_task.cancel()


async def event_batching_example() -> None:
    """
    Demonstrates event batching.
    """
    emitter = EventEmitter()

    @emitter.on("batch_complete")
    async def handle_batch(event: Event[List[Dict[str, Any]]]) -> None:
        print(f"Processing batch of {len(event.data)} items")
        for item in event.data:
            print(f"- {item}")

    # Emit batch of events
    async with emitter.batch_operations():
        for i in range(3):
            await emitter.emit("data_item", {"id": i, "value": f"item{i}"})


async def main() -> None:
    """
    Run all event handling examples.
    """
    print("=== Basic Events Example ===")
    await basic_events_example()

    print("\n=== Priority Events Example ===")
    await priority_events_example()

    print("\n=== Filtered Events Example ===")
    await filtered_events_example()

    print("\n=== Channel Example ===")
    await channel_example()

    print("\n=== Event Batching Example ===")
    await event_batching_example()


if __name__ == "__main__":
    asyncio.run(main())
