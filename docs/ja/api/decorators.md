# デコレータAPIリファレンス

`mtaio.decorators`モジュールは、キャッシュ、リトライ、レート制限などの追加機能で非同期関数を拡張するためのユーティリティデコレータを提供します。

## アダプター

異なる非同期パターン間の変換を行うデコレータです。

### async_adapter

同期関数を非同期関数に変換します。

```python
from mtaio.decorators import async_adapter

# 基本的な使用法
@async_adapter
def cpu_intensive(data: str) -> str:
    # CPU負荷の高い処理
    return processed_data

# カスタムエグゼキューターを使用
@async_adapter(executor=ThreadPoolExecutor(max_workers=4))
def parallel_operation(data: str) -> str:
    return processed_data

# デコレートされた関数の使用
async def main():
    result = await cpu_intensive("データ")
```

### async_iterator

同期的な反復可能オブジェクトを非同期イテレータに変換します。

```python
from mtaio.decorators import async_iterator

@async_iterator(chunk_size=10)
def generate_data() -> Iterable[int]:
    return range(1000)

async def process_data():
    async for items in generate_data():
        # アイテムのチャンクを処理
        pass
```

### async_context_adapter

同期コンテキストマネージャを非同期コンテキストマネージャに変換します。

```python
from mtaio.decorators import async_context_adapter
from contextlib import contextmanager

@async_context_adapter
@contextmanager
def resource_manager():
    resource = acquire_resource()
    try:
        yield resource
    finally:
        release_resource(resource)

async def use_resource():
    async with resource_manager() as resource:
        await process(resource)
```

## 制御フロー

関数実行を制御するデコレータです。

### with_timeout

非同期関数にタイムアウト制御を追加します。

```python
from mtaio.decorators import with_timeout

@with_timeout(5.0)  # 5秒のタイムアウト
async def api_call() -> dict:
    return await make_request()

# カスタムエラーメッセージ付き
@with_timeout(10.0, error_message="APIコールがタイムアウトしました")
async def long_operation() -> None:
    await process_data()
```

### with_retry

失敗した操作のリトライロジックを追加します。

```python
from mtaio.decorators import with_retry

# 基本的なリトライ
@with_retry(max_attempts=3)
async def unstable_operation() -> str:
    return await flaky_service_call()

# 高度なリトライ設定
@with_retry(
    max_attempts=5,
    delay=1.0,
    backoff_factor=2.0,
    exceptions=(ConnectionError, TimeoutError)
)
async def network_operation() -> bytes:
    return await fetch_data()
```

### with_rate_limit

関数呼び出しにレート制限を追加します。

```python
from mtaio.decorators import with_rate_limit

@with_rate_limit(10.0)  # 1秒あたり10回の呼び出し
async def rate_limited_api() -> dict:
    return await api_call()

# バースト許容付き
@with_rate_limit(rate=5.0, burst=10)
async def burst_allowed_operation() -> None:
    await process()
```

### with_circuit_breaker

サーキットブレーカーパターンを実装します。

```python
from mtaio.decorators import with_circuit_breaker

@with_circuit_breaker(
    failure_threshold=5,    # 5回の失敗後にオープン
    reset_timeout=60.0,     # 60秒後にリセットを試行
    half_open_timeout=5.0   # タイムアウト後に1回のテスト呼び出しを許可
)
async def protected_operation() -> str:
    return await external_service_call()
```

### with_fallback

失敗した操作のフォールバック動作を提供します。

```python
from mtaio.decorators import with_fallback

# 静的フォールバック付き
@with_fallback("デフォルト値")
async def get_data() -> str:
    return await fetch_data()

# フォールバック関数付き
@with_fallback(lambda: get_cached_data())
async def fetch_user(user_id: str) -> dict:
    return await db_query(user_id)
```

### with_cache

関数の結果にキャッシュを追加します。

```python
from mtaio.decorators import with_cache
from mtaio.cache import TTLCache

cache = TTLCache[str]()

@with_cache(cache)
async def expensive_calculation(input: str) -> str:
    return await compute_result(input)

# カスタムキー関数付き
@with_cache(cache, key_func=lambda x, y: f"{x}:{y}")
async def parameterized_operation(x: int, y: int) -> int:
    return await compute(x, y)
```

## 高度な使用法

### デコレータの組み合わせ

デコレータを組み合わせて複数の動作を追加できます:

```python
@with_timeout(5.0)
@with_retry(max_attempts=3)
@with_cache(cache)
async def robust_operation() -> dict:
    return await fetch_data()
```

### カスタムアダプター

カスタムアダプターの作成:

```python
from mtaio.decorators import CallbackAdapter

class CustomAdapter:
    def __init__(self, timeout: float = 30.0):
        self.adapter = CallbackAdapter[str](timeout)
    
    def callback(self, result: str) -> None:
        self.adapter.callback(result)
    
    async def wait(self) -> str:
        return await self.adapter.wait()
```

### エラー処理

デコレータ固有のエラー処理:

```python
from mtaio.exceptions import (
    TimeoutError,
    RetryError,
    RateLimitError,
    CircuitBreakerError
)

async def handle_errors():
    try:
        await protected_operation()
    except TimeoutError:
        # タイムアウトの処理
        pass
    except RetryError as e:
        # リトライ回数超過の処理
        print(f"{e.attempts}回の試行後に失敗しました")
    except RateLimitError as e:
        # レート制限の処理
        print(f"レート制限を超過しました: {e.limit}")
```

## ベストプラクティス

1. **デコレータの順序**
   ```python
   # タイムアウトは実行時間を適切に制御するため最外部にする
   @with_timeout(5.0)
   @with_retry(max_attempts=3)
   @with_cache(cache)
   async def optimized_operation():
       pass
   ```

2. **リソースのクリーンアップ**
   ```python
   # 適切なクリーンアップのために非同期コンテキストマネージャを使用
   @async_context_adapter
   @contextmanager
   def managed_resource():
       try:
           yield setup_resource()
       finally:
           cleanup_resource()
   ```

3. **エラー処理**
   ```python
   # より良いエラー制御のために特定の例外を処理
   @with_fallback(
       fallback=default_value,
       exceptions=(ConnectionError, TimeoutError)
   )
   async def safe_operation():
       pass
   ```

## パフォーマンスの考慮事項

1. **キャッシュ戦略**
   ```python
   # 適切なキャッシュ設定を使用
   @with_cache(
       TTLCache[str](
           default_ttl=300.0,  # 5分
           max_size=1000
       )
   )
   async def cached_operation():
       pass
   ```

2. **レート制限**
   ```python
   # 保護とパフォーマンスのバランスを取る
   @with_rate_limit(
       rate=100.0,    # 1秒あたり100回の呼び出し
       burst=20       # バーストを許可
   )
   async def high_throughput_operation():
       pass
   ```

3. **リトライタイミング**
   ```python
   # リトライに指数バックオフを使用
   @with_retry(
       delay=1.0,
       backoff_factor=2.0  # 1秒, 2秒, 4秒, 8秒...
   )
   async def network_operation():
       pass
   ```

## 関連項目

- 基本機能については[コアAPIリファレンス](core.md)を参照
- キャッシュ操作については[キャッシュAPIリファレンス](cache.md)を参照
- リソース管理については[リソースAPIリファレンス](resources.md)を参照
- サンプルコードは[サンプルリポジトリ](https://github.com/t3tra-dev/mtaio/tree/main/examples/decorators.py)を参照
