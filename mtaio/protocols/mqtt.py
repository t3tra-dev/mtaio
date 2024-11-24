"""
Asynchronous MQTT client implementation.

This module provides components for MQTT communication:

* MQTTClient: Main MQTT client class
* MQTTMessage: Message container
* MQTTProtocol: Low-level protocol implementation
* QoS: Quality of Service levels
"""

from typing import (
    List,
    Optional,
    Union,
    Callable,
    Awaitable,
    AsyncIterator,
)
from dataclasses import dataclass
import asyncio
import struct
import random
import enum
import logging
from ..exceptions import MQTTError

logger = logging.getLogger(__name__)


class QoS(enum.IntEnum):
    """MQTT Quality of Service levels."""

    AT_MOST_ONCE = 0
    AT_LEAST_ONCE = 1
    EXACTLY_ONCE = 2


class MQTTControlPacketType(enum.IntEnum):
    """MQTT control packet types."""

    CONNECT = 1
    CONNACK = 2
    PUBLISH = 3
    PUBACK = 4
    PUBREC = 5
    PUBREL = 6
    PUBCOMP = 7
    SUBSCRIBE = 8
    SUBACK = 9
    UNSUBSCRIBE = 10
    UNSUBACK = 11
    PINGREQ = 12
    PINGRESP = 13
    DISCONNECT = 14


@dataclass
class MQTTMessage:
    """
    MQTT message container.

    :param topic: Message topic
    :type topic: str
    :param payload: Message payload
    :type payload: Union[str, bytes]
    :param qos: Quality of Service level
    :type qos: QoS
    :param retain: Whether to retain the message
    :type retain: bool
    """

    topic: str
    payload: Union[str, bytes]
    qos: QoS = QoS.AT_MOST_ONCE
    retain: bool = False
    message_id: Optional[int] = None

    def encode(self) -> bytes:
        """Encode message to bytes."""
        if isinstance(self.payload, str):
            payload = self.payload.encode("utf-8")
        else:
            payload = self.payload

        # Variable header
        topic_bytes = self.topic.encode("utf-8")
        variable_header = struct.pack(
            f"!H{len(topic_bytes)}s", len(topic_bytes), topic_bytes
        )

        if self.qos > 0:
            if not self.message_id:
                raise MQTTError("Message ID required for QoS > 0")
            variable_header += struct.pack("!H", self.message_id)

        # Payload
        return variable_header + payload

    @classmethod
    def decode(cls, data: bytes, qos: QoS = QoS.AT_MOST_ONCE) -> "MQTTMessage":
        """Decode message from bytes."""
        # Topic length
        topic_length = struct.unpack("!H", data[:2])[0]
        offset = 2

        # Topic
        topic = data[offset: offset + topic_length].decode("utf-8")
        offset += topic_length

        # Message ID (if QoS > 0)
        message_id = None
        if qos > 0:
            message_id = struct.unpack("!H", data[offset: offset + 2])[0]
            offset += 2

        # Payload
        payload = data[offset:]

        return cls(topic, payload, qos, message_id=message_id)


