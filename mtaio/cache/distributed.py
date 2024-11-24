"""
Distributed cache implementation.

This module provides components for distributed caching:

* DistributedCache: Main distributed cache class
* CacheNode: Cache node implementation
* CacheProtocol: Cache communication protocol
* CacheClient: Cache client implementation
"""

from typing import (
    Dict,
    List,
    Optional,
    Any,
    TypeVar,
    Generic,
    Tuple,
)
from dataclasses import dataclass
import asyncio
import json
import time
import pickle
import hashlib
import logging
from enum import Enum, auto
from ..exceptions import CacheError

T = TypeVar("T")
logger = logging.getLogger(__name__)


class CacheCommand(Enum):
    """Cache command types."""

    GET = auto()
    SET = auto()
    DELETE = auto()
    CLEAR = auto()
    PING = auto()
    SYNC = auto()


@dataclass
class CacheMessage:
    """
    Cache message container.

    :param command: Command type
    :type command: CacheCommand
    :param key: Cache key
    :type key: str
    :param value: Optional value
    :type value: Optional[bytes]
    :param ttl: Optional TTL in seconds
    :type ttl: Optional[float]
    """

    command: CacheCommand
    key: str
    value: Optional[bytes] = None
    ttl: Optional[float] = None
    node_id: Optional[str] = None

    def serialize(self) -> bytes:
        """Serialize message to bytes."""
        data = {
            "command": self.command.name,
            "key": self.key,
            "value": self.value.hex() if self.value else None,
            "ttl": self.ttl,
            "node_id": self.node_id,
        }
        return json.dumps(data).encode("utf-8")

    @classmethod
    def deserialize(cls, data: bytes) -> "CacheMessage":
        """Deserialize message from bytes."""
        try:
            msg = json.loads(data.decode("utf-8"))
            value = bytes.fromhex(msg["value"]) if msg["value"] else None
            return cls(
                command=CacheCommand[msg["command"]],
                key=msg["key"],
                value=value,
                ttl=msg["ttl"],
                node_id=msg["node_id"],
            )
        except Exception as e:
            raise CacheError(f"Failed to deserialize message: {e}") from e


class CacheEntry:
    """
    Cache entry container.

    :param value: Cached value
    :type value: bytes
    :param ttl: Time-to-live in seconds
    :type ttl: Optional[float]
    """

    def __init__(self, value: bytes, ttl: Optional[float] = None):
        self.value = value
        self.timestamp = time.monotonic()
        self.ttl = ttl

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.ttl is None:
            return False
        return time.monotonic() - self.timestamp > self.ttl


