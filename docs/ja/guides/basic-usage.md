# 基本的な使い方

このガイドでは、実践的な例を通してmtaioの基本的な機能を説明します。

## 基本機能

### タスク実行

`TaskExecutor`は非同期タスクの制御された実行を提供します:

```python
from mtaio.core import TaskExecutor

async def process_item(item: str) -> str:
    return f"処理済み: {item}"

async def main():
    # 基本的な使用方法
    async with TaskExecutor() as executor:
        # 単一タスクの処理
        result = await executor.run(process_item("データ"))
        
        # 並行性制限付きで複数のタスクを処理
        items = ["項目1", "項目2", "項目3", "項目4"]
        results = await executor.gather(
            *(process_item(item) for item in items),
            limit=2  # 最大2つの同時実行タスク
        )

    # 項目に対するマップ操作
    async with TaskExecutor() as executor:
        results = await executor.map(process_item, items, limit=2)
```

### 非同期キュー

非同期データフローの管理:

```python
from mtaio.core import AsyncQueue

async def producer_consumer():
    queue = AsyncQueue[str](maxsize=10)
    
    # プロデューサー
    await queue.put("項目")
    
    # コンシューマー
    item = await queue.get()
    queue.task_done()
    
    # すべてのタスクの完了を待機
    await queue.join()
```

## イベント処理

イベントシステムはコンポーネント間の疎結合な通信を可能にします:

```python
from mtaio.events import EventEmitter

# エミッターの作成
emitter = EventEmitter()

# ハンドラーの定義
@emitter.on("user_action")
async def handle_user_action(event):
    user = event.data
    print(f"ユーザー {user['name']} がアクションを実行しました")

@emitter.once("startup")  # 1回限りのハンドラー
async def handle_startup(event):
    print("アプリケーションが起動しました")

# イベントの発行
await emitter.emit("startup", {"time": "2024-01-01"})
await emitter.emit("user_action", {"name": "田中"})
```

## キャッシュ

mtaioは様々なキャッシュ機能を提供します:

### TTLキャッシュ

```python
from mtaio.cache import TTLCache

# 5分間のTTLでキャッシュを作成
cache = TTLCache[str](
    default_ttl=300.0,
    max_size=1000
)

# 基本的な操作
await cache.set("キー", "値")
value = await cache.get("キー")

# カスタムTTLの使用
await cache.set("キー2", "値2", ttl=60.0)  # 60秒

# バッチ操作
await cache.set_many({
    "キー1": "値1",
    "キー2": "値2"
})
```

### 分散キャッシュ

```python
from mtaio.cache import DistributedCache

# 複数ノードの分散キャッシュを作成
cache = DistributedCache[str](
    nodes=[
        ("localhost", 5000),
        ("localhost", 5001)
    ],
    replication_factor=2
)

async with cache:
    await cache.set("キー", "値")
    value = await cache.get("キー")
```

## リソース管理

### レート制限

```python
from mtaio.resources import RateLimiter

# レート制限の作成
limiter = RateLimiter(10.0)  # 1秒あたり10回の操作

@limiter.limit
async def rate_limited_operation():
    # この関数は1秒あたり10回に制限されます
    pass

# 手動でのレート制限
async def manual_rate_limit():
    async with limiter:
        # レート制限されたコードブロック
        pass
```

### タイムアウト管理

```python
from mtaio.resources import TimeoutManager

async def operation_with_timeout():
    async with TimeoutManager(5.0) as tm:  # 5秒のタイムアウト
        result = await tm.run(long_running_operation())
        
        # 特定の操作に異なるタイムアウトを設定
        result2 = await tm.run(
            another_operation(),
            timeout=2.0  # 2秒のタイムアウト
        )
```

## エラー処理

mtaioは包括的な例外階層を提供します:

```python
from mtaio.exceptions import (
    MTAIOError,
    TimeoutError,
    CacheError,
    RateLimitError
)

async def safe_operation():
    try:
        await rate_limited_operation()
    except RateLimitError:
        # レート制限超過の処理
        pass
    except TimeoutError:
        # タイムアウトの処理
        pass
    except MTAIOError as e:
        # mtaio固有のエラーの処理
        print(f"操作が失敗しました: {e}")
```

## 型安全性

mtaioは完全な型付けとタイプチェックをサポートしています:

```python
from mtaio.typing import AsyncFunc, CacheKey, CacheValue

class CustomCache(CacheValue):
    def __init__(self, data: str):
        self.data = data
    
    async def serialize(self) -> bytes:
        return self.data.encode()
    
    @classmethod
    async def deserialize(cls, data: bytes) -> 'CustomCache':
        return cls(data.decode())

# 型安全な関数定義
async def process_data(func: AsyncFunc[str]) -> str:
    return await func()
```

## 一般的なパターン

### 処理の連鎖

```python
from mtaio.data import Pipeline
from mtaio.events import EventEmitter

# 処理パイプラインの作成
pipeline = Pipeline()
emitter = EventEmitter()

# 処理ステージの追加
pipeline.add_stage(DataValidationStage())
pipeline.add_stage(DataTransformStage())
pipeline.add_stage(DataStorageStage())

# イベント付きのデータ処理
async def process():
    async with pipeline:
        for item in items:
            result = await pipeline.process(item)
            await emitter.emit("item_processed", result)
```

### モニタリング

```python
from mtaio.monitoring import ResourceMonitor

# モニターの作成
monitor = ResourceMonitor(interval=1.0)

@monitor.on_threshold_exceeded
async def handle_threshold(metric: str, value: float, threshold: float):
    print(f"警告: {metric}がしきい値を超えました: {value} > {threshold}")

# モニタリングの開始
await monitor.start()
monitor.set_threshold("cpu_usage", 80.0)  # CPU使用率80%のしきい値
```

## 次のステップ

これらの基本を理解したら、以下に進むことができます:

1. より複雑なパターンについては[高度な使い方](advanced-usage.md)を参照
2. 詳細なドキュメントについては[APIリファレンス](../api/index.md)を確認
3. より多くの例については[サンプルリポジトリ](https://github.com/t3tra-dev/mtaio/tree/main/examples)を参照