class MQTTProtocol:
    """Low-level MQTT protocol implementation."""

    @staticmethod
    def encode_length(length: int) -> bytes:
        """Encode remaining length field."""
        result = bytearray()
        while True:
            byte = length % 128
            length = length // 128
            if length > 0:
                byte |= 0x80
            result.append(byte)
            if length == 0:
                break
        return bytes(result)

    @staticmethod
    def decode_length(data: bytes) -> tuple[int, int]:
        """Decode remaining length field."""
        multiplier = 1
        value = 0
        offset = 0

        while True:
            byte = data[offset]
            value += (byte & 127) * multiplier
            if byte & 128 == 0:
                break
            multiplier *= 128
            offset += 1

        return value, offset + 1

    @classmethod
    def encode_connect(
        cls,
        client_id: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        clean_session: bool = True,
        keepalive: int = 60,
    ) -> bytes:
        """Encode CONNECT packet."""
        # Fixed header
        fixed_header = bytes([MQTTControlPacketType.CONNECT << 4])

        # Variable header
        protocol_name = b"\x00\x04MQTT\x04"  # MQTT v3.1.1

        # Connect flags
        flags = 0
        if clean_session:
            flags |= 0x02
        if username:
            flags |= 0x80
        if password:
            flags |= 0x40

        variable_header = protocol_name + bytes([flags]) + struct.pack("!H", keepalive)

        # Payload
        payload = bytearray()

        # Client ID
        client_id_bytes = client_id.encode("utf-8")
        payload.extend(struct.pack("!H", len(client_id_bytes)))
        payload.extend(client_id_bytes)

        # Username
        if username:
            username_bytes = username.encode("utf-8")
            payload.extend(struct.pack("!H", len(username_bytes)))
            payload.extend(username_bytes)

        # Password
        if password:
            password_bytes = password.encode("utf-8")
            payload.extend(struct.pack("!H", len(password_bytes)))
            payload.extend(password_bytes)

        # Remaining length
        remaining_length = cls.encode_length(len(variable_header) + len(payload))

        return fixed_header + remaining_length + variable_header + payload

    @classmethod
    def encode_publish(cls, message: MQTTMessage) -> bytes:
        """Encode PUBLISH packet."""
        # Fixed header
        flags = 0
        if message.retain:
            flags |= 0x01
        flags |= (message.qos & 0x03) << 1
        fixed_header = bytes([(MQTTControlPacketType.PUBLISH << 4) | flags])

        # Payload
        payload = message.encode()

        # Remaining length
        remaining_length = cls.encode_length(len(payload))

        return fixed_header + remaining_length + payload

    @classmethod
    def encode_subscribe(cls, message_id: int, topics: List[tuple[str, QoS]]) -> bytes:
        """Encode SUBSCRIBE packet."""
        # Fixed header
        fixed_header = bytes([(MQTTControlPacketType.SUBSCRIBE << 4) | 0x02])

        # Variable header
        variable_header = struct.pack("!H", message_id)

        # Payload
        payload = bytearray()
        for topic, qos in topics:
            topic_bytes = topic.encode("utf-8")
            payload.extend(
                struct.pack(
                    f"!H{len(topic_bytes)}sB", len(topic_bytes), topic_bytes, qos
                )
            )

        # Remaining length
        remaining_length = cls.encode_length(len(variable_header) + len(payload))

        return fixed_header + remaining_length + variable_header + payload


