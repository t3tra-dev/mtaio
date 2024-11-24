# データAPIリファレンス

`mtaio.data`モジュールは、パイプライン、ストリーム、オブザーバブルを含むデータ処理と変換のためのコンポーネントを提供します。

## パイプライン処理

### Pipeline

`Pipeline`クラスは、設定可能なステージを通じた順次データ処理のフレームワークを提供します。

#### 基本的な使い方

```python
from mtaio.data import Pipeline, Stage

# 処理ステージの定義
class ValidationStage(Stage[dict, dict]):
    async def process(self, data: dict) -> dict:
        if "id" not in data:
            raise ValueError("idフィールドが必要です")
        return data

class EnrichmentStage(Stage[dict, dict]):
    async def process(self, data: dict) -> dict:
        data["timestamp"] = time.time()
        return data

# パイプラインの作成と使用
async def process_data():
    pipeline = Pipeline()
    pipeline.add_stage(ValidationStage())
    pipeline.add_stage(EnrichmentStage())
    
    async with pipeline:
        result = await pipeline.process({"id": "123"})
```

#### クラスリファレンス

```python
class Pipeline[T, U]:
    def __init__(self, buffer_size: int = 0):
        """
        パイプラインを初期化します。

        Args:
            buffer_size: ステージ間のバッファサイズ
        """

    def add_stage(self, stage: Stage) -> "Pipeline":
        """処理ステージを追加します。"""
        
    async def process(self, data: T) -> U:
        """単一のアイテムをパイプラインで処理します。"""

    async def process_many(
        self,
        items: Union[Iterable[T], AsyncIterable[T]]
    ) -> List[U]:
        """複数のアイテムをパイプラインで処理します。"""
```

### Stage

パイプラインステージのベースクラスです。

```python
from mtaio.data import Stage

class CustomStage(Stage[T, U]):
    async def process(self, data: T) -> U:
        """単一のアイテムを処理します。"""
        return processed_data

    async def setup(self) -> None:
        """パイプライン開始時に呼び出されます。"""
        pass

    async def cleanup(self) -> None:
        """パイプライン終了時に呼び出されます。"""
        pass
```

### 提供されるステージ

#### BatchStage

データをバッチで処理します。

```python
from mtaio.data import BatchStage

class AverageBatchStage(BatchStage[float, float]):
    def __init__(self, batch_size: int = 10):
        super().__init__(batch_size)
    
    async def process_batch(self, batch: List[float]) -> float:
        return sum(batch) / len(batch)
```

#### FilterStage

述語に基づいてデータをフィルタリングします。

```python
from mtaio.data import FilterStage

# フィルターステージの作成
filter_stage = FilterStage(lambda x: x > 0)

# または非同期述語を使用
async def async_predicate(x):
    return x > await get_threshold()

filter_stage = FilterStage(async_predicate)
```

#### MapStage

マッピング関数を使用してデータを変換します。

```python
from mtaio.data import MapStage

# マップステージの作成
map_stage = MapStage(lambda x: x * 2)

# または非同期マッピングを使用
async def async_transform(x):
    return await process_value(x)

map_stage = MapStage(async_transform)
```

## ストリーム処理

### Stream

`Stream`クラスは、データシーケンスを処理するための流暢なインターフェースを提供します。

#### 基本的な使い方

```python
from mtaio.data import Stream

async def process_stream():
    stream = Stream.from_iterable([1, 2, 3, 4, 5])
    
    result = await (stream
        .map(lambda x: x * 2)
        .filter(lambda x: x > 5)
        .reduce(lambda acc, x: acc + x))
```

#### クラスリファレンス

```python
class Stream[T]:
    @classmethod
    def from_iterable(
        cls,
        iterable: Union[Iterable[T], AsyncIterable[T]]
    ) -> "Stream[T]":
        """反復可能オブジェクトからストリームを作成します。"""

    def map(
        self,
        func: Union[Callable[[T], U], Callable[[T], Awaitable[U]]]
    ) -> "Stream[U]":
        """マッピング関数を使用してアイテムを変換します。"""

    def filter(
        self,
        predicate: Union[Callable[[T], bool], Callable[[T], Awaitable[bool]]]
    ) -> "Stream[T]":
        """述語を使用してアイテムをフィルタリングします。"""

    async def reduce(
        self,
        func: Union[Callable[[U, T], U], Callable[[U, T], Awaitable[U]]],
        initial: Optional[U] = None,
    ) -> U:
        """ストリームを単一の値に縮約します。"""
```

