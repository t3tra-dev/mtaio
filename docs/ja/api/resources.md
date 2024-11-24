# リソースAPIリファレンス

`mtaio.resources`モジュールは、レート制限、タイムアウト、同時実行制御を含むシステムリソースを管理するためのコンポーネントを提供します。

## RateLimiter

### 基本的な使い方

```python
from mtaio.resources import RateLimiter

# レート制限の作成
limiter = RateLimiter(10.0)  # 1秒あたり10回の操作

# デコレータとしての使用
@limiter.limit
async def rate_limited_operation():
    await perform_operation()

# コンテキストマネージャとしての使用
async def manual_rate_limit():
    async with limiter:
        await perform_operation()
```

### クラスリファレンス

```python
class RateLimiter:
    def __init__(
        self,
        rate: float,
        burst: Optional[int] = None
    ):
        """
        レート制限を初期化します。

        Args:
            rate: 1秒あたりの最大操作回数
            burst: 最大バーストサイズ（Noneの場合はレートベースのバースト）
        """

    async def acquire(self, tokens: int = 1) -> None:
        """
        レート制限からトークンを取得します。

        Args:
            tokens: 取得するトークン数

        Raises:
            ResourceLimitError: レート制限を超過した場合
        """

    def limit(
        self,
        func: Optional[Callable[..., Awaitable[T]]] = None,
        *,
        tokens: int = 1
    ) -> Callable[..., Awaitable[T]]:
        """関数にレート制限を適用するデコレータ。"""
```

## TimeoutManager

非同期操作のタイムアウト制御を提供します。

### 基本的な使い方

```python
from mtaio.resources import TimeoutManager

async def operation_with_timeout():
    # 一連の操作にタイムアウトを設定
    async with TimeoutManager(5.0) as tm:  # 5秒のタイムアウト
        result = await tm.run(long_running_operation())
        
        # 特定の操作に異なるタイムアウトを設定
        result2 = await tm.run(
            another_operation(),
            timeout=2.0  # 2秒のタイムアウト
        )
```

### クラスリファレンス

```python
class TimeoutManager:
    def __init__(self, default_timeout: Optional[float] = None):
        """
        タイムアウトマネージャーを初期化します。

        Args:
            default_timeout: デフォルトのタイムアウト（秒）
        """

    async def run(
        self,
        coro: Awaitable[T],
        *,
        timeout: Optional[float] = None
    ) -> T:
        """
        コルーチンをタイムアウト付きで実行します。

        Args:
            coro: 実行するコルーチン
            timeout: オプションのタイムアウト上書き

        Returns:
            コルーチンの実行結果

        Raises:
            TimeoutError: 操作がタイムアウトした場合
        """
```

## ConcurrencyLimiter

同時実行操作の数を制御します。

### 基本的な使い方

```python
from mtaio.resources import ConcurrencyLimiter

# 最大5つの同時実行操作を許可するリミッターを作成
limiter = ConcurrencyLimiter(5)

@limiter.limit
async def concurrent_operation():
    await process_task()

# 手動での使用
async def manual_concurrency():
    async with limiter:
        await perform_operation()
```

### クラスリファレンス

```python
class ConcurrencyLimiter:
    def __init__(self, limit: int):
        """
        同時実行制限を初期化します。

        Args:
            limit: 最大同時実行数
        """

    async def acquire(self) -> None:
        """
        実行許可を取得します。

        Raises:
            ResourceLimitError: 制限を超過した場合
        """

    def limit(
        self,
        func: Callable[..., Awaitable[T]]
    ) -> Callable[..., Awaitable[T]]:
        """同時実行を制限するデコレータ。"""
```

## ResourceGroup

複数のリソースを一緒に管理します。

### 基本的な使い方

```python
from mtaio.resources import ResourceGroup

async def manage_resources():
    group = ResourceGroup()
    
    # グループにリソースを追加
    rate_limiter = await group.add(RateLimiter(10.0))
    timeout = await group.add(TimeoutManager(5.0))
    
    # リソースは自動的に管理される
    async with group:
        async with timeout:
            await rate_limiter.acquire()
            await perform_operation()
```

### クラスリファレンス

