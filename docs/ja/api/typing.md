# 型定義APIリファレンス

`mtaio.typing`モジュールは、より良いコード補完と静的型チェックを可能にする、mtaioフレームワーク全体で使用される型定義とプロトコルを提供します。

## 基本的な型

### ジェネリック型変数

```python
from mtaio.typing import T, T_co, T_contra, K, V

# 基本的なジェネリック型変数
T = TypeVar("T")               # 不変型変数
T_co = TypeVar("T_co", covariant=True)       # 共変型変数
T_contra = TypeVar("T_contra", contravariant=True)  # 反共変型変数
K = TypeVar("K")               # キー型変数
V = TypeVar("V")               # 値型変数
```

### 一般的な型エイリアス

```python
from mtaio.typing import (
    JSON,
    PathLike,
    TimeValue,
    Primitive
)

# JSON互換の型
JSON = Union[Dict[str, Any], List[Any], str, int, float, bool, None]

# パス形式の型
PathLike = Union[str, Path]

# 時間値の型
TimeValue = Union[int, float, timedelta]

# プリミティブ型
Primitive = Union[str, int, float, bool, None]
```

## 関数型

### コールバック型

```python
from mtaio.typing import (
    Callback,
    AsyncCallback,
    ErrorCallback,
    AsyncErrorCallback
)

# 同期および非同期コールバック
Callback = Callable[..., Any]
AsyncCallback = Callable[..., Awaitable[Any]]

# エラー処理コールバック
ErrorCallback = Callable[[Exception], Any]
AsyncErrorCallback = Callable[[Exception], Awaitable[Any]]

# クリーンアップコールバック
CleanupCallback = Callable[[], Any]
AsyncCleanupCallback = Callable[[], Awaitable[Any]]
```

### 関数型定義

```python
from mtaio.typing import (
    SyncFunc,
    AsyncFunc,
    AsyncCallable,
    CoroFunc,
    AnyFunc,
    Decorator
)

# 関数型
SyncFunc = Callable[..., T]
AsyncFunc = Callable[..., Awaitable[T]]
AsyncCallable = Callable[..., Awaitable[T]]
CoroFunc = TypeVar('CoroFunc', bound=AsyncCallable[Any])

# 組み合わせた関数型
AnyFunc = Union[SyncFunc[T], AsyncFunc[T]]

# デコレータ型
Decorator = Callable[[AnyFunc[T]], AnyFunc[T]]
```

## プロトコル定義

### リソース管理

```python
from mtaio.typing import Resource, ResourceManager

@runtime_checkable
class Resource(Protocol):
    """リソースオブジェクトのプロトコル。"""
    
    async def acquire(self) -> None:
        """リソースを取得します。"""
        ...

    async def release(self) -> None:
        """リソースを解放します。"""
        ...

class ResourceManager(AsyncContextManager[Resource], Protocol):
    """リソースマネージャのプロトコル。"""
    
    async def __aenter__(self) -> Resource:
        """コンテキストに入り、リソースを取得します。"""
        ...

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Any,
    ) -> Optional[bool]:
        """コンテキストを抜け、リソースを解放します。"""
        ...
```

### イベント処理

```python
from mtaio.typing import Event, EventHandler

@runtime_checkable
class Event(Protocol[T]):
    """イベントオブジェクトのプロトコル。"""
    
    @property
    def name(self) -> str:
        """イベント名。"""
        ...

    @property
    def data(self) -> T:
        """イベントデータ。"""
        ...

class EventHandler(Protocol[T]):
    """イベントハンドラのプロトコル。"""
    
    async def handle(self, event: Event[T]) -> None:
        """イベントを処理します。"""
        ...
```

### キャッシュ型

```python
from mtaio.typing import CacheKey, CacheValue

@runtime_checkable
class CacheKey(Protocol):
    """キャッシュキーのプロトコル。"""
    
    def __str__(self) -> str:
        """文字列に変換します。"""
        ...

    def __hash__(self) -> int:
        """ハッシュ値を取得します。"""
        ...

class CacheValue(Protocol):
    """キャッシュ値のプロトコル。"""
    
    async def serialize(self) -> bytes:
        """値をシリアライズします。"""
        ...

    @classmethod
    async def deserialize(cls, data: bytes) -> Any:
        """値をデシリアライズします。"""
        ...
```

## ユーティリティ型

### 結果型

