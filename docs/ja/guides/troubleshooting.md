# トラブルシューティングガイド

このガイドでは、mtaioアプリケーションで発生する一般的な問題の診断と解決方法について説明します。

## 一般的な問題

### リソース管理

#### 高メモリ使用量

**問題**: アプリケーションのメモリ使用量が継続的に増加する。

**考えられる原因**:

- リソースが適切に閉じられていない
- キャッシュサイズが適切に設定されていない
- イベントハンドラでのメモリリーク

**解決策**:

```python
from mtaio.resources import ResourceManager
from mtaio.cache import TTLCache

# 適切なリソースのクリーンアップ
async with ResourceManager() as manager:
    # リソースは自動的にクリーンアップされる
    pass

# 適切なサイズでキャッシュを設定
cache = TTLCache[str](
    max_size=1000,  # キャッシュサイズを制限
    default_ttl=300.0  # 5分後にアイテムをクリア
)

# イベントハンドラのクリーンアップ
emitter = EventEmitter()
@emitter.on("event")
async def handler(event):
    # イベントの処理
    pass

# 不要になったハンドラを削除
emitter.remove_listener("event", handler)
```

#### タスク実行のタイムアウト

**問題**: タスクが頻繁にタイムアウトするか、実行に時間がかかりすぎる。

**解決策**:

```python
from mtaio.core import TaskExecutor
from mtaio.resources import TimeoutManager

# 適切なタイムアウトを設定
async with TimeoutManager(default_timeout=30.0) as tm:
    async with TaskExecutor() as executor:
        # 同時実行数の制限を設定
        result = await executor.gather(
            *tasks,
            limit=5  # 同時実行タスクを制限
        )
```

### イベント処理

#### イベントハンドラのメモリリーク

**問題**: イベントハンドラの登録によりメモリ使用量が増加する。

**解決策**:

```python
from mtaio.events import EventEmitter
import weakref

class EventHandlers:
    def __init__(self):
        self._handlers = weakref.WeakSet()
        self.emitter = EventEmitter()
    
    def register(self, handler):
        self._handlers.add(handler)
        self.emitter.on("event")(handler)
    
    def cleanup(self):
        self._handlers.clear()
```

#### イベントハンドラの未登録

**問題**: イベントが処理されない。

**解決策**:

```python
from mtaio.events import EventEmitter

async def setup_handlers():
    emitter = EventEmitter()
    
    # エラー処理を追加
    @emitter.on("error")
    async def handle_error(event):
        print(f"エラーが発生しました: {event.data}")
    
    # ハンドラ登録を確認
    if emitter.listener_count("error") == 0:
        raise RuntimeError("エラーハンドラが登録されていません")
```

### キャッシュの問題

#### キャッシュの不整合

**問題**: アプリケーションの異なる部分でキャッシュデータが不整合になる。

**解決策**:

```python
from mtaio.cache import DistributedCache
from mtaio.events import EventEmitter

async def setup_cache():
    cache = DistributedCache[str]([
        ("localhost", 5000),
        ("localhost", 5001)
    ])
    emitter = EventEmitter()
    
    @emitter.on("data_changed")
    async def invalidate_cache(event):
        affected_keys = event.data.get("keys", [])
        for key in affected_keys:
            await cache.delete(key)
```

#### キャッシュのパフォーマンス問題

**問題**: キャッシュ操作が遅いまたは非効率。

**解決策**:

```python
from mtaio.cache import TTLCache
from mtaio.monitoring import ResourceMonitor

async def optimize_cache():
    # キャッシュパフォーマンスのモニタリング
    monitor = ResourceMonitor()
    cache = TTLCache[str](
        default_ttl=60.0,  # 頻繁に変更されるデータには短いTTL
        max_size=1000
    )
    
    # キャッシュメトリクスの追加
    @monitor.on_metric("cache_hits")
    async def track_cache_hits(value):
        if value < 0.5:  # ヒット率が50%未満
            print("キャッシュヒット率が低いため、TTLの調整を検討してください")
```

## デバッグツール

### ロギングの設定

デバッグ用の詳細なロギングを設定:

```python
import logging
from mtaio.logging import AsyncFileHandler

async def setup_debug_logging():
    logger = logging.getLogger("mtaio")
    logger.setLevel(logging.DEBUG)
    
    handler = AsyncFileHandler("debug.log")
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
```

### パフォーマンスプロファイリング

ボトルネックを特定するためのアプリケーションプロファイリング:

```python
from mtaio.monitoring import Profiler

async def profile_application():
    profiler = Profiler()
    
    @profiler.trace
    async def monitored_function():
        # モニタリング対象の関数
        pass
    
    # パフォーマンスメトリクスの取得
    profile = await profiler.get_profile()
    print(f"実行時間: {profile.total_time:.2f}秒")
    print(f"メモリ使用量: {profile.memory_usage} MB")
```

## エラーメッセージ

### 一般的なエラーメッセージと解決策

1. **`MTAIOError: Resource limit exceeded`**
    - 原因: 同時実行操作が多すぎる
    - 解決策: リソース制限の調整またはレート制限の追加

2. **`TimeoutError: Operation timed out`**
    - 原因: 操作の完了に時間がかかりすぎた
    - 解決策: タイムアウトの増加または操作の最適化

3. **`CacheError: Cache connection failed`**
    - 原因: キャッシュサーバーに接続できない
    - 解決策: キャッシュサーバーの状態と設定を確認

4. **`EventError: Event handler failed`**
    - 原因: イベントハンドラでの例外発生
    - 解決策: イベントハンドラにエラー処理を追加

## ベストプラクティス

### エラー処理

包括的なエラー処理の実装:

```python
from mtaio.exceptions import MTAIOError

async def handle_errors():
    try:
        # コードをここに記述
        pass
    except MTAIOError as e:
        # mtaio固有のエラーを処理
        logger.error(f"mtaioエラー: {e}")
    except Exception as e:
        # 予期しないエラーを処理
        logger.exception("予期しないエラーが発生しました")
```

### リソースのクリーンアップ

適切なリソースのクリーンアップを確保:

```python
from contextlib import AsyncExitStack

async def cleanup_resources():
    async with AsyncExitStack() as stack:
        # スタックにリソースを追加
        executor = await stack.enter_async_context(TaskExecutor())
        cache = await stack.enter_async_context(TTLCache[str]())
        
        # リソースは自動的にクリーンアップされる
```

## サポートの取得

問題が解決しない場合は:

1. 正しい使用方法について[APIリファレンス](../api/index.md)を確認する
2. 既存の[GitHubのIssue](https://github.com/t3tra-dev/mtaio/issues)を検索する
3. [コミュニティディスカッション](https://github.com/t3tra-dev/mtaio/discussions)で質問する

問題を報告する際は、以下の情報を含めてください:

- Pythonのバージョン
- mtaioのバージョン
- 最小限の再現可能な例
- エラーメッセージとスタックトレース
- 関連する設定情報