```python
class ResourceGroup:
    async def add(self, resource: Any) -> Any:
        """
        リソースをグループに追加します。

        Args:
            resource: 管理するリソース

        Returns:
            追加されたリソース
        """

    async def remove(self, resource: Any) -> None:
        """
        リソースをグループから削除します。

        Args:
            resource: 削除するリソース
        """
```

## 高度な機能

### 適応型レート制限

```python
from mtaio.resources import RateLimiter
from typing import Dict

class AdaptiveRateLimiter(RateLimiter):
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

### カスケードタイムアウト

```python
from mtaio.resources import TimeoutManager
from contextlib import asynccontextmanager

class TimeoutController:
    def __init__(self):
        self.timeouts = TimeoutManager()
    
    @asynccontextmanager
    async def cascading_timeout(self, timeouts: list[float]):
        """フォールバック付きのカスケードタイムアウトを実装。"""
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

## ベストプラクティス

### リソースのクリーンアップ

```python
from contextlib import AsyncExitStack

async def cleanup_resources():
    async with AsyncExitStack() as stack:
        # スタックにリソースを追加
        rate_limiter = await stack.enter_async_context(RateLimiter(10.0))
        timeout = await stack.enter_async_context(TimeoutManager(5.0))
        
        # リソースは自動的にクリーンアップされる
```

### エラー処理

```python
from mtaio.exceptions import ResourceLimitError, TimeoutError

async def handle_resource_errors():
    try:
        async with TimeoutManager(5.0) as tm:
            await tm.run(operation())
    except TimeoutError:
        logger.error("操作がタイムアウトしました")
    except ResourceLimitError as e:
        logger.error(f"リソース制限を超過しました: {e}")
```

### パフォーマンス最適化

1. **レート制限戦略**
   ```python
   # 保護とパフォーマンスのバランスを取る
   rate_limiter = RateLimiter(
       rate=100.0,    # 1秒あたり100操作
       burst=20       # 20操作のバーストを許可
   )
   ```

2. **タイムアウト設定**
   ```python
   # 適切なタイムアウトを設定
   timeout_manager = TimeoutManager(
       default_timeout=30.0  # デフォルト30秒
   )
   ```

3. **同時実行制御**
   ```python
   # システム容量に基づいて同時実行を制限
   concurrency_limiter = ConcurrencyLimiter(
       limit=cpu_count() * 2  # CPUコアあたり2操作
   )
   ```

## エラー処理の例

```python
from mtaio.exceptions import (
    ResourceError,
    ResourceLimitError,
    TimeoutError
)

async def handle_errors():
    try:
        async with RateLimiter(10.0) as limiter:
            await limiter.acquire()
            
    except ResourceLimitError:
        # レート制限超過の処理
        logger.warning("レート制限を超過しました")
        await asyncio.sleep(1)
        
    except TimeoutError:
        # タイムアウトの処理
        logger.error("操作がタイムアウトしました")
        
    except ResourceError as e:
        # 一般的なリソースエラーの処理
        logger.error(f"リソースエラー: {e}")
```

## 統合例

### Webアプリケーション

```python
from mtaio.resources import RateLimiter, TimeoutManager

class RateLimitedAPI:
    def __init__(self):
        self.rate_limiter = RateLimiter(100.0)  # 1秒あたり100リクエスト
        self.timeout = TimeoutManager(5.0)      # 5秒のタイムアウト
    
    async def handle_request(self, request):
        async with self.timeout:
            await self.rate_limiter.acquire()
            return await process_request(request)
```

### タスク処理

```python
from mtaio.resources import ConcurrencyLimiter

class TaskProcessor:
    def __init__(self):
        self.limiter = ConcurrencyLimiter(10)  # 10個の同時タスク
    
    async def process_tasks(self, tasks: list):
        async with self.limiter:
            results = []
            for task in tasks:
                result = await self.process_task(task)
                results.append(result)
            return results
```

## 関連項目

- 基本機能については[コアAPIリファレンス](core.md)を参照
- イベント処理については[イベントAPIリファレンス](events.md)を参照
- サンプルコードは[サンプルリポジトリ](https://github.com/t3tra-dev/mtaio/tree/main/examples/resources.py)を参照
