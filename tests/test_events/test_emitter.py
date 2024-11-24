"""
Test event emitter implementation.
"""

import pytest
from mtaio.events import EventEmitter, Event, EventPriority


@pytest.mark.asyncio
async def test_event_emitter_basic():
    """Test basic event emission."""
    emitter = EventEmitter()
    results = []

    @emitter.on("test_event")
    async def handler(event: Event):
        results.append(event.data)

    await emitter.emit("test_event", "test_data")
    assert results == ["test_data"]


@pytest.mark.asyncio
async def test_event_emitter_priority():
    """Test event handler priority."""
    emitter = EventEmitter()
    results = []

    @emitter.on("test_event", priority=EventPriority.LOW)
    async def low_handler(event: Event):
        results.append("low")

    @emitter.on("test_event", priority=EventPriority.HIGH)
    async def high_handler(event: Event):
        results.append("high")

    await emitter.emit("test_event", None)
    assert results == ["high", "low"]
