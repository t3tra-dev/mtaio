"""
Asynchronous channel implementation for data distribution.

This module provides components for distributing data to multiple subscribers:

* Channel: Base channel class for data distribution
* Subscriber: Subscriber interface
* Publisher: Publisher interface
* Topic: Topic-based communication
"""

from contextlib import asynccontextmanager
import time
from typing import (
    TypeVar,
    Generic,
    AsyncIterator,
    Dict,
    Set,
    Optional,
    List,
    Any,
)
from dataclasses import dataclass, field
import asyncio
import weakref
import logging
from ..exceptions import ChannelError, ChannelClosedError

T = TypeVar("T")
logger = logging.getLogger(__name__)


@dataclass
class Message(Generic[T]):
    """
    Message container for channel communication.

    :param data: Message data
    :type data: T
    :param topic: Optional topic name
    :type topic: Optional[str]
    :param metadata: Optional message metadata
    :type metadata: Dict[str, Any]
    """

    data: T
    topic: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class Subscriber(Generic[T]):
    """
    Subscriber class for receiving channel messages.

    :param buffer_size: Size of subscriber's message buffer
    :type buffer_size: int
    """

    def __init__(self, buffer_size: int = 0):
        """Initialize the subscriber."""
        self.queue: asyncio.Queue[Optional[Message[T]]] = asyncio.Queue(buffer_size)
        self.topics: Set[str] = set()
        self._closed = False

    async def receive(self) -> Message[T]:
        """
        Receive the next message.

        :return: Next message
        :rtype: Message[T]
        :raises ChannelClosedError: If channel is closed
        """
        if self._closed:
            raise ChannelClosedError("Subscriber is closed")

        message = await self.queue.get()
        if message is None:
            self._closed = True
            raise ChannelClosedError("Channel was closed")
        return message

    async def __aiter__(self) -> AsyncIterator[Message[T]]:
        """Iterate over messages."""
        try:
            while True:
                yield await self.receive()
        except ChannelClosedError:
            return


