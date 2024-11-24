# 高度な使い方

このガイドでは、高度な非同期アプリケーションを構築するためのmtaioの高度な機能とパターンについて説明します。

## 高度なイベントパターン

### イベントパイプライン

イベントとデータパイプラインを組み合わせて複雑なワークフローを作成:

```python
from mtaio.events import EventEmitter
from mtaio.data import Pipeline, Stage

class ValidationStage(Stage[dict, dict]):
    async def process(self, data: dict) -> dict:
        if "user_id" not in data:
            raise ValueError("user_idが見つかりません")
        return data

class EnrichmentStage(Stage[dict, dict]):
    async def process(self, data: dict) -> dict:
        data["timestamp"] = time.time()
        return data

async def setup_event_pipeline():
    pipeline = Pipeline()
    emitter = EventEmitter()
    
    # パイプラインの設定
    pipeline.add_stage(ValidationStage())
    pipeline.add_stage(EnrichmentStage())
    
    @emitter.on("user_action")
    async def handle_user_action(event):
        async with pipeline:
            processed_data = await pipeline.process(event.data)
            await emitter.emit("processed_action", processed_data)

    return emitter
```

### イベントのフィルタリングと変換

```python
from mtaio.events import EventEmitter, Event

async def setup_event_processing():
    emitter = EventEmitter()
    
    # イベントのフィルタリング
    filtered = emitter.filter(
        lambda event: event.data.get("priority") == "high"
    )
    
    # イベントの変換
    transformed = emitter.map(
        lambda event: Event(
            event.name,
            {**event.data, "processed": True}
        )
    )
    
    # 複数のエミッターを連鎖
    emitter.pipe(filtered)
    filtered.pipe(transformed)
```

## 高度なキャッシュ戦略

### キャッシュの階層化

最適なパフォーマンスのためのマルチレベルキャッシュの実装:

```python
from mtaio.cache import TTLCache, DistributedCache
from typing import Optional, TypeVar, Generic

T = TypeVar("T")

class LayeredCache(Generic[T]):
    def __init__(self):
        self.local = TTLCache[T](default_ttl=60.0)  # 1分のローカルキャッシュ
        self.distributed = DistributedCache[T]([
            ("localhost", 5000),
            ("localhost", 5001)
        ])
    
    async def get(self, key: str) -> Optional[T]:
        # まずローカルキャッシュを試行
        value = await self.local.get(key)
        if value is not None:
            return value
        
        # 分散キャッシュを試行
        value = await self.distributed.get(key)
        if value is not None:
            # ローカルキャッシュを更新
            await self.local.set(key, value)
            return value
        
        return None
    
    async def set(self, key: str, value: T) -> None:
        # 両方のキャッシュを更新
        await self.local.set(key, value)
        await self.distributed.set(key, value)
```

### キャッシュ無効化パターン

```python
from mtaio.cache import TTLCache
from mtaio.events import EventEmitter

class CacheInvalidator:
    def __init__(self):
        self.cache = TTLCache[str]()
        self.emitter = EventEmitter()
        
        @self.emitter.on("data_updated")
        async def invalidate_cache(event):
            keys = event.data.get("affected_keys", [])
            for key in keys:
                await self.cache.delete(key)
            
            if event.data.get("clear_all", False):
                await self.cache.clear()
    
    async def update_data(self, key: str, value: str) -> None:
        await self.cache.set(key, value)
        await self.emitter.emit("data_updated", {
            "affected_keys": [key]
        })
```

## 高度なリソース管理

### カスタムリソースリミッター

特定のニーズに合わせたリソースリミッターの作成:

```python
from mtaio.resources import ResourceLimiter
from mtaio.typing import AsyncFunc
from typing import Dict

class AdaptiveRateLimiter(ResourceLimiter):
    def __init__(self):
        self.rates: Dict[str, float] = {}
        self._current_load = 0.0
    
    async def acquire(self, resource_id: str) -> None:
        rate = self.rates.get(resource_id, 1.0)
        if self._current_load > 0.8:  # 80%の負荷
            rate *= 0.5  # レートを削減
        await super().acquire(tokens=1/rate)
    
    def adjust_rate(self, resource_id: str, load: float) -> None:
        self._current_load = load
        if load > 0.9:  # 高負荷
            self.rates[resource_id] *= 0.8
        elif load < 0.5:  # 低負荷
            self.rates[resource_id] *= 1.2
```

### 複雑なタイムアウトパターン

