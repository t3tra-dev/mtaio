# イベントAPIリファレンス

`mtaio.events`モジュールは、イベント駆動型アプリケーションを構築するための堅牢なイベント処理システムを提供します。

## EventEmitter

### 基本的な使い方

```python
from mtaio.events import EventEmitter

# エミッターの作成
emitter = EventEmitter()

# ハンドラの定義
@emitter.on("user_login")
async def handle_login(event):
    user = event.data
    print(f"ユーザー {user['name']} がログインしました")

# イベントの発行
await emitter.emit("user_login", {
    "name": "田中",
    "id": "123"
})
```

### クラスリファレンス

```python
class EventEmitter:
    def __init__(self):
        """イベントエミッターを初期化します。"""
    
    def on(
        self,
        event_name: str,
        priority: EventPriority = EventPriority.NORMAL
    ) -> Callable:
        """
        イベントハンドラを登録するデコレータ。

        Args:
            event_name: 処理するイベントの名前
            priority: ハンドラの優先度レベル

        Returns:
            デコレートされたイベントハンドラ
        """
    
    def once(
        self,
        event_name: str,
        priority: EventPriority = EventPriority.NORMAL
    ) -> Callable:
        """1回限りのイベントハンドラを登録します。"""
    
    async def emit(
        self,
        event_name: str,
        data: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        イベントを発行します。

        Args:
            event_name: イベントの名前
            data: イベントデータ
            metadata: オプションのイベントメタデータ
        """
```

## イベントの種類

### Event

基本イベントコンテナクラス。

```python
from mtaio.events import Event, ChangeType

@dataclass
class Event[T]:
    name: str              # イベント名
    data: T               # イベントデータ
    propagate: bool = True # 伝播を継続するかどうか
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### EventPriority

イベントハンドラの優先度レベル。

```python
class EventPriority(Enum):
    LOWEST = auto()   # 最低優先度
    LOW = auto()      # 低優先度
    NORMAL = auto()   # 通常優先度
    HIGH = auto()     # 高優先度
    HIGHEST = auto()  # 最高優先度
    MONITOR = auto()  # モニタリングのみ
```

## 高度な機能

### イベントのフィルタリング

条件に基づいてイベントをフィルタリング:

```python
from mtaio.events import EventEmitter

emitter = EventEmitter()

# フィルタリングされたエミッターの作成
filtered = emitter.filter(
    lambda event: event.data.get("priority") == "high"
)

@filtered.on("alert")
async def handle_high_priority_alert(event):
    alert = event.data
    print(f"高優先度アラート: {alert['message']}")
```

### イベントの変換

処理前にイベントを変換:

```python
from mtaio.events import EventEmitter, Event

# 変換されたエミッターの作成
transformed = emitter.map(
    lambda event: Event(
        name=event.name,
        data={**event.data, "processed": True}
    )
)

@transformed.on("data_event")
async def handle_processed_data(event):
    # 変換されたイベントを処理
    pass
```

### バッチ操作

複数のイベントをグループ化:

```python
from mtaio.events import EventEmitter

emitter = EventEmitter()

async def batch_operations():
    async with emitter.batch_operations():
        # イベントがバッチ処理される
        await emitter.emit("event1", data1)
        await emitter.emit("event2", data2)
        # ハンドラは全てのイベントについて一度に呼び出される
```

### イベントチャネル

特定の目的のためのイベントチャネルを作成:

```python
from mtaio.events import Channel, Subscriber

async def channel_example():
    channel = Channel[str]("notifications")
    
    # チャネルの購読
    subscriber = await channel.subscribe()
    
    # メッセージの配信
    await channel.publish("購読者の皆様へ")
    
    # メッセージの受信
    message = await subscriber.receive()
```

### トピックベースのイベント

トピックでイベントを処理:

```python
from mtaio.events import Channel

async def topic_example():
    channel = Channel[str]("events")
    
    # 特定のトピックを購読
    subscriber = await channel.subscribe(["user.*", "system.*"])
    
    # トピックへの配信
    await channel.publish(
        "ユーザーがログインしました",
        topic="user.login"
    )
```

## エラー処理

### イベントエラー

イベント関連のエラーを処理:

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
        # 発行エラーの処理
        pass
    except EventHandlerError:
        # ハンドラエラーの処理
        pass
```

### エラーイベント

エラーイベントの発行:

```python
@emitter.on("error")
async def handle_error(event):
    error = event.data
    print(f"エラーが発生しました: {error}")

# エラーイベントの発行
try:
    await process_data()
except Exception as e:
    await emitter.emit("error", e)
```

## ベストプラクティス

### イベントハンドラの構成

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

# 使用例
handlers = UserEventHandlers(emitter)
```

### リソース管理

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

### パフォーマンス最適化

1. **イベントのバッチ処理**
   ```python
   async with emitter.batch_operations():
       for item in items:
           await emitter.emit("item.processed", item)
   ```

2. **優先度処理**
   ```python
   @emitter.on("critical", priority=EventPriority.HIGHEST)
   async def handle_critical(event):
       # 重要なイベントを最初に処理
       pass
   ```

3. **イベントのフィルタリング**
   ```python
   # 早期にイベントをフィルタリング
   filtered = emitter.filter(lambda e: e.data.get("important"))
   
   @filtered.on("event")
   async def handle_important_events(event):
       pass
   ```

## 使用例

### イベント駆動データ処理

```python
from mtaio.events import EventEmitter

class DataProcessor:
    def __init__(self):
        self.emitter = EventEmitter()
    
    async def process(self, data: dict):
        # 前処理イベントの発行
        await self.emitter.emit("process.start", data)
        
        try:
            result = await self.process_data(data)
            await self.emitter.emit("process.complete", result)
        except Exception as e:
            await self.emitter.emit("process.error", e)
```

### イベントモニタリング

```python
class EventMonitor:
    def __init__(self, emitter: EventEmitter):
        @emitter.on("*", priority=EventPriority.MONITOR)
        async def monitor_all(event):
            await self.log_event(event)
    
    async def log_event(self, event: Event):
        print(f"イベント: {event.name}, データ: {event.data}")
```

## 関連項目

- 基本機能については[コアAPIリファレンス](core.md)を参照
- デコレータについては[デコレータAPIリファレンス](decorators.md)を参照
- サンプルコードは[サンプルリポジトリ](https://github.com/t3tra-dev/mtaio/tree/main/examples/events.py)を参照
