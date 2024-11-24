# キャッシュAPIリファレンス

`mtaio.cache`モジュールは、データを非同期で保存および取得するための様々なキャッシュ機能を提供します。

## 概要

キャッシュモジュールには以下の主要なコンポーネントが含まれています:

- `TTLCache`: 有効期限(Time-to-live)付きキャッシュの実装
- `DistributedCache`: 複数ノードにまたがる分散キャッシュ
- 各種キャッシュポリシー(LRU, LFU, FIFO)

## TTLCache

`TTLCache[T]`は、有効期限をサポートする汎用キャッシュ実装です。

### 基本的な使い方

```python
from mtaio.cache import TTLCache

# キャッシュインスタンスの作成
cache = TTLCache[str](
    default_ttl=300.0,  # 5分間のTTL
    max_size=1000
)

# 値の設定
await cache.set("key", "value")

# 値の取得
value = await cache.get("key")
```

### クラスリファレンス

```python
class TTLCache[T]:
    def __init__(
        self,
        default_ttl: float = 300.0,
        max_size: Optional[int] = None,
        cleanup_interval: float = 60.0,
        eviction_policy: EvictionPolicy = EvictionPolicy.LRU,
        on_evicted: Optional[Callable[[str, T], Awaitable[None]]] = None,
    ):
        """
        TTLキャッシュを初期化します。

        Args:
            default_ttl (float): デフォルトの有効期限（秒）
            max_size (Optional[int]): キャッシュの最大サイズ（Noneは無制限）
            cleanup_interval (float): クリーンアップ間隔（秒）
            eviction_policy (EvictionPolicy): キャッシュの退避ポリシー
            on_evicted (Optional[Callable[[str, T], Awaitable[None]]]): アイテム退避時のコールバック
        """
```

### メソッド

#### `async def set(key: str, value: T, ttl: Optional[float] = None) -> None`
キャッシュに値を設定します(オプションでTTLを指定可能)。

```python
# デフォルトのTTLで設定
await cache.set("key", "value")

# カスタムTTLで設定
await cache.set("key", "value", ttl=60.0)  # 1分間のTTL
```

#### `async def get(key: str, default: Optional[T] = None) -> Optional[T]`
キャッシュから値を取得します。

```python
# デフォルト値付きで取得
value = await cache.get("key", default="デフォルト値")

# 値の存在確認
if (value := await cache.get("key")) is not None:
    print(f"値が見つかりました: {value}")
```

#### `async def delete(key: str) -> None`
キャッシュから値を削除します。

```python
await cache.delete("key")
```

#### `async def clear() -> None`
すべてのキャッシュエントリをクリアします。

```python
await cache.clear()
```

#### `async def touch(key: str, ttl: Optional[float] = None) -> bool`
アイテムのTTLを更新します。

```python
# TTLを延長
if await cache.touch("key", ttl=300.0):
    print("TTLが更新されました")
```

#### バッチ操作

```python
# 複数の値を設定
await cache.set_many({
    "key1": "value1",
    "key2": "value2"
})

# 複数の値を取得
values = await cache.get_many(["key1", "key2"])

# 複数の値を削除
await cache.delete_many(["key1", "key2"])
```

## DistributedCache

`DistributedCache[T]`は、複数のノードにまたがる分散キャッシュを提供します。

### 基本的な使い方

```python
from mtaio.cache import DistributedCache

# 分散キャッシュの作成
cache = DistributedCache[str](
    nodes=[
        ("localhost", 5000),
        ("localhost", 5001)
    ],
    replication_factor=2,  # レプリケーション係数
    read_quorum=1         # 読み取りクォーラム
)

async with cache:
    await cache.set("key", "value")
    value = await cache.get("key")
```

### クラスリファレンス

```python
class DistributedCache[T]:
    def __init__(
        self,
        nodes: List[Tuple[str, int]],
        replication_factor: int = 2,
        read_quorum: int = 1,
    ):
        """
        分散キャッシュを初期化します。

        Args:
            nodes (List[Tuple[str, int]]): キャッシュノードのアドレスリスト
            replication_factor (int): レプリカの数
            read_quorum (int): 読み取りコンセンサスに必要なノード数
        """
```

### メソッド

TTLCacheと同様の機能に加えて、分散機能を提供します:

#### `async def set(key: str, value: T, ttl: Optional[float] = None) -> None`
分散ノード間で値を設定します。

```python
await cache.set("key", "value")
```

