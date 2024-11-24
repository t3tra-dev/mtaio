# 例外APIリファレンス

`mtaio.exceptions`モジュールは、mtaioアプリケーションのエラー処理のための包括的な例外階層を提供します。

## 例外の階層

### 基本例外

```python
class MTAIOError(Exception):
    """すべてのmtaioエラーの基本例外クラス。"""
    def __init__(self, message: str, *args: Any, **kwargs: Any) -> None:
        self.message = message
        super().__init__(message, *args)
```

すべてのmtaio例外はこの基本クラスを継承します。

## コア例外

### ExecutionError

タスク実行が失敗した場合に発生します。

```python
from mtaio.exceptions import ExecutionError

try:
    async with TaskExecutor() as executor:
        await executor.run(task)
except ExecutionError as e:
    print(f"タスクの実行に失敗しました: {e}")
```

### TimeoutError

操作がタイムアウトした場合に発生します。

```python
from mtaio.exceptions import TimeoutError

try:
    async with TimeoutManager(5.0):
        await long_running_operation()
except TimeoutError as e:
    print(f"操作がタイムアウトしました: {e}")
```

### RetryError

リトライ回数を超過した場合に発生します。

```python
class RetryError(MTAIOError):
    def __init__(
        self,
        message: str,
        attempts: Optional[int] = None,
        last_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.attempts = attempts
        self.last_error = last_error

# 使用例
try:
    @with_retry(max_attempts=3)
    async def unstable_operation():
        pass
except RetryError as e:
    print(f"{e.attempts}回の試行後に失敗しました")
    if e.last_error:
        print(f"最後のエラー: {e.last_error}")
```

## リソース管理例外

### ResourceLimitError

リソース制限を超過した場合に発生します。

```python
from mtaio.exceptions import ResourceLimitError

try:
    limiter = RateLimiter(10.0)  # 1秒あたり10回の操作
    await limiter.acquire()
except ResourceLimitError as e:
    print(f"レート制限を超過しました: {e}")
```

### ResourceLockError

リソースのロック操作が失敗した場合に発生します。

```python
from mtaio.exceptions import ResourceLockError

try:
    async with resource_lock:
        await process_resource()
except ResourceLockError as e:
    print(f"ロックの取得に失敗しました: {e}")
```

## キャッシュ例外

### CacheError

キャッシュ操作の基本例外です。

```python
class CacheError(MTAIOError):
    """キャッシュ関連エラーの基本例外"""
    pass

class CacheKeyError(CacheError):
    """キャッシュキーが無効または見つからない場合に発生"""
    pass

class CacheConnectionError(CacheError):
    """キャッシュ接続が失敗した場合に発生"""
    pass

# 使用例
try:
    await cache.get("key")
except CacheKeyError:
    print("キーが見つかりません")
except CacheConnectionError:
    print("キャッシュへの接続に失敗しました")
except CacheError as e:
    print(f"キャッシュ操作が失敗しました: {e}")
```

## イベント例外

### EventError

イベント操作の基本例外です。

```python
class EventError(MTAIOError):
    """イベント関連エラーの基本例外"""
    pass

class EventEmitError(EventError):
    """イベント発行が失敗した場合に発生"""
    pass

class EventHandlerError(EventError):
    """イベントハンドラが失敗した場合に発生"""
    pass

# 使用例
try:
    await emitter.emit("event", data)
except EventEmitError:
    print("イベントの発行に失敗しました")
except EventHandlerError:
    print("イベントハンドラが失敗しました")
```

## プロトコル例外

### ProtocolError

プロトコル操作の基本例外です。

```python
class ProtocolError(MTAIOError):
    """プロトコル関連エラーの基本例外"""
    pass

class ASGIError(ProtocolError):
    """ASGIプロトコルエラーが発生した場合に発生"""
    pass

class MQTTError(ProtocolError):
    """MQTTプロトコルエラーが発生した場合に発生"""
    pass

# 使用例
try:
    await mqtt_client.connect()
except MQTTError as e:
    print(f"MQTT接続に失敗しました: {e}")
```

## エラー処理のベストプラクティス

### 具体的な例外処理

最も具体的な例外から最も一般的な例外の順で処理します:

```python
try:
    await operation()
except CacheKeyError:
    # 具体的なキーエラーの処理
    pass
except CacheError:
    # 一般的なキャッシュエラーの処理
    pass
except MTAIOError:
    # 任意のmtaioエラーの処理
    pass
except Exception:
    # 予期しないエラーの処理
    pass
```

### カスタム例外クラス

カスタム例外の作成:

```python
class CustomOperationError(MTAIOError):
    def __init__(
        self,
        message: str,
        operation_id: str,
        *args: Any
    ) -> None:
        super().__init__(message, *args)
        self.operation_id = operation_id

# 使用例
try:
    raise CustomOperationError(
        "操作が失敗しました",
        operation_id="123"
    )
except CustomOperationError as e:
    print(f"操作 {e.operation_id} が失敗しました: {e.message}")
```

### 例外ユーティリティ関数

```python
from mtaio.exceptions import format_exception, wrap_exception

# 詳細付きで例外をフォーマット
try:
    await operation()
except MTAIOError as e:
    error_message = format_exception(e)
    logger.error(error_message)

# 新しい型で例外をラップ
try:
    await operation()
except ConnectionError as e:
    raise wrap_exception(
        e,
        CacheConnectionError,
        "キャッシュ接続に失敗しました"
    )
```

### 非同期コンテキストマネージャのエラー処理

```python
class SafeResource:
    async def __aenter__(self):
        try:
            await self.connect()
            return self
        except Exception as e:
            raise ResourceError("リソースの取得に失敗しました") from e

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            await self.disconnect()
        except Exception as e:
            # クリーンアップ中のエラーはログに記録するだけ
            logger.error(f"クリーンアップエラー: {e}")
```

## 一般的なエラーパターン

### リトライパターン

```python
async def with_retry(
    operation: Callable,
    max_attempts: int = 3,
    exceptions: Tuple[Type[Exception], ...] = (MTAIOError,)
):
    last_error = None
    for attempt in range(max_attempts):
        try:
            return await operation()
        except exceptions as e:
            last_error = e
            if attempt == max_attempts - 1:
                raise RetryError(
                    "リトライ後も操作が失敗しました",
                    attempts=attempt + 1,
                    last_error=last_error
                )
            await asyncio.sleep(2 ** attempt)
```

### サーキットブレーカーパターン

```python
class CircuitBreakerError(MTAIOError):
    def __init__(
        self,
        message: str,
        failures: Optional[int] = None,
        reset_timeout: Optional[float] = None
    ):
        super().__init__(message)
        self.failures = failures
        self.reset_timeout = reset_timeout

# 使用例
breaker = CircuitBreaker(failure_threshold=5)
try:
    await breaker.call(operation)
except CircuitBreakerError as e:
    print(f"サーキットブレーカーが開きました: {e.failures}回の失敗")
```

## 関連項目

- 基本機能については[コアAPIリファレンス](core.md)を参照
- イベント処理については[イベントAPIリファレンス](events.md)を参照
- サンプルコードは[サンプルリポジトリ](https://github.com/t3tra-dev/mtaio/tree/main/examples/error-handling.py)を参照