### ストリーム操作

#### ウィンドウ処理

```python
from mtaio.data import Stream

async def window_example():
    stream = Stream.from_iterable(range(10))
    
    # スライディングウィンドウ
    async for window in stream.window(size=3, step=1):
        print(f"ウィンドウ: {window}")  # [0,1,2], [1,2,3], ...
```

#### バッチ処理

```python
from mtaio.data import Stream

async def batch_example():
    stream = Stream.from_iterable(range(10))
    
    # バッチで処理
    async for batch in stream.batch(size=3):
        print(f"バッチ: {batch}")  # [0,1,2], [3,4,5], ...
```

## オブザーバーパターン

### Observable

`Observable`クラスは、リアクティブなデータ処理のためのオブザーバーパターンを実装します。

#### 基本的な使い方

```python
from mtaio.data import Observable, Change, ChangeType

class DataStore(Observable[dict]):
    def __init__(self):
        super().__init__()
        self._data = {}
    
    async def update(self, key: str, value: Any) -> None:
        old_value = self._data.get(key)
        self._data[key] = value
        
        await self.notify(Change(
            type=ChangeType.UPDATE,
            path=f"data.{key}",
            value=value,
            old_value=old_value
        ))
```

#### オブザーバー

```python
# オブザーバーの追加
@data_store.on_change
async def handle_change(change: Change[dict]):
    print(f"値が変更されました: {change.value}")

# 1回限りのオブザーバー
@data_store.once
async def handle_first_change(change: Change[dict]):
    print("最初の変更のみ")
```

### バッチ操作

```python
from mtaio.data import Observable

async def batch_updates():
    store = DataStore()
    
    async with store.batch_operations():
        await store.update("key1", "value1")
        await store.update("key2", "value2")
        # すべての変更についてオブザーバーに一度通知されます
```

## ベストプラクティス

### パイプラインの設計

```python
# 明確さのために型ヒントを使用
class ProcessingPipeline(Pipeline[dict, dict]):
    def __init__(self):
        super().__init__()
        self.add_stage(ValidationStage())
        self.add_stage(TransformationStage())
        self.add_stage(EnrichmentStage())

# 適切にクリーンアップを処理
async with ProcessingPipeline() as pipeline:
    results = await pipeline.process_many(items)
```

### ストリーム処理

```python
# 効率的に操作を連鎖
result = await (Stream.from_iterable(data)
    .filter(is_valid)
    .map(transform)
    .batch(100)
    .reduce(aggregate))

# 必要に応じて非同期述語を使用
async def is_valid(item: dict) -> bool:
    return await validate(item)
```

### オブザーバブルの実装

```python
# カスタムオブザーバブルの実装
class DataManager(Observable[T]):
    def __init__(self):
        super().__init__()
        self._cleanup_handlers = []
    
    async def cleanup(self):
        for handler in self._cleanup_handlers:
            self.remove_observer(handler)
```

## パフォーマンスの考慮事項

1. **パイプラインのバッファリング**
   ```python
   # 適切なバッファサイズを使用
   pipeline = Pipeline(buffer_size=1000)
   ```

2. **バッチ処理**
   ```python
   # 最適なバッチサイズでデータを処理
   async for batch in stream.batch(size=optimal_batch_size):
       await process_batch(batch)
   ```

3. **オブザーバーのクリーンアップ**
   ```python
   # 不要になったらオブザーバーを削除
   observable.remove_observer(handler)
   ```

## 関連項目

- 基本機能については[コアAPIリファレンス](core.md)を参照
- キャッシュ操作については[キャッシュAPIリファレンス](cache.md)を参照
- イベント処理については[イベントAPIリファレンス](events.md)を参照
- サンプルコードは[サンプルリポジトリ](https://github.com/t3tra-dev/mtaio/tree/main/examples/data.py)を参照