#### `async def get(key: str) -> Optional[T]`
クォーラムを使用して分散キャッシュから値を取得します。

```python
value = await cache.get("key")
```

## キャッシュポリシー

### EvictionPolicy

キャッシュ退避ポリシーを定義する列挙型:

```python
class EvictionPolicy(Enum):
    LRU = auto()  # 最も長く使用されていないものを退避
    LFU = auto()  # 最も使用頻度の低いものを退避
    FIFO = auto() # 最も古いものを退避
```

### 特殊化されたキャッシュクラス

#### TTLLRUCache

LRU特化型のTTLキャッシュ実装。

```python
from mtaio.cache import TTLLRUCache

cache = TTLLRUCache[str](max_size=1000)
await cache.set("key", "value")
```

#### TTLLFUCache

LFU特化型のTTLキャッシュ実装。

```python
from mtaio.cache import TTLLFUCache

cache = TTLLFUCache[str](max_size=1000)
await cache.set("key", "value")
```

#### TTLFIFOCache

FIFO特化型のTTLキャッシュ実装。

```python
from mtaio.cache import TTLFIFOCache

cache = TTLFIFOCache[str](max_size=1000)
await cache.set("key", "value")
```

## 統計とモニタリング

キャッシュ実装は統計情報の追跡を提供します:

```python
from mtaio.cache import TTLCache

cache = TTLCache[str]()

# キャッシュ統計の取得
stats = cache.get_stats()
print(f"キャッシュヒット数: {stats.hits}")
print(f"キャッシュミス数: {stats.misses}")
print(f"ヒット率: {stats.hit_rate:.2f}")
```

### CacheStatsクラス

```python
@dataclass
class CacheStats:
    hits: int = 0          # ヒット数
    misses: int = 0        # ミス数
    evictions: int = 0     # 退避数
    expirations: int = 0   # 有効期限切れ数
    items: int = 0         # アイテム数
```

## エラー処理

キャッシュモジュールは以下の例外型を定義します:

```python
from mtaio.exceptions import (
    CacheError,          # 基本キャッシュ例外
    CacheKeyError,       # 無効または未発見のキー
    CacheConnectionError # 接続失敗
)

try:
    await cache.get("key")
except CacheKeyError:
    print("キーが見つかりません")
except CacheConnectionError:
    print("接続に失敗しました")
except CacheError as e:
    print(f"キャッシュエラー: {e}")
```

## 高度な使用法

### カスタムキャッシュの実装

カスタムキャッシュ実装の作成:

```python
from mtaio.cache import TTLCache
from mtaio.typing import CacheKey, CacheValue

class CustomCache(TTLCache[str]):
    async def pre_set(self, key: str, value: str) -> None:
        # キャッシュ設定前の前処理
        pass
    
    async def post_get(self, key: str, value: Optional[str]) -> Optional[str]:
        # キャッシュ取得後の後処理
        return value
```

### キャッシュデコレータ

関数の結果をキャッシュするデコレータの使用:

```python
from mtaio.decorators import with_cache
from mtaio.cache import TTLCache

cache = TTLCache[str]()

@with_cache(cache)
async def expensive_operation(param: str) -> str:
    # 重い計算処理
    return result
```

## ベストプラクティス

1. **TTLの設定**
   ```python
   # 頻繁に変更されるデータには短いTTL
   volatile_cache = TTLCache[str](default_ttl=60.0)
   
   # 安定したデータには長いTTL
   stable_cache = TTLCache[str](default_ttl=3600.0)
   ```

2. **リソース管理**
   ```python
   async with TTLCache[str]() as cache:
       # キャッシュは自動的にクリーンアップされます
       pass
   ```

3. **エラー処理**
   ```python
   try:
       async with cache.transaction() as txn:
           await txn.set("key", "value")
   except CacheError:
       # キャッシュエラーの処理
       pass
   ```

4. **モニタリング**
   ```python
   # キャッシュパフォーマンスのモニタリング
   stats = cache.get_stats()
   if stats.hit_rate < 0.5:
       logger.warning("キャッシュヒット率が低下しています")
   ```

## 関連項目

- 基本機能については[コアAPIリファレンス](core.md)を参照
- キャッシュイベントについては[イベントAPIリファレンス](events.md)を参照
- リソース管理については[リソースAPIリファレンス](resources.md)を参照
- サンプルコードは[サンプルリポジトリ](https://github.com/t3tra-dev/mtaio/tree/main/examples/cache.py)を参照