class Channel(Generic[T]):
    """
    Asynchronous channel for distributing messages to multiple subscribers.

    Example::

        channel = Channel[str]("notifications")

        # Subscribe to channel
        subscriber = await channel.subscribe()

        # Publish message
        await channel.publish("Hello, subscribers!")

        # Receive message
        message = await subscriber.receive()
    """

    def __init__(
        self, name: str, *, max_subscribers: Optional[int] = None, buffer_size: int = 0
    ):
        """
        Initialize the channel.

        :param name: Channel name
        :type name: str
        :param max_subscribers: Maximum number of subscribers (None for unlimited)
        :type max_subscribers: Optional[int]
        :param buffer_size: Size of subscriber buffers
        :type buffer_size: int
        """
        self.name = name
        self.max_subscribers = max_subscribers
        self.buffer_size = buffer_size
        self._subscribers: weakref.WeakSet[Subscriber[T]] = weakref.WeakSet()
        self._topics: Dict[str, weakref.WeakSet[Subscriber[T]]] = {}
        self._closed = False
        self._lock = asyncio.Lock()

    async def subscribe(self, topics: Optional[List[str]] = None) -> Subscriber[T]:
        """
        Subscribe to the channel.

        :param topics: Optional list of topics to subscribe to
        :type topics: Optional[List[str]]
        :return: New subscriber
        :rtype: Subscriber[T]
        :raises ChannelError: If channel is closed or subscriber limit reached
        """
        if self._closed:
            raise ChannelClosedError("Channel is closed")

        async with self._lock:
            if (
                self.max_subscribers is not None
                and len(self._subscribers) >= self.max_subscribers
            ):
                raise ChannelError("Maximum number of subscribers reached")

            subscriber = Subscriber[T](self.buffer_size)
            self._subscribers.add(subscriber)

            if topics:
                for topic in topics:
                    if topic not in self._topics:
                        self._topics[topic] = weakref.WeakSet()
                    self._topics[topic].add(subscriber)
                    subscriber.topics.add(topic)

            return subscriber

    async def unsubscribe(self, subscriber: Subscriber[T]) -> None:
        """
        Unsubscribe from the channel.

        :param subscriber: Subscriber to remove
        :type subscriber: Subscriber[T]
        """
        async with self._lock:
            self._subscribers.discard(subscriber)
            for topic in subscriber.topics:
                if topic in self._topics:
                    self._topics[topic].discard(subscriber)
            await self._send_to_subscriber(subscriber, None)

    async def publish(
        self,
        data: T,
        topic: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Publish a message to subscribers.

        :param data: Message data to publish
        :type data: T
        :param topic: Optional topic to publish to
        :type topic: Optional[str]
        :param metadata: Optional message metadata
        :type metadata: Optional[Dict[str, Any]]
        :return: Number of subscribers message was sent to
        :rtype: int
        :raises ChannelClosedError: If channel is closed
        """
        if self._closed:
            raise ChannelClosedError("Channel is closed")

        message = Message(data, topic, metadata or {})
        count = 0

        async with self._lock:
            if topic is not None:
                # Send to topic subscribers
                if topic in self._topics:
                    for subscriber in self._topics[topic]:
                        if await self._send_to_subscriber(subscriber, message):
                            count += 1
            else:
                # Send to all subscribers
                for subscriber in self._subscribers:
                    if await self._send_to_subscriber(subscriber, message):
                        count += 1

        return count

    async def broadcast(
        self, data: T, metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Broadcast a message to all subscribers.

        :param data: Message data to broadcast
        :type data: T
        :param metadata: Optional message metadata
        :type metadata: Optional[Dict[str, Any]]
        :return: Number of subscribers message was sent to
        :rtype: int
        """
        return await self.publish(data, None, metadata)

    async def close(self) -> None:
        """Close the channel and notify all subscribers."""
        if self._closed:
            return

        self._closed = True
        async with self._lock:
            for subscriber in self._subscribers:
                await self._send_to_subscriber(subscriber, None)
            self._subscribers.clear()
            self._topics.clear()

    @property
    def subscriber_count(self) -> int:
        """
        Get the current number of subscribers.

        :return: Number of subscribers
        :rtype: int
        """
        return len(self._subscribers)

    @property
    def is_closed(self) -> bool:
        """
        Check if the channel is closed.

        :return: True if channel is closed
        :rtype: bool
        """
        return self._closed

    async def _send_to_subscriber(
        self, subscriber: Subscriber[T], message: Optional[Message[T]]
    ) -> bool:
        """
        Send a message to a subscriber.

        :param subscriber: Subscriber to send to
        :type subscriber: Subscriber[T]
        :param message: Message to send
        :type message: Optional[Message[T]]
        :return: True if message was sent
        :rtype: bool
        """
        try:
            await subscriber.queue.put(message)
            return True
        except Exception as e:
            logger.error(f"Error sending message to subscriber: {str(e)}")
            return False


class TopicChannel(Generic[T]):
    """
    Topic-based channel implementation.

    Example::

        channel = TopicChannel[str]()

        # Subscribe to specific topics
        subscriber = await channel.subscribe(["news", "updates"])

        # Publish to a topic
        await channel.publish("news", "Breaking news!")
    """

    def __init__(self, *, max_subscribers: Optional[int] = None, buffer_size: int = 0):
        """
        Initialize the topic channel.

        :param max_subscribers: Maximum subscribers per topic
        :type max_subscribers: Optional[int]
        :param buffer_size: Size of subscriber buffers
        :type buffer_size: int
        """
        self._channels: Dict[str, Channel[T]] = {}
        self.max_subscribers = max_subscribers
        self.buffer_size = buffer_size
        self._lock = asyncio.Lock()

    async def subscribe(self, topics: List[str]) -> Subscriber[T]:
        """
        Subscribe to multiple topics.

        :param topics: List of topics to subscribe to
        :type topics: List[str]
        :return: New subscriber
        :rtype: Subscriber[T]
        """
        async with self._lock:
            subscriber = Subscriber[T](self.buffer_size)
            for topic in topics:
                if topic not in self._channels:
                    self._channels[topic] = Channel(
                        topic,
                        max_subscribers=self.max_subscribers,
                        buffer_size=self.buffer_size,
                    )
                await self._channels[topic].subscribe([topic])
            return subscriber

    async def publish(
        self, topic: str, data: T, metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Publish a message to a topic.

        :param topic: Topic to publish to
        :type topic: str
        :param data: Message data
        :type data: T
        :param metadata: Optional message metadata
        :type metadata: Optional[Dict[str, Any]]
        :return: Number of subscribers message was sent to
        :rtype: int
        """
        if topic not in self._channels:
            return 0
        return await self._channels[topic].publish(data, topic, metadata)

    async def close(self) -> None:
        """Close all topic channels."""
        async with self._lock:
            for channel in self._channels.values():
                await channel.close()
            self._channels.clear()

    @property
    def topics(self) -> List[str]:
        """
        Get list of active topics.

        :return: List of topic names
        :rtype: List[str]
        """
        return list(self._channels.keys())


class Publisher:
    """
    Message publisher for Channel.

    Example::

        publisher = Publisher(channel)
        await publisher.publish("topic", "Hello, World!")

        async with publisher.batch() as batch:
            await batch.publish("topic1", "Message 1")
            await batch.publish("topic2", "Message 2")
    """

    def __init__(
        self,
        channel: Channel,
        *,
        default_topic: Optional[str] = None,
        batch_size: int = 100,
        flush_interval: float = 1.0,
    ):
        """
        Initialize publisher.

        :param channel: Channel to publish to
        :type channel: Channel
        :param default_topic: Optional default topic
        :type default_topic: Optional[str]
        :param batch_size: Maximum batch size
        :type batch_size: int
        :param flush_interval: Maximum time between flushes
        :type flush_interval: float
        """
        self.channel = channel
        self.default_topic = default_topic
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._batch: List[Message[Any]] = []
        self._batch_task: Optional[asyncio.Task] = None
        self._last_flush = time.monotonic()
        self._lock = asyncio.Lock()
        self._closed = False

    async def publish(
        self,
        data: Any,
        topic: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Publish a message.

        :param data: Message data
        :type data: Any
        :param topic: Optional topic override
        :type topic: Optional[str]
        :param metadata: Optional message metadata
        :type metadata: Optional[Dict[str, Any]]
        :raises ChannelError: If channel is closed
        """
        used_topic = topic or self.default_topic
        if used_topic is None:
            raise ChannelError("No topic specified and no default topic set")

        message = Message(data, topic=used_topic, metadata=metadata or {})
        await self.channel.publish(
            message.topic, message.data, metadata=message.metadata
        )

    async def publish_batch(
        self,
        messages: List[tuple[Any, Optional[str], Optional[Dict[str, Any]]]],
        *,
        ignore_errors: bool = False,
    ) -> List[Optional[Exception]]:
        """
        Publish multiple messages.

        :param messages: List of (data, topic, metadata) tuples
        :type messages: List[tuple[Any, Optional[str], Optional[Dict[str, Any]]]]
        :param ignore_errors: Whether to continue on errors
        :type ignore_errors: bool
        :return: List of exceptions (None for successful messages)
        :rtype: List[Optional[Exception]]
        """
        errors: List[Optional[Exception]] = []

        for data, topic, metadata in messages:
            try:
                await self.publish(data, topic, metadata)
                errors.append(None)
            except Exception as e:
                errors.append(e)
                if not ignore_errors:
                    break

        return errors

    @asynccontextmanager
    async def batch(self) -> AsyncIterator["PublisherBatch"]:
        """
        Create batch context for efficient publishing.

        Example::

            async with publisher.batch() as batch:
                await batch.publish("Hello")
                await batch.publish("World")
        """
        batch = PublisherBatch(self)
        try:
            yield batch
        finally:
            await batch.flush()

    async def start(self) -> None:
        """Start background batch processing."""
        if self._batch_task is None:
            self._batch_task = asyncio.create_task(self._process_batch())

    async def stop(self) -> None:
        """Stop background batch processing."""
        self._closed = True
        if self._batch_task:
            self._batch_task.cancel()
            try:
                await self._batch_task
            except asyncio.CancelledError:
                pass
            self._batch_task = None

    async def _process_batch(self) -> None:
        """Process batched messages."""
        while not self._closed:
            try:
                now = time.monotonic()
                should_flush = (
                    len(self._batch) >= self.batch_size
                    or now - self._last_flush >= self.flush_interval
                )

                if should_flush and self._batch:
                    async with self._lock:
                        batch = self._batch
                        self._batch = []
                        self._last_flush = now

                    try:
                        messages = [
                            (msg.data, msg.topic, msg.metadata) for msg in batch
                        ]
                        await self.publish_batch(messages, ignore_errors=True)
                    except Exception as e:
                        logger.error(f"Error processing batch: {e}")

                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in batch processing: {e}")
                await asyncio.sleep(1.0)

    async def __aenter__(self) -> "Publisher":
        """Start publisher."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop publisher."""
        await self.stop()


class PublisherBatch:
    """
    Batch context for efficient publishing.

    Example::

        async with publisher.batch() as batch:
            await batch.publish("Message 1")
            await batch.publish("Message 2")
    """

    def __init__(self, publisher: Publisher):
        """
        Initialize batch.

        :param publisher: Parent publisher
        :type publisher: Publisher
        """
        self.publisher = publisher
        self._messages: List[Message[Any]] = []

    async def publish(
        self,
        data: Any,
        topic: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add message to batch.

        :param data: Message data
        :type data: Any
        :param topic: Optional topic override
        :type topic: Optional[str]
        :param metadata: Optional message metadata
        :type metadata: Optional[Dict[str, Any]]
        """
        used_topic = topic or self.publisher.default_topic
        if used_topic is None:
            raise ChannelError("No topic specified and no default topic set")

        message = Message(data, topic=used_topic, metadata=metadata or {})
        self._messages.append(message)

        if len(self._messages) >= self.publisher.batch_size:
            await self.flush()

    async def flush(self) -> None:
        """Flush batched messages."""
        if not self._messages:
            return

        messages = [(msg.data, msg.topic, msg.metadata) for msg in self._messages]
        await self.publisher.publish_batch(messages)
        self._messages.clear()

    async def __aenter__(self) -> "PublisherBatch":
        """Enter batch context."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit batch context and flush messages."""
        await self.flush()