class CacheNode:
    """
    Cache node implementation.

    Example::

        node = CacheNode('node1', ('localhost', 5000))
        await node.start()

        # Other nodes can connect to this one
        client = CacheClient()
        await client.connect(('localhost', 5000))
    """

    def __init__(
        self,
        node_id: str,
        address: Tuple[str, int],
        peers: Optional[List[Tuple[str, int]]] = None,
    ):
        """
        Initialize cache node.

        :param node_id: Unique node identifier
        :type node_id: str
        :param address: Node address (host, port)
        :type address: Tuple[str, int]
        :param peers: Optional list of peer addresses
        :type peers: Optional[List[Tuple[str, int]]]
        """
        self.node_id = node_id
        self.address = address
        self.peers = set(peers or [])
        self._cache: Dict[str, CacheEntry] = {}
        self._server: Optional[asyncio.Server] = None
        self._peer_connections: Dict[str, asyncio.Transport] = {}
        self._clean_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the cache node."""
        self._server = await asyncio.start_server(
            self._handle_connection, self.address[0], self.address[1]
        )
        self._clean_task = asyncio.create_task(self._clean_expired())

        # Connect to peers
        for peer in self.peers:
            await self._connect_to_peer(peer)

    async def stop(self) -> None:
        """Stop the cache node."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()

        if self._clean_task:
            self._clean_task.cancel()
            try:
                await self._clean_task
            except asyncio.CancelledError:
                pass

        for transport in self._peer_connections.values():
            transport.close()

    async def set(
        self, key: str, value: Any, ttl: Optional[float] = None, propagate: bool = True
    ) -> None:
        """
        Set cache value.

        :param key: Cache key
        :type key: str
        :param value: Value to cache
        :type value: Any
        :param ttl: Optional time-to-live in seconds
        :type ttl: Optional[float]
        :param propagate: Whether to propagate to peers
        :type propagate: bool
        """
        try:
            value_bytes = pickle.dumps(value)
            self._cache[key] = CacheEntry(value_bytes, ttl)

            if propagate:
                message = CacheMessage(
                    command=CacheCommand.SET,
                    key=key,
                    value=value_bytes,
                    ttl=ttl,
                    node_id=self.node_id,
                )
                await self._broadcast(message)
        except Exception as e:
            raise CacheError(f"Failed to set cache value: {e}") from e

    async def get(self, key: str) -> Optional[Any]:
        """
        Get cache value.

        :param key: Cache key
        :type key: str
        :return: Cached value or None
        :rtype: Optional[Any]
        """
        entry = self._cache.get(key)
        if entry:
            if entry.is_expired():
                del self._cache[key]
                return None
            try:
                return pickle.loads(entry.value)
            except Exception as e:
                raise CacheError(f"Failed to deserialize cache value: {e}") from e
        return None

    async def delete(self, key: str, propagate: bool = True) -> None:
        """
        Delete cache value.

        :param key: Cache key
        :type key: str
        :param propagate: Whether to propagate to peers
        :type propagate: bool
        """
        self._cache.pop(key, None)

        if propagate:
            message = CacheMessage(
                command=CacheCommand.DELETE, key=key, node_id=self.node_id
            )
            await self._broadcast(message)

    async def clear(self, propagate: bool = True) -> None:
        """
        Clear all cache entries.

        :param propagate: Whether to propagate to peers
        :type propagate: bool
        """
        self._cache.clear()

        if propagate:
            message = CacheMessage(
                command=CacheCommand.CLEAR, key="", node_id=self.node_id
            )
            await self._broadcast(message)

    async def _handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle incoming connection."""
        try:
            while True:
                length_bytes = await reader.read(4)
                if not length_bytes:
                    break

                length = int.from_bytes(length_bytes, "big")
                data = await reader.read(length)
                if not data:
                    break

                message = CacheMessage.deserialize(data)
                await self._handle_message(message, writer)
        except Exception as e:
            logger.error(f"Error handling connection: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def _handle_message(
        self, message: CacheMessage, writer: asyncio.StreamWriter
    ) -> None:
        """Handle received message."""
        try:
            if message.command == CacheCommand.GET:
                entry = self._cache.get(message.key)
                response = CacheMessage(
                    command=CacheCommand.GET,
                    key=message.key,
                    value=entry.value if entry else None,
                    ttl=entry.ttl if entry else None,
                    node_id=self.node_id,
                )
                await self._send_message(response, writer)

            elif message.command == CacheCommand.SET:
                if message.value is not None:
                    self._cache[message.key] = CacheEntry(message.value, message.ttl)

            elif message.command == CacheCommand.DELETE:
                self._cache.pop(message.key, None)

            elif message.command == CacheCommand.CLEAR:
                self._cache.clear()

            elif message.command == CacheCommand.SYNC:
                # Send all cache entries to the requesting node
                for key, entry in self._cache.items():
                    if not entry.is_expired():
                        sync_message = CacheMessage(
                            command=CacheCommand.SET,
                            key=key,
                            value=entry.value,
                            ttl=entry.ttl,
                            node_id=self.node_id,
                        )
                        await self._send_message(sync_message, writer)

        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def _connect_to_peer(self, address: Tuple[str, int]) -> None:
        """Connect to peer node."""
        retry_count = 0
        max_retries = 3
        while retry_count < max_retries:
            try:
                reader, writer = await asyncio.open_connection(*address)
                # 接続成功
                return
            except Exception:
                retry_count += 1
                await asyncio.sleep(1 * retry_count)
        raise ConnectionError(f"Failed to connect to peer after {max_retries} attempts")

    async def _broadcast(self, message: CacheMessage) -> None:
        """Broadcast message to all peers."""
        for transport in self._peer_connections.values():
            try:
                data = message.serialize()
                length = len(data).to_bytes(4, "big")
                transport.write(length + data)
                await transport.drain()
            except Exception as e:
                logger.error(f"Failed to broadcast message: {e}")

    async def _send_message(
        self, message: CacheMessage, writer: asyncio.StreamWriter
    ) -> None:
        """Send message to specific peer."""
        try:
            data = message.serialize()
            length = len(data).to_bytes(4, "big")
            writer.write(length + data)
            await writer.drain()
        except Exception as e:
            logger.error(f"Failed to send message: {e}")

    async def _clean_expired(self) -> None:
        """Clean expired cache entries."""
        while True:
            try:
                for key, entry in list(self._cache.items()):
                    if entry.is_expired():
                        del self._cache[key]
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error cleaning expired entries: {e}")
                await asyncio.sleep(1)


class CacheClient:
    """
    Cache client implementation.

    Example::

        client = CacheClient()
        await client.connect(('localhost', 5000))

        await client.set('key', 'value', ttl=60)
        value = await client.get('key')
    """

    def __init__(self):
        """Initialize cache client."""
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None

    async def connect(self, address: Tuple[str, int]) -> None:
        """
        Connect to cache node.

        :param address: Node address (host, port)
        :type address: Tuple[str, int]
        """
        self._reader, self._writer = await asyncio.open_connection(*address)

    async def disconnect(self) -> None:
        """Disconnect from cache node."""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
            self._reader = self._writer = None

    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """
        Set cache value.

        :param key: Cache key
        :type key: str
        :param value: Value to cache
        :type value: Any
        :param ttl: Optional time-to-live in seconds
        :type ttl: Optional[float]
        """
        try:
            value_bytes = pickle.dumps(value)
            message = CacheMessage(
                command=CacheCommand.SET, key=key, value=value_bytes, ttl=ttl
            )
            await self._send_message(message)
        except Exception as e:
            raise CacheError(f"Failed to set cache value: {e}") from e

    async def get(self, key: str) -> Optional[Any]:
        """
        Get cache value.

        :param key: Cache key
        :type key: str
        :return: Cached value or None
        :rtype: Optional[Any]
        """
        try:
            message = CacheMessage(command=CacheCommand.GET, key=key)
            response = await self._send_message(message)

            if response and response.value:
                return pickle.loads(response.value)
            return None
        except Exception as e:
            raise CacheError(f"Failed to get cache value: {e}") from e

    async def delete(self, key: str) -> None:
        """
        Delete cache value.

        :param key: Cache key
        :type key: str
        """
        message = CacheMessage(command=CacheCommand.DELETE, key=key)
        await self._send_message(message)

    async def clear(self) -> None:
        """Clear all cache entries."""
        message = CacheMessage(command=CacheCommand.CLEAR, key="")
        await self._send_message(message)

    async def _send_message(self, message: CacheMessage) -> Optional[CacheMessage]:
        """
        Send message and wait for response if needed.

        :param message: Message to send
        :type message: CacheMessage
        :return: Optional response message
        :rtype: Optional[CacheMessage]
        :raises CacheError: If communication fails
        """
        if not self._writer or not self._reader:
            raise CacheError("Not connected")

        try:
            # Serialize and send message
            data = message.serialize()
            length = len(data).to_bytes(4, "big")
            self._writer.write(length + data)
            await self._writer.drain()

            # Wait for response if it's a GET command
            if message.command == CacheCommand.GET:
                length_bytes = await self._reader.read(4)
                if not length_bytes:
                    raise CacheError("Connection closed")

                length = int.from_bytes(length_bytes, "big")
                data = await self._reader.read(length)
                if not data:
                    raise CacheError("Connection closed")

                return CacheMessage.deserialize(data)

            return None

        except asyncio.CancelledError:
            raise
        except Exception as e:
            raise CacheError(f"Failed to send message: {e}") from e

    async def __aenter__(self) -> "CacheClient":
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.disconnect()


class DistributedCache(Generic[T]):
    """
    High-level distributed cache interface.

    Example::

        cache = DistributedCache[str](nodes=[
            ('localhost', 5000),
            ('localhost', 5001)
        ])

        await cache.set("key", "value", ttl=60)
        value = await cache.get("key")
    """

    def __init__(
        self,
        nodes: List[Tuple[str, int]],
        replication_factor: int = 2,
        read_quorum: int = 1,
    ):
        """
        Initialize distributed cache.

        :param nodes: List of cache node addresses
        :type nodes: List[Tuple[str, int]]
        :param replication_factor: Number of replicas
        :type replication_factor: int
        :param read_quorum: Number of nodes for read consensus
        :type read_quorum: int
        """
        self.nodes = nodes
        self.replication_factor = min(replication_factor, len(nodes))
        self.read_quorum = min(read_quorum, len(nodes))
        self._clients: Dict[Tuple[str, int], CacheClient] = {}

    def _get_nodes_for_key(self, key: str) -> List[Tuple[str, int]]:
        """Get nodes responsible for a key."""
        # Simple consistent hashing
        key_hash = int(hashlib.md5(key.encode()).hexdigest(), 16)
        sorted_nodes = sorted(self.nodes)
        start_idx = key_hash % len(sorted_nodes)

        selected_nodes = []
        for i in range(self.replication_factor):
            idx = (start_idx + i) % len(sorted_nodes)
            selected_nodes.append(sorted_nodes[idx])

        return selected_nodes

    async def _get_client(self, node: Tuple[str, int]) -> CacheClient:
        """Get or create client for node."""
        if node not in self._clients:
            client = CacheClient()
            await client.connect(node)
            self._clients[node] = client
        return self._clients[node]

    async def set(self, key: str, value: T, ttl: Optional[float] = None) -> None:
        """
        Set cache value.

        :param key: Cache key
        :type key: str
        :param value: Value to cache
        :type value: T
        :param ttl: Optional time-to-live in seconds
        :type ttl: Optional[float]
        """
        nodes = self._get_nodes_for_key(key)
        tasks = []

        for node in nodes:
            try:
                client = await self._get_client(node)
                tasks.append(client.set(key, value, ttl))
            except Exception as e:
                logger.error(f"Failed to set value on node {node}: {e}")

        if tasks:
            await asyncio.gather(*tasks)
        else:
            raise CacheError("No available nodes")

    async def get(self, key: str) -> Optional[T]:
        """
        Get cache value.

        :param key: Cache key
        :type key: str
        :return: Cached value or None
        :rtype: Optional[T]
        """
        nodes = self._get_nodes_for_key(key)
        tasks = []
        results = []

        for node in nodes:
            try:
                client = await self._get_client(node)
                tasks.append(client.get(key))
            except Exception as e:
                logger.error(f"Failed to get value from node {node}: {e}")

        if not tasks:
            raise CacheError("No available nodes")

        # Wait for quorum
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        for task in done:
            try:
                result = await task
                if result is not None:
                    results.append(result)
                if len(results) >= self.read_quorum:
                    break
            except Exception as e:
                logger.error(f"Error getting value: {e}")

        # Return most common value
        if results:
            return max(set(results), key=results.count)
        return None

    async def delete(self, key: str) -> None:
        """
        Delete cache value.

        :param key: Cache key
        :type key: str
        """
        nodes = self._get_nodes_for_key(key)
        tasks = []

        for node in nodes:
            try:
                client = await self._get_client(node)
                tasks.append(client.delete(key))
            except Exception as e:
                logger.error(f"Failed to delete value on node {node}: {e}")

        if tasks:
            await asyncio.gather(*tasks)
        else:
            raise CacheError("No available nodes")

    async def close(self) -> None:
        """Close all connections."""
        for client in self._clients.values():
            await client.disconnect()
        self._clients.clear()

    async def __aenter__(self) -> "DistributedCache[T]":
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.close()
