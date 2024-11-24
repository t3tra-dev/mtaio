"""
Test MQTT protocol implementation.
"""

import pytest
import asyncio
from unittest import mock
from mtaio.protocols import MQTTClient
from mtaio.exceptions import MQTTError


@pytest.mark.asyncio
async def test_mqtt_client_publish():
    """Test MQTT message publishing."""
    client = MQTTClient()
    try:
        await asyncio.wait_for(client.connect("localhost", 1883), timeout=1.0)
    except (MQTTError, OSError, asyncio.TimeoutError):
        pytest.skip("MQTT broker not available")
        return


@pytest.mark.asyncio
async def test_mqtt_client_qos():
    """Test MQTT QoS levels."""
    client = MQTTClient()

    mock_transport = mock.Mock()
    mock_protocol = mock.Mock()

    client._writer = asyncio.StreamWriter(
        transport=mock_transport,
        protocol=mock_protocol,
        reader=None,
        loop=asyncio.get_event_loop()
    )
    client._connected.set()

    with pytest.raises(MQTTError, match="Invalid QoS"):
        await client.publish(
            "test/topic",
            "message",
            qos=999
        )