class MQTTClient:
    """
    Asynchronous MQTT client.

    Example::

        client = MQTTClient()

        @client.on_message
        async def handle_message(message):
            print(f"Received: {message.payload}")

        await client.connect("localhost", 1883)
        await client.subscribe("test/topic")
        await client.publish("test/topic", "Hello, MQTT!")
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        clean_session: bool = True,
        keepalive: int = 60,
    ):
        """
        Initialize MQTT client.

        :param client_id: Client identifier
        :type client_id: Optional[str]
        :param clean_session: Whether to start with a clean session
        :type clean_session: bool
        :param keepalive: Keepalive interval in seconds
        :type keepalive: int
        """
        self.client_id = client_id or f"mqtt-async-{random.randint(0, 1000000)}"
        self.clean_session = clean_session
        self.keepalive = keepalive

        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._message_handlers: List[Callable[[MQTTMessage], Awaitable[None]]] = []
        self._message_id = 0
        self._connected = asyncio.Event()
        self._stopping = False
        self._ping_task: Optional[asyncio.Task] = None

    def on_message(
        self, handler: Callable[[MQTTMessage], Awaitable[None]]
    ) -> Callable[[MQTTMessage], Awaitable[None]]:
        """
        Register message handler.

        :param handler: Message handler function
        :type handler: Callable[[MQTTMessage], Awaitable[None]]
        :return: Handler function
        :rtype: Callable[[MQTTMessage], Awaitable[None]]
        """
        self._message_handlers.append(handler)
        return handler

    async def connect(
        self,
        host: str,
        port: int = 1883,
        username: Optional[str] = None,
        password: Optional[str] = None,
        ssl: bool = False,
    ) -> None:
        """
        Connect to MQTT broker.

        :param host: Broker hostname
        :type host: str
        :param port: Broker port
        :type port: int
        :param username: Optional username
        :type username: Optional[str]
        :param password: Optional password
        :type password: Optional[str]
        :param ssl: Whether to use SSL
        :type ssl: bool
        """
        try:
            self._reader, self._writer = await asyncio.open_connection(
                host, port, ssl=ssl
            )

            # Send CONNECT packet
            connect_packet = MQTTProtocol.encode_connect(
                self.client_id, username, password, self.clean_session, self.keepalive
            )
            self._writer.write(connect_packet)
            await self._writer.drain()

            # Wait for CONNACK
            packet_type, remaining_length = await self._read_fixed_header()
            if packet_type != MQTTControlPacketType.CONNACK:
                raise MQTTError("Expected CONNACK packet")

            data = await self._reader.read(remaining_length)
            if len(data) != 2:
                raise MQTTError("Invalid CONNACK packet")

            session_present, return_code = struct.unpack("!BB", data)
            if return_code != 0:
                raise MQTTError(f"Connection refused: {return_code}")

            self._connected.set()
            self._ping_task = asyncio.create_task(self._ping_loop())
            asyncio.create_task(self._receive_loop())

        except Exception as e:
            if self._writer:
                self._writer.close()
                await self._writer.wait_closed()
            self._reader = self._writer = None
            raise MQTTError(f"Connection failed: {str(e)}") from e

    async def disconnect(self) -> None:
        """Disconnect from broker."""
        if self._writer:
            try:
                # Send DISCONNECT packet
                self._writer.write(bytes([MQTTControlPacketType.DISCONNECT << 4, 0]))
                await self._writer.drain()
            finally:
                self._stopping = True
                if self._ping_task:
                    self._ping_task.cancel()
                self._writer.close()
                await self._writer.wait_closed()
                self._reader = self._writer = None
                self._connected.clear()

    async def publish(
        self,
        topic: str,
        payload: Union[str, bytes],
        qos: QoS = QoS.AT_MOST_ONCE,
        retain: bool = False,
    ) -> None:
        """
        Publish message to topic.

        :param topic: Topic to publish to
        :type topic: str
        :param payload: Message payload
        :type payload: Union[str, bytes]
        :param qos: Quality of Service level
        :type qos: QoS
        :param retain: Whether to retain the message
        :type retain: bool
        """
        if not self._connected.is_set():
            raise MQTTError("Not connected")

        if not isinstance(qos, QoS):
            raise MQTTError("Invalid QoS")

        message = MQTTMessage(
            topic, payload, qos, retain, self._get_message_id() if qos > 0 else None
        )

        packet = MQTTProtocol.encode_publish(message)
        self._writer.write(packet)
        await self._writer.drain()

    async def subscribe(self, topic: str, qos: QoS = QoS.AT_MOST_ONCE) -> None:
        """
        Subscribe to topic.

        :param topic: Topic to subscribe to
        :type topic: str
        :param qos: Quality of Service level
        :type qos: QoS
        """
        if not self._connected.is_set():
            raise MQTTError("Not connected")

        message_id = self._get_message_id()
        packet = MQTTProtocol.encode_subscribe(message_id, [(topic, qos)])
        self._writer.write(packet)
        await self._writer.drain()

    async def _read_fixed_header(self) -> tuple[int, int]:
        """Read fixed header of MQTT packet."""
        first_byte = await self._reader.read(1)
        if not first_byte:
            raise MQTTError("Connection closed by broker")

        packet_type = first_byte[0] >> 4

        remaining_length = 0
        multiplier = 1
        while True:
            byte = await self._reader.read(1)
            if not byte:
                raise MQTTError("Connection closed by broker")

            remaining_length += (byte[0] & 127) * multiplier
            if byte[0] & 128 == 0:
                break
            multiplier *= 128

        return packet_type, remaining_length

    async def _ping_loop(self) -> None:
        """Send periodic PING packets."""
        try:
            while not self._stopping:
                await asyncio.sleep(self.keepalive)
                if self._writer and not self._writer.is_closing():
                    self._writer.write(bytes([MQTTControlPacketType.PINGREQ << 4, 0]))
                    await self._writer.drain()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in ping loop: {str(e)}")
            await self.disconnect()

    async def _receive_loop(self) -> None:
        """Receive and process incoming packets."""
        try:
            while not self._stopping:
                packet_type, remaining_length = await self._read_fixed_header()

                if remaining_length > 0:
                    data = await self._reader.read(remaining_length)
                    if len(data) != remaining_length:
                        raise MQTTError("Incomplete packet received")
                else:
                    data = b""

                await self._handle_packet(packet_type, data)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in receive loop: {str(e)}")
            await self.disconnect()

    async def _handle_packet(self, packet_type: int, data: bytes) -> None:
        """
        Handle received MQTT packet.

        :param packet_type: Type of packet
        :type packet_type: int
        :param data: Packet data
        :type data: bytes
        """
        try:
            if packet_type == MQTTControlPacketType.PUBLISH:
                message = MQTTMessage.decode(data)
                for handler in self._message_handlers:
                    try:
                        await handler(message)
                    except Exception as e:
                        logger.error(f"Error in message handler: {str(e)}")

            elif packet_type == MQTTControlPacketType.PUBACK:
                if len(data) >= 2:
                    message_id = struct.unpack("!H", data[:2])[0]
                    logger.debug(f"Received PUBACK for message {message_id}")

            elif packet_type == MQTTControlPacketType.SUBACK:
                if len(data) >= 2:
                    message_id = struct.unpack("!H", data[:2])[0]
                    logger.debug(f"Received SUBACK for message {message_id}")

            elif packet_type == MQTTControlPacketType.PINGRESP:
                logger.debug("Received PINGRESP")

            else:
                logger.warning(f"Unhandled packet type: {packet_type}")

        except Exception as e:
            logger.error(f"Error handling packet: {str(e)}")

    def _get_message_id(self) -> int:
        """Generate unique message ID."""
        self._message_id = (self._message_id + 1) % 65536
        return self._message_id

    async def __aenter__(self) -> "MQTTClient":
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.disconnect()


class MQTTSubscriber:
    """
    MQTT subscriber helper.

    Example::

        subscriber = MQTTSubscriber()
        async for message in subscriber.subscribe("test/topic"):
            print(f"Received: {message.payload}")
    """

    def __init__(self, client: Optional[MQTTClient] = None, queue_size: int = 0):
        """
        Initialize subscriber.

        :param client: Optional MQTT client
        :type client: Optional[MQTTClient]
        :param queue_size: Size of message queue
        :type queue_size: int
        """
        self.client = client or MQTTClient()
        self.queue: asyncio.Queue[MQTTMessage] = asyncio.Queue(queue_size)

    async def subscribe(
        self, topic: str, qos: QoS = QoS.AT_MOST_ONCE
    ) -> AsyncIterator[MQTTMessage]:
        """
        Subscribe to topic and yield messages.

        :param topic: Topic to subscribe to
        :type topic: str
        :param qos: Quality of Service level
        :type qos: QoS
        :return: AsyncIterator of messages
        :rtype: AsyncIterator[MQTTMessage]
        """

        @self.client.on_message
        async def handler(message: MQTTMessage) -> None:
            if message.topic == topic:
                await self.queue.put(message)

        try:
            await self.client.subscribe(topic, qos)
            while True:
                message = await self.queue.get()
                yield message
        finally:
            self._message_handlers.remove(handler)


class MQTTPublisher:
    """
    MQTT publisher helper.

    Example::

        async with MQTTPublisher() as publisher:
            await publisher.connect("localhost", 1883)
            await publisher.publish_batch([
                ("test/topic1", "message1"),
                ("test/topic2", "message2")
            ])
    """

    def __init__(
        self,
        client: Optional[MQTTClient] = None,
        qos: QoS = QoS.AT_MOST_ONCE,
        retain: bool = False,
    ):
        """
        Initialize publisher.

        :param client: Optional MQTT client
        :type client: Optional[MQTTClient]
        :param qos: Default Quality of Service level
        :type qos: QoS
        :param retain: Default retain flag
        :type retain: bool
        """
        self.client = client or MQTTClient()
        self.qos = qos
        self.retain = retain

    async def publish_batch(
        self, messages: List[tuple[str, Union[str, bytes]]], delay: float = 0.0
    ) -> None:
        """
        Publish multiple messages.

        :param messages: List of (topic, payload) tuples
        :type messages: List[tuple[str, Union[str, bytes]]]
        :param delay: Delay between messages
        :type delay: float
        """
        for topic, payload in messages:
            await self.client.publish(topic, payload, self.qos, self.retain)
            if delay > 0:
                await asyncio.sleep(delay)

    async def __aenter__(self) -> "MQTTPublisher":
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.client.disconnect()