```python
from mtaio.resources import TimeoutManager
from contextlib import asynccontextmanager

class TimeoutController:
    def __init__(self):
        self.timeouts = TimeoutManager()
    
    @asynccontextmanager
    async def cascading_timeout(self, timeouts: list[float]):
        """段階的なタイムアウトとフォールバック動作を実装"""
        for timeout in timeouts:
            try:
                async with self.timeouts.timeout(timeout):
                    yield
                break
            except TimeoutError:
                if timeout == timeouts[-1]:
                    raise
                continue
```

## 高度なデータ処理

### カスタムパイプラインステージ

複雑なデータ変換のための特殊なパイプラインステージの作成:

```python
from mtaio.data import Pipeline, Stage
from typing import Any, AsyncIterator

class BatchProcessingStage(Stage[Any, Any]):
    def __init__(self, batch_size: int):
        self.batch_size = batch_size
        self.batch = []
    
    async def process(self, item: Any) -> AsyncIterator[Any]:
        self.batch.append(item)
        
        if len(self.batch) >= self.batch_size:
            result = await self._process_batch(self.batch)
            self.batch = []
            return result
    
    async def _process_batch(self, batch: list[Any]) -> Any:
        # バッチ処理ロジックの実装
        return batch
```

### ストリーム処理

複雑なストリーム処理パターンの実装:

```python
from mtaio.data import Stream
from typing import TypeVar, AsyncIterator

T = TypeVar("T")

class StreamProcessor(Stream[T]):
    async def window(
        self,
        size: int,
        slide: int = 1
    ) -> AsyncIterator[list[T]]:
        """スライディングウィンドウの実装"""
        buffer: list[T] = []
        
        async for item in self:
            buffer.append(item)
            if len(buffer) >= size:
                yield buffer[-size:]
                buffer = buffer[slide:]
    
    async def batch_by_time(
        self,
        seconds: float
    ) -> AsyncIterator[list[T]]:
        """時間ベースのバッチ処理"""
        batch: list[T] = []
        start_time = time.monotonic()
        
        async for item in self:
            batch.append(item)
            if time.monotonic() - start_time >= seconds:
                yield batch
                batch = []
                start_time = time.monotonic()
```

## 高度なモニタリング

### カスタムメトリクス収集

```python
from mtaio.monitoring import ResourceMonitor
from dataclasses import dataclass

@dataclass
class CustomMetrics:
    request_count: int = 0
    error_count: int = 0
    average_response_time: float = 0.0

class ApplicationMonitor(ResourceMonitor):
    def __init__(self):
        super().__init__()
        self.metrics = CustomMetrics()
    
    async def collect_metrics(self) -> None:
        while True:
            stats = await self.get_current_stats()
            
            # カスタムメトリクスの更新
            self.metrics.average_response_time = (
                stats.latency_sum / stats.request_count
                if stats.request_count > 0 else 0.0
            )
            
            # 必要に応じてアラートを発行
            if self.metrics.error_count > 100:
                await self.alert("高いエラー率が検出されました")
            
            await asyncio.sleep(60)  # 1分ごとに収集
```

## 本番環境のベストプラクティス

### エラーリカバリー

```python
from mtaio.core import TaskExecutor
from mtaio.exceptions import MTAIOError

class ResilientExecutor:
    def __init__(self):
        self.executor = TaskExecutor()
        self.retry_count = 3
    
    async def execute_with_recovery(
        self,
        func: AsyncFunc[T],
        *args: Any,
        **kwargs: Any
    ) -> T:
        for attempt in range(self.retry_count):
            try:
                return await self.executor.run(
                    func(*args, **kwargs)
                )
            except MTAIOError as e:
                if attempt == self.retry_count - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # 指数バックオフ
```

### リソースのクリーンアップ

```python
from mtaio.resources import ResourceManager
from typing import AsyncIterator

class ManagedResources:
    def __init__(self):
        self.resources: list[AsyncCloseable] = []
    
    async def acquire(self, resource: AsyncCloseable) -> None:
        self.resources.append(resource)
    
    async def cleanup(self) -> None:
        while self.resources:
            resource = self.resources.pop()
            await resource.close()
    
    @asynccontextmanager
    async def resource_scope(self) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await self.cleanup()
```

## 次のステップ

- [サンプルアプリケーション](https://github.com/t3tra-dev/mtaio/tree/main/examples.py)をチェック
- [APIリファレンス](../api/index.md)を確認
- [コミュニティディスカッション](https://github.com/t3tra-dev/mtaio/discussions)に参加
