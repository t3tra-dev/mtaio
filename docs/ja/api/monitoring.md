# モニタリングAPIリファレンス

`mtaio.monitoring`モジュールは、システムリソース、アプリケーションメトリクス、パフォーマンスプロファイリングのためのツールを提供します。

## ResourceMonitor

### 基本的な使い方

```python
from mtaio.monitoring import ResourceMonitor

# モニターの作成
monitor = ResourceMonitor(interval=1.0)  # 1秒間隔

# アラートハンドラーの設定
@monitor.on_threshold_exceeded
async def handle_alert(metric: str, value: float, threshold: float):
    print(f"警告: {metric}がしきい値を超過 ({value} > {threshold})")

# しきい値の設定
monitor.set_threshold("cpu_usage", 80.0)  # CPU使用率80%
monitor.set_threshold("memory_usage", 90.0)  # メモリ使用率90%

# モニタリングの開始
await monitor.start()
```

### クラスリファレンス

```python
class ResourceMonitor:
    def __init__(
        self,
        interval: float = 1.0,
        history_size: int = 3600
    ):
        """
        リソースモニターを初期化します。

        Args:
            interval: モニタリング間隔（秒）
            history_size: 保持する履歴統計の数
        """

    async def start(self) -> None:
        """モニタリングを開始します。"""

    async def stop(self) -> None:
        """モニタリングを停止します。"""

    def set_threshold(
        self,
        metric: str,
        value: float
    ) -> None:
        """メトリクスのしきい値を設定します。"""

    async def get_current_stats(self) -> SystemStats:
        """現在のシステム統計を取得します。"""
```

## システム統計

### SystemStats

システム統計データのコンテナ。

```python
@dataclass
class SystemStats:
    timestamp: float
    cpu: CPUStats
    memory: MemoryStats
    io: IOStats

@dataclass
class CPUStats:
    usage_percent: float
    load_average: List[float]
    thread_count: int

@dataclass
class MemoryStats:
    total: int
    available: int
    used: int
    percent: float

@dataclass
class IOStats:
    read_bytes: int
    write_bytes: int
    read_count: int
    write_count: int
```

## Profiler

### 基本的な使い方

```python
from mtaio.monitoring import Profiler

# プロファイラーの作成
profiler = Profiler()

# 関数実行のプロファイリング
@profiler.trace
async def monitored_function():
    await perform_operation()

# コードブロックのプロファイリング
async with profiler.trace_context("操作"):
    await perform_operation()

# プロファイルデータの取得
profile = await profiler.get_profile()
print(f"合計実行時間: {profile.total_time:.2f}秒")
```

### クラスリファレンス

```python
class Profiler:
    def __init__(
        self,
        enabled: bool = True,
        trace_async_tasks: bool = True,
        collect_stack_trace: bool = False
    ):
        """
        プロファイラーを初期化します。

        Args:
            enabled: プロファイリングを有効にするかどうか
            trace_async_tasks: 非同期タスクをトレースするかどうか
            collect_stack_trace: スタックトレースを収集するかどうか
        """

    def trace(
        self,
        func: Optional[Callable[..., Awaitable[T]]] = None,
        *,
        name: Optional[str] = None
    ) -> Callable:
        """非同期関数をトレースするデコレータ。"""
```

## パフォーマンスメトリクス

### プロファイルデータ

```python
@dataclass
class ProfileTrace:
    name: str
    start_time: float
    end_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    memory_start: int = 0
    memory_end: int = 0

    @property
    def duration(self) -> float:
        """操作の所要時間を取得します。"""
        return self.end_time - self.start_time

    @property
    def memory_delta(self) -> int:
        """メモリ使用量の変化を取得します。"""
        return self.memory_end - self.memory_start
```

## 高度な機能

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
            # メトリクスの更新
            stats = await self.get_current_stats()
            
            # メトリクスの処理
            if self.metrics.error_count > 100:
                await self.alert("エラー率が高くなっています")
            
            await asyncio.sleep(60)
```

### パフォーマンスプロファイリング

```python
from mtaio.monitoring import Profiler

class PerformanceProfiler:
    def __init__(self):
        self.profiler = Profiler(
            trace_async_tasks=True,
            collect_stack_trace=True
        )
    
    async def profile_operation(self):
        async with self.profiler.trace_context("操作"):
            # メモリ使用量のモニタリング
            await self.profiler.start_trace(
                "memory_usage",
                metadata={"type": "memory"}
            )
            
            # 操作の実行
            await perform_operation()
            
            # 結果の取得
            profile = await self.profiler.get_profile()
            return self.analyze_profile(profile)
```

## 統合例

### Webアプリケーションのモニタリング

```python
class WebAppMonitor:
    def __init__(self):
        self.monitor = ResourceMonitor()
        self.profiler = Profiler()
        
    async def monitor_request(self, request):
        async with self.profiler.trace_context("http_request"):
            start_time = time.time()
            
            try:
                response = await process_request(request)
                duration = time.time() - start_time
                
                await self.monitor.record_metric(
                    "request_duration",
                    duration
                )
                
                return response
                
            except Exception as e:
                await self.monitor.record_metric(
                    "request_error",
                    1.0
                )
                raise
```

### バックグラウンドタスクのモニタリング

```python
class TaskMonitor:
    def __init__(self):
        self.monitor = ResourceMonitor()
        
    async def monitor_task(self, task_id: str):
        @self.monitor.on_threshold_exceeded
        async def handle_task_alert(metric, value, threshold):
            await self.notify_admin(
                f"タスク {task_id} の {metric} がしきい値を超過しました"
            )
        
        while True:
            stats = await self.get_task_stats(task_id)
            await self.monitor.record_metrics({
                "task_memory": stats.memory_usage,
                "task_cpu": stats.cpu_usage
            })
            await asyncio.sleep(1)
```

## ベストプラクティス

### リソース管理

```python
# 適切なクリーンアップ
async def cleanup_monitoring():
    monitor = ResourceMonitor()
    try:
        await monitor.start()
        yield monitor
    finally:
        await monitor.stop()
```

### しきい値の設定

```python
# 適切なしきい値の設定
def configure_thresholds(monitor: ResourceMonitor):
    # システムリソース
    monitor.set_threshold("cpu_usage", 80.0)
    monitor.set_threshold("memory_usage", 90.0)
    
    # アプリケーションメトリクス
    monitor.set_threshold("error_rate", 5.0)
    monitor.set_threshold("response_time", 1.0)
```

### パフォーマンス最適化

```python
# 効率的なメトリクス収集
class OptimizedMonitor(ResourceMonitor):
    def __init__(self):
        super().__init__(interval=5.0)  # 収集頻度を減らす
        self._metrics_cache = {}
    
    async def get_metric(self, name: str) -> float:
        if name in self._metrics_cache:
            if time.time() - self._metrics_cache[name]["timestamp"] < 1.0:
                return self._metrics_cache[name]["value"]
        
        value = await self._collect_metric(name)
        self._metrics_cache[name] = {
            "value": value,
            "timestamp": time.time()
        }
        return value
```

## 関連項目

- 基本機能については[コアAPIリファレンス](core.md)を参照
- イベント処理については[イベントAPIリファレンス](events.md)を参照
- ロギング統合については[ロギングAPIリファレンス](logging.md)を参照
- サンプルコードは[サンプルリポジトリ](https://github.com/t3tra-dev/mtaio/tree/main/examples/monitoring.py)を参照