```python
from mtaio.typing import Result

class Result(Generic[T]):
    """操作結果のコンテナ。"""

    def __init__(
        self,
        value: Optional[T] = None,
        error: Optional[Exception] = None
    ) -> None:
        self.value = value
        self.error = error
        self.success = error is None

    def unwrap(self) -> T:
        """
        値を取得するか、エラーを発生させます。

        Returns:
            格納されている値

        Raises:
            エラーが存在する場合はそのエラー
        """
        if self.error:
            raise self.error
        if self.value is None:
            raise ValueError("結果に値がありません")
        return self.value
```

### 設定型

```python
from mtaio.typing import ConfigProtocol, Config

@runtime_checkable
class ConfigProtocol(Protocol):
    """設定オブジェクトのプロトコル。"""

    def get(self, key: str, default: Any = None) -> Any:
        """設定値を取得します。"""
        ...

    def get_path(self, key: str, default: Optional[PathLike] = None) -> PathLike:
        """パス値を取得します。"""
        ...

    def get_timedelta(self, key: str, default: Optional[TimeValue] = None) -> timedelta:
        """時間差分値を取得します。"""
        ...

class Config(Dict[str, Any], ConfigProtocol):
    """設定の実装。"""
    pass
```

### ファクトリ型

```python
from mtaio.typing import Factory, AsyncFactory

class Factory(Protocol[T]):
    """ファクトリオブジェクトのプロトコル。"""
    
    def create(self) -> T:
        """新しいインスタンスを作成します。"""
        ...

class AsyncFactory(Protocol[T]):
    """非同期ファクトリオブジェクトのプロトコル。"""
    
    async def create(self) -> T:
        """新しいインスタンスを非同期に作成します。"""
        ...
```

## ベストプラクティス

### 型ヒントの使用

```python
from mtaio.typing import AsyncFunc, Result

# 関数の型ヒント
async def process_data(func: AsyncFunc[str]) -> Result[str]:
    try:
        result = await func()
        return Result(value=result)
    except Exception as e:
        return Result(error=e)

# プロトコルの使用
class DataProcessor(AsyncFactory[str]):
    async def create(self) -> str:
        return await self.process()

    async def process(self) -> str:
        # 処理の実装
        return "処理済みデータ"
```

### ジェネリック型の使用

```python
from mtaio.typing import T, CacheValue

class CustomCache(Generic[T]):
    async def get(self, key: str) -> Optional[T]:
        ...

    async def set(self, key: str, value: T) -> None:
        ...

# 特定の型での実装
cache = CustomCache[str]()
```

### プロトコルの継承

```python
from mtaio.typing import Resource, EventHandler

class ManagedResource(Resource, EventHandler[str]):
    async def acquire(self) -> None:
        ...

    async def release(self) -> None:
        ...

    async def handle(self, event: Event[str]) -> None:
        ...
```

## エラー処理

```python
from mtaio.typing import Result, AsyncFunc

async def safe_operation(func: AsyncFunc[T]) -> Result[T]:
    try:
        result = await func()
        return Result(value=result)
    except Exception as e:
        logger.error(f"操作が失敗しました: {e}")
        return Result(error=e)

# 使用例
result = await safe_operation(async_function)
if result.success:
    value = result.unwrap()
else:
    handle_error(result.error)
```

## 統合例

### リソース管理

```python
from mtaio.typing import Resource, ResourceManager

class DatabaseConnection(Resource):
    async def acquire(self) -> None:
        await self.connect()

    async def release(self) -> None:
        await self.disconnect()

class ConnectionManager(ResourceManager[DatabaseConnection]):
    async def __aenter__(self) -> DatabaseConnection:
        conn = DatabaseConnection()
        await conn.acquire()
        return conn

    async def __aexit__(self, *args) -> None:
        await self.resource.release()
```

### イベントシステム

```python
from mtaio.typing import Event, EventHandler

class DataEvent(Event[Dict[str, Any]]):
    def __init__(self, name: str, data: Dict[str, Any]):
        self._name = name
        self._data = data

    @property
    def name(self) -> str:
        return self._name

    @property
    def data(self) -> Dict[str, Any]:
        return self._data

class DataHandler(EventHandler[Dict[str, Any]]):
    async def handle(self, event: Event[Dict[str, Any]]) -> None:
        await self.process_data(event.data)
```

## 関連項目

- 基本機能については[コアAPIリファレンス](core.md)を参照
- エラー処理については[例外APIリファレンス](exceptions.md)を参照
- サンプルコードは[サンプルリポジトリ](https://github.com/t3tra-dev/mtaio/tree/main/examples/typing.py)を参照
