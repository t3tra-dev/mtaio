# コアAPIリファレンス

`mtaio.core`モジュールは、タスク実行、キュー、基本データ構造など、非同期操作のための基本的なコンポーネントを提供します。

## タスク実行

### TaskExecutor

`TaskExecutor`クラスは、同時実行制限とリソース管理を備えた非同期タスクの制御された実行を提供します。

#### 基本的な使い方

```python
from mtaio.core import TaskExecutor

async def process_item(item: str) -> str:
    return f"処理済み: {item}"

# 基本的な実行
async with TaskExecutor() as executor:
    # 単一タスク
    result = await executor.run(process_item("データ"))
    
    # 同時実行制限付きの複数タスク
    items = ["項目1", "項目2", "項目3"]
    results = await executor.gather(
        *(process_item(item) for item in items),
        limit=2  # 最大2つの同時実行タスク
    )
```

#### クラスリファレンス

```python
class TaskExecutor:
    def __init__(
        self,
        thread_pool: Optional[concurrent.futures.ThreadPoolExecutor] = None
    ):
        """
        タスクエグゼキューターを初期化します。

        Args:
            thread_pool: 同期関数を実行するための任意のスレッドプール
        """

    async def run(
        self,
        coro: Awaitable[T],
        *,
        timeout: Optional[float] = None
    ) -> T:
        """
        単一のコルーチンをオプションのタイムアウト付きで実行します。

        Args:
            coro: 実行するコルーチン
            timeout: タイムアウト（秒）

        Returns:
            コルーチンの結果

        Raises:
            TimeoutError: 操作がタイムアウトした場合
            ExecutionError: 実行が失敗した場合
        """

    async def gather(
        self,
        *coroutines: Coroutine[Any, Any, T],
        limit: Optional[int] = None,
        return_exceptions: bool = False,
    ) -> List[T]:
        """
        複数のコルーチンを同時実行制限付きで実行します。

        Args:
            *coroutines: 実行するコルーチン
            limit: 最大同時実行数
            return_exceptions: 例外を発生させる代わりに返すかどうか

        Returns:
            入力コルーチンの順序での結果リスト

        Raises:
            ExecutionError: 実行が失敗し、return_exceptionsがFalseの場合
        """

    async def map(
        self,
        func: AsyncCallable[T],
        *iterables: Any,
        limit: Optional[int] = None,
        return_exceptions: bool = False,
    ) -> List[T]:
        """
        反復可能オブジェクトの各要素に関数を同時に適用します。

        Args:
            func: 適用する非同期関数
            *iterables: 入力となる反復可能オブジェクト
            limit: 最大同時実行数
            return_exceptions: 例外を発生させる代わりに返すかどうか

        Returns:
            結果のリスト
        """
```

### 高度な使用法

#### スレッドプールの実行

```python
from mtaio.core import TaskExecutor

async def process_with_thread_pool():
    async with TaskExecutor() as executor:
        # CPU負荷の高い関数をスレッドプールで実行
        result = await executor.run_in_thread(
            cpu_intensive_function,
            arg1,
            arg2
        )
```

#### エラー処理

```python
from mtaio.exceptions import ExecutionError, TimeoutError

async def handle_execution_errors():
    try:
        async with TaskExecutor() as executor:
            results = await executor.gather(
                *tasks,
                return_exceptions=True
            )
            
            for result in results:
                if isinstance(result, Exception):
                    print(f"タスクが失敗しました: {result}")
    except ExecutionError as e:
        print(f"実行が失敗しました: {e}")
```

## キュー

### AsyncQueue

汎用非同期キューの実装です。

#### 基本的な使い方

```python
from mtaio.core import AsyncQueue

async def producer_consumer():
    queue: AsyncQueue[str] = AsyncQueue(maxsize=10)
    
    # プロデューサー
    await queue.put("項目")
    
    # コンシューマー
    item = await queue.get()
    queue.task_done()
    
    # キューが空になるまで待機
    await queue.join()
```

#### クラスリファレンス

```python
class AsyncQueue[T]:
    def __init__(self, maxsize: int = 0):
        """
        非同期キューを初期化します。

        Args:
            maxsize: キューの最大サイズ(0は無制限)
        """

    async def put(self, item: T) -> None:
        """キューに項目を追加します。"""

    async def get(self) -> T:
        """キューから項目を取り出して返します。"""

    def task_done(self) -> None:
        """以前にキューに入れられたタスクが完了したことを示します。"""

    async def join(self) -> None:
        """キュー内のすべての項目が処理されるまで待機します。"""

    def qsize(self) -> int:
        """キューの現在のサイズを返します。"""

    def empty(self) -> bool:
        """キューが空の場合はTrueを返します。"""

    def full(self) -> bool:
        """キューが満杯の場合はTrueを返します。"""
```

