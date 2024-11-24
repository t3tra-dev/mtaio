"""
Protocol implementation examples for mtaio library.

This example demonstrates:
- ASGI application
- MQTT client usage
- Mail client operations
"""

import asyncio
from mtaio.protocols import (
    ASGIApplication,
    Request,
    Response,
    MQTTClient,
    AsyncSMTPClient,
    MailMessage,
    Attachment,
)


class SimpleApp(ASGIApplication):
    """
    Simple ASGI application example.
    """

    async def handle_request(self, request: Request) -> Response:
        """
        Handle HTTP request.

        :param request: Incoming request
        :return: HTTP response
        """
        if request.path == "/":
            return Response.html("<h1>Welcome to MTAIO</h1>")

        elif request.path == "/api/data":
            return Response.json(
                {
                    "message": "Hello from API",
                    "method": request.method,
                    "query": request.query_params,
                }
            )

        return Response.text("Not Found", status_code=404)


async def asgi_example() -> None:
    """
    Demonstrates ASGI application usage.
    """
    app = SimpleApp()

    # Simulate some requests
    async def simulate_request(
        path: str, method: str = "GET", query_string: bytes = b""
    ) -> Response:
        scope = {
            "type": "http",
            "path": path,
            "method": method,
            "query_string": query_string,
            "headers": [],
        }

        async def receive():
            return {"type": "http.request"}

        response_chunks = []

        async def send(message):
            response_chunks.append(message)

        await app(scope, receive, send)
        print(f"Request to {path}: {response_chunks}")

    # Try different routes
    await simulate_request("/")
    await simulate_request("/api/data")
    await simulate_request("/unknown")


async def mqtt_example() -> None:
    """
    Demonstrates MQTT client usage.
    """
    client = MQTTClient()

    # Set up message handler
    @client.on_message
    async def handle_message(message):
        print(f"Received on {message.topic}: {message.payload}")

    try:
        # Connect to broker
        await client.connect("localhost", 1883, username="user", password="password")

        # Subscribe to topic
        await client.subscribe("test/topic")

        # Publish some messages
        for i in range(3):
            await client.publish("test/topic", f"Message {i}")
            await asyncio.sleep(0.1)

    except Exception as e:
        print(f"MQTT error: {e}")
    finally:
        await client.disconnect()


async def mail_example() -> None:
    """
    Demonstrates mail client usage.
    """
    # Create message
    message = MailMessage(
        subject="Test Message",
        sender="sender@example.com",
        recipients=["recipient@example.com"],
        text_content="Hello from MTAIO!",
        html_content="<h1>Hello from MTAIO!</h1>",
        attachments=[
            Attachment(
                filename="test.txt", content="Test content", content_type="text/plain"
            )
        ],
    )

    # Send message
    client = AsyncSMTPClient()
    try:
        await client.connect("smtp.example.com", 587)
        await client.login("username", "password")
        await client.send_message(message)
    except Exception as e:
        print(f"SMTP error: {e}")
    finally:
        await client.close()


async def main() -> None:
    """
    Run all protocol examples.
    """
    print("=== ASGI Example ===")
    await asgi_example()

    print("\n=== MQTT Example ===")
    await mqtt_example()

    print("\n=== Mail Example ===")
    await mail_example()


if __name__ == "__main__":
    asyncio.run(main())
