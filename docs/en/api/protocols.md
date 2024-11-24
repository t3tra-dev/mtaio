# Protocols API Reference

The `mtaio.protocols` module provides implementations for various network protocols, including ASGI, MQTT, and mail protocols.

## ASGI Protocol

### ASGIApplication

Basic ASGI application implementation.

```python
from mtaio.protocols import ASGIApplication, Request, Response

class App(ASGIApplication):
    async def handle_request(self, request: Request) -> Response:
        if request.path == "/":
            return Response.json({
                "message": "Welcome to mtaio"
            })
        return Response.text("Not Found", status_code=404)

app = App()
```

### Request

ASGI request wrapper.

```python
class Request:
    @property
    def method(self) -> str:
        """Get HTTP method."""
    
    @property
    def path(self) -> str:
        """Get request path."""
    
    @property
    def query_string(self) -> bytes:
        """Get raw query string."""
    
    @property
    def headers(self) -> Dict[str, str]:
        """Get request headers."""
    
    async def body(self) -> bytes:
        """Get request body."""
    
    async def json(self) -> Any:
        """Get JSON-decoded body."""
    
    async def form(self) -> Dict[str, str]:
        """Get parsed form data."""
```

### Response

ASGI response wrapper.

```python
class Response:
    @classmethod
    def text(
        cls,
        content: str,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None
    ) -> "Response":
        """Create text response."""
    
    @classmethod
    def json(
        cls,
        content: Any,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None
    ) -> "Response":
        """Create JSON response."""
    
    @classmethod
    def html(
        cls,
        content: str,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None
    ) -> "Response":
        """Create HTML response."""
```

### Router

URL routing implementation.

```python
from mtaio.protocols import Router

router = Router()

@router.route("/users/{user_id}")
async def get_user(request, user_id: str):
    return Response.json({
        "user_id": user_id
    })

@router.route("/users", methods=["POST"])
async def create_user(request):
    data = await request.json()
    return Response.json(data, status_code=201)
```

## MQTT Protocol

### MQTTClient

MQTT client implementation.

```python
from mtaio.protocols import MQTTClient, QoS

# Create client
client = MQTTClient()

# Set up message handler
@client.on_message
async def handle_message(message):
    print(f"Received: {message.payload}")

# Connect and subscribe
async with client:
    await client.connect("localhost", 1883)
    await client.subscribe("test/topic", qos=QoS.AT_LEAST_ONCE)
    
    # Publish message
    await client.publish(
        "test/topic",
        "Hello MQTT",
        qos=QoS.AT_LEAST_ONCE
    )
```

### MQTTMessage

MQTT message container.

```python
@dataclass
class MQTTMessage:
    topic: str
    payload: Union[str, bytes]
    qos: QoS = QoS.AT_MOST_ONCE
    retain: bool = False
    message_id: Optional[int] = None
```

### QoS

MQTT Quality of Service levels.

```python
class QoS(enum.IntEnum):
    AT_MOST_ONCE = 0
    AT_LEAST_ONCE = 1
    EXACTLY_ONCE = 2
```

## Mail Protocol

### AsyncIMAPClient

Asynchronous IMAP client implementation.

```python
from mtaio.protocols import AsyncIMAPClient

async with AsyncIMAPClient() as client:
    # Connect and login
    await client.connect("imap.example.com", 993)
    await client.login("user@example.com", "password")
    
    # Select mailbox
    await client.select_mailbox("INBOX")
    
    # Fetch messages
    messages = await client.fetch_messages(
        criteria="UNSEEN",
        limit=10
    )
```

### AsyncSMTPClient

Asynchronous SMTP client implementation.

```python
from mtaio.protocols import AsyncSMTPClient, MailMessage, Attachment

async with AsyncSMTPClient() as client:
    # Connect and login
    await client.connect("smtp.example.com", 587)
    await client.login("user@example.com", "password")
    
    # Create message
    message = MailMessage(
        subject="Test Message",
        sender="sender@example.com",
        recipients=["recipient@example.com"],
        text_content="Hello from mtaio",
        html_content="<h1>Hello from mtaio</h1>"
    )
    
    # Add attachment
    attachment = Attachment(
        filename="document.pdf",
        content=pdf_content,
        content_type="application/pdf"
    )
    message.attachments.append(attachment)
    
    # Send message
    await client.send_message(message)
```

## Best Practices

### ASGI Applications

```python
# Use middleware for common functionality
class LoggingMiddleware(ASGIMiddleware):
    async def __call__(self, scope, receive, send):
        start_time = time.time()
        await self.app(scope, receive, send)
        duration = time.time() - start_time
        logger.info(f"Request processed in {duration:.2f}s")

# Handle errors properly
class App(ASGIApplication):
    async def handle_error(self, error: Exception, send):
        if isinstance(error, ValidationError):
            response = Response.json(
                {"error": str(error)},
                status_code=400
            )
        else:
            response = Response.json(
                {"error": "Internal Server Error"},
                status_code=500
            )
        await response(send)
```

### MQTT Applications

```python
# Implement reliable messaging
class ReliableMQTTClient(MQTTClient):
    async def reliable_publish(
        self,
        topic: str,
        payload: str,
        retries: int = 3
    ):
        for attempt in range(retries):
            try:
                await self.publish(
                    topic,
                    payload,
                    qos=QoS.EXACTLY_ONCE
                )
                return
            except MQTTError:
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(1)
```

### Mail Applications

```python
# Handle attachments efficiently
class MailHandler:
    def __init__(self):
        self.imap = AsyncIMAPClient()
        self.smtp = AsyncSMTPClient()
    
    async def forward_with_attachments(
        self,
        message: MailMessage,
        forward_to: str
    ):
        # Download attachments in parallel
        tasks = [
            self.download_attachment(att)
            for att in message.attachments
        ]
        attachments = await asyncio.gather(*tasks)
        
        # Create new message
        forward = MailMessage(
            subject=f"Fwd: {message.subject}",
            sender=self.smtp.username,
            recipients=[forward_to],
            text_content=message.text_content,
            attachments=attachments
        )
        
        await self.smtp.send_message(forward)
```

## Error Handling

```python
from mtaio.exceptions import (
    ProtocolError,
    ASGIError,
    MQTTError,
    MailError
)

# ASGI error handling
try:
    await app(scope, receive, send)
except ASGIError as e:
    logger.error(f"ASGI error: {e}")
    # Handle error response

# MQTT error handling
try:
    await client.publish(topic, message)
except MQTTError as e:
    logger.error(f"MQTT error: {e}")
    # Implement retry logic

# Mail error handling
try:
    await smtp.send_message(message)
except MailError as e:
    logger.error(f"Mail error: {e}")
    # Queue for retry
```

## See Also

- [Core API Reference](core.md) for base functionality
- [Events API Reference](events.md) for event handling
- [Examples Repository](https://github.com/t3tra-dev/mtaio/tree/main/examples/protocols.py)
