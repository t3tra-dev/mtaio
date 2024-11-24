# プロトコルAPIリファレンス

`mtaio.protocols`モジュールは、ASGI、MQTT、メールプロトコルなど、様々なネットワークプロトコルの実装を提供します。

## ASGIプロトコル

### ASGIApplication

基本的なASGIアプリケーションの実装です。

```python
from mtaio.protocols import ASGIApplication, Request, Response

class App(ASGIApplication):
    async def handle_request(self, request: Request) -> Response:
        if request.path == "/":
            return Response.json({
                "message": "mtaioへようこそ"
            })
        return Response.text("Not Found", status_code=404)

app = App()
```

### Request

ASGIリクエストのラッパー。

```python
class Request:
    @property
    def method(self) -> str:
        """HTTPメソッドを取得します。"""
    
    @property
    def path(self) -> str:
        """リクエストパスを取得します。"""
    
    @property
    def query_string(self) -> bytes:
        """生のクエリ文字列を取得します。"""
    
    @property
    def headers(self) -> Dict[str, str]:
        """リクエストヘッダーを取得します。"""
    
    async def body(self) -> bytes:
        """リクエストボディを取得します。"""
    
    async def json(self) -> Any:
        """JSONデコードされたボディを取得します。"""
    
    async def form(self) -> Dict[str, str]:
        """解析されたフォームデータを取得します。"""
```

### Response

ASGIレスポンスのラッパー。

```python
class Response:
    @classmethod
    def text(
        cls,
        content: str,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None
    ) -> "Response":
        """テキストレスポンスを作成します。"""
    
    @classmethod
    def json(
        cls,
        content: Any,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None
    ) -> "Response":
        """JSONレスポンスを作成します。"""
    
    @classmethod
    def html(
        cls,
        content: str,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None
    ) -> "Response":
        """HTMLレスポンスを作成します。"""
```

### Router

URLルーティングの実装です。

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

## MQTTプロトコル

### MQTTClient

MQTTクライアントの実装です。

```python
from mtaio.protocols import MQTTClient, QoS

# クライアントの作成
client = MQTTClient()

# メッセージハンドラーの設定
@client.on_message
async def handle_message(message):
    print(f"受信: {message.payload}")

# 接続とサブスクライブ
async with client:
    await client.connect("localhost", 1883)
    await client.subscribe("test/topic", qos=QoS.AT_LEAST_ONCE)
    
    # メッセージの配信
    await client.publish(
        "test/topic",
        "MQTTからこんにちは",
        qos=QoS.AT_LEAST_ONCE
    )
```

### MQTTMessage

MQTTメッセージのコンテナです。

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

MQTTのサービス品質（QoS）レベルです。

```python
class QoS(enum.IntEnum):
    AT_MOST_ONCE = 0  # 最大1回
    AT_LEAST_ONCE = 1 # 最低1回
    EXACTLY_ONCE = 2  # 正確に1回
```

## メールプロトコル

### AsyncIMAPClient

非同期IMAPクライアントの実装です。

```python
from mtaio.protocols import AsyncIMAPClient

async with AsyncIMAPClient() as client:
    # 接続とログイン
    await client.connect("imap.example.com", 993)
    await client.login("user@example.com", "password")
    
    # メールボックスの選択
    await client.select_mailbox("INBOX")
    
    # メッセージの取得
    messages = await client.fetch_messages(
        criteria="UNSEEN",
        limit=10
    )
```

### AsyncSMTPClient

非同期SMTPクライアントの実装です。

```python
from mtaio.protocols import AsyncSMTPClient, MailMessage, Attachment

async with AsyncSMTPClient() as client:
    # 接続とログイン
    await client.connect("smtp.example.com", 587)
    await client.login("user@example.com", "password")
    
    # メッセージの作成
    message = MailMessage(
        subject="テストメッセージ",
        sender="sender@example.com",
        recipients=["recipient@example.com"],
        text_content="mtaioからこんにちは",
        html_content="<h1>mtaioからこんにちは</h1>"
    )
    
    # 添付ファイルの追加
    attachment = Attachment(
        filename="document.pdf",
        content=pdf_content,
        content_type="application/pdf"
    )
    message.attachments.append(attachment)
    
    # メッセージの送信
    await client.send_message(message)
```

## ベストプラクティス

### ASGIアプリケーション

```python
# 共通機能にミドルウェアを使用
class LoggingMiddleware(ASGIMiddleware):
    async def __call__(self, scope, receive, send):
        start_time = time.time()
        await self.app(scope, receive, send)
        duration = time.time() - start_time
        logger.info(f"リクエスト処理時間: {duration:.2f}秒")

# エラーを適切に処理
class App(ASGIApplication):
    async def handle_error(self, error: Exception, send):
        if isinstance(error, ValidationError):
            response = Response.json(
                {"error": str(error)},
                status_code=400
            )
        else:
            response = Response.json(
                {"error": "内部サーバーエラー"},
                status_code=500
            )
        await response(send)
```

### MQTTアプリケーション

```python
# 信頼性のあるメッセージング実装
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

### メールアプリケーション

```python
# 添付ファイルの効率的な処理
class MailHandler:
    def __init__(self):
        self.imap = AsyncIMAPClient()
        self.smtp = AsyncSMTPClient()
    
    async def forward_with_attachments(
        self,
        message: MailMessage,
        forward_to: str
    ):
        # 添付ファイルの並列ダウンロード
        tasks = [
            self.download_attachment(att)
            for att in message.attachments
        ]
        attachments = await asyncio.gather(*tasks)
        
        # 新しいメッセージの作成
        forward = MailMessage(
            subject=f"転送: {message.subject}",
            sender=self.smtp.username,
            recipients=[forward_to],
            text_content=message.text_content,
            attachments=attachments
        )
        
        await self.smtp.send_message(forward)
```

## エラー処理

```python
from mtaio.exceptions import (
    ProtocolError,
    ASGIError,
    MQTTError,
    MailError
)

# ASGIエラー処理
try:
    await app(scope, receive, send)
except ASGIError as e:
    logger.error(f"ASGIエラー: {e}")
    # エラーレスポンスの処理

# MQTTエラー処理
try:
    await client.publish(topic, message)
except MQTTError as e:
    logger.error(f"MQTTエラー: {e}")
    # リトライロジックの実装

# メールエラー処理
try:
    await smtp.send_message(message)
except MailError as e:
    logger.error(f"メール送信エラー: {e}")
    # 再試行のためのキュー登録
```

## 関連項目

- 基本機能については[コアAPIリファレンス](core.md)を参照
- イベント処理については[イベントAPIリファレンス](events.md)を参照
- サンプルコードは[サンプルリポジトリ](https://github.com/t3tra-dev/mtaio/tree/main/examples/protocols.py)を参照