### 特殊なキュー

#### PriorityQueue

優先度に基づいて項目を取り出すキューです。

```python
from mtaio.core import PriorityQueue

async def priority_queue_example():
    queue: PriorityQueue[str] = PriorityQueue()
    
    # 優先度付きで項目を追加（数値が小さいほど優先度が高い）
    await queue.put("通常タスク", priority=2)
    await queue.put("緊急タスク", priority=1)
    
    # 項目は優先度順で取り出される
    item = await queue.get()  # "緊急タスク"が返される
```

#### LIFOQueue

後入れ先出し（LIFO）キューの実装です。

```python
from mtaio.core import LIFOQueue

async def lifo_queue_example():
    stack: LIFOQueue[str] = LIFOQueue()
    
    await stack.put("1番目")
    await stack.put("2番目")
    
    item = await stack.get()  # "2番目"が返される
```

## 同期プリミティブ

### Latch

カウントダウンラッチの同期実装です。

```python
from mtaio.core import Latch

async def latch_example():
    # カウント3のラッチを作成
    latch = Latch(3)
    
    # カウントを減らす
    await latch.count_down()
    
    # カウントが0になるまで待機
    await latch.wait(timeout=5.0)  # オプションでタイムアウト
```

#### クラスリファレンス

```python
class Latch:
    def __init__(self, count: int):
        """
        ラッチを初期化します。

        Args:
            count: 初期カウント
        """

    async def count_down(self) -> None:
        """カウントを1つ減らします。"""

    async def wait(self, timeout: Optional[float] = None) -> bool:
        """
        カウントが0になるまで待機します。

        Args:
            timeout: 待機する最大時間(秒)

        Returns:
            カウントが0になった場合はTrue、タイムアウトした場合はFalse
        """

    def get_count(self) -> int:
        """現在のカウントを取得します。"""
```

## ベストプラクティス

### リソース管理

```python
# クリーンアップのために常に非同期コンテキストマネージャを使用
async with TaskExecutor() as executor:
    # リソースは自動的にクリーンアップされる
    pass

# キューのクリーンアップを処理
queue = AsyncQueue[str]()
try:
    await queue.put("項目")
    item = await queue.get()
finally:
    # 残りの項目をクリーンアップ
    while not queue.empty():
        await queue.get()
```

### 同時実行制御

```python
# 同時実行タスクを制限
async with TaskExecutor() as executor:
    results = await executor.gather(
        *long_running_tasks,
        limit=5  # 同時実行タスクの過剰を防止
    )

# キューサイズを制御
queue = AsyncQueue[str](maxsize=100)  # 無制限の成長を防止
```

### エラー処理

```python
from mtaio.exceptions import ExecutionError

async def handle_execution():
    try:
        async with TaskExecutor() as executor:
            await executor.run(risky_operation())
    except ExecutionError as e:
        # 実行エラーを処理
        logger.error(f"実行に失敗しました: {e}")
    except TimeoutError as e:
        # タイムアウトを処理
        logger.error(f"操作がタイムアウトしました: {e}")
```

## パフォーマンスのヒント

1. **タスクのバッチ処理**
   ```python
   # スループット向上のためにタスクをバッチで処理
   async with TaskExecutor() as executor:
       for batch in chunks(tasks, size=10):
           await executor.gather(*batch, limit=5)
   ```

2. **キューのサイズ設定**
   ```python
   # 適切なキューサイズを設定
   queue = AsyncQueue[str](
       maxsize=1000  # メモリ問題を防止
   )
   ```

3. **リソース制限**
   ```python
   # リソース使用を制御
   executor = TaskExecutor(
       thread_pool=ThreadPoolExecutor(max_workers=4)
   )
   ```

## 関連項目

- キャッシュ機能については[キャッシュAPIリファレンス](cache.md)を参照
- イベント処理については[イベントAPIリファレンス](events.md)を参照
- リソース管理については[リソースAPIリファレンス](resources.md)を参照
- サンプルコードは[サンプルリポジトリ](https://github.com/t3tra-dev/mtaio/tree/main/examples/core.py)を参照
