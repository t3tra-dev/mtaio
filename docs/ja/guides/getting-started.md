# mtaioを始める

このガイドではmtaioフレームワークの使い方について説明します。インストール、基本的な概念、そして簡単なアプリケーションの作成方法を順を追って解説します。

## インストール

まず、pipを使用してmtaioをインストールします:

```bash
pip install mtaio
```

## 基本的な概念

mtaioは以下の核となる概念に基づいて構築されています:

1. **非同期優先**: すべてがPythonの`asyncio`と連携するように設計
2. **リソース管理**: システムリソースを効率的に扱うための組み込みツール
3. **イベント駆動**: リアクティブなアプリケーションを構築するためのイベントベースアーキテクチャ
4. **型安全性**: より良い開発体験のための完全な型ヒントサポート

## 最初のmtaioアプリケーション

mtaioの基本機能を示す簡単なアプリケーションを作成してみましょう。

```python
import asyncio
from mtaio.events import EventEmitter
from mtaio.cache import TTLCache
from mtaio.core import TaskExecutor

# データプロセッサクラスの作成
class DataProcessor:
    def __init__(self):
        self.emitter = EventEmitter()
        self.cache = TTLCache[str](default_ttl=60.0)  # 60秒のTTL
        self.executor = TaskExecutor()

    async def process_data(self, data: str) -> str:
        # まずキャッシュを確認
        cached_result = await self.cache.get(data)
        if cached_result is not None:
            await self.emitter.emit("cache_hit", data)
            return cached_result

        # データを処理
        async with self.executor as executor:
            result = await executor.run(self.compute_result, data)

        # 結果をキャッシュ
        await self.cache.set(data, result)
        await self.emitter.emit("process_complete", result)
        return result

    async def compute_result(self, data: str) -> str:
        # 重い計算をシミュレート
        await asyncio.sleep(1)
        return data.upper()

# イベントハンドラーの作成
async def handle_cache_hit(event):
    print(f"キャッシュヒット: {event.data}")

async def handle_process_complete(event):
    print(f"処理完了 - 結果: {event.data}")

# メインアプリケーション
async def main():
    # プロセッサの初期化
    processor = DataProcessor()

    # イベントハンドラーの登録
    processor.emitter.on("cache_hit")(handle_cache_hit)
    processor.emitter.on("process_complete")(handle_process_complete)

    # データの処理
    data_items = ["hello", "world", "hello", "mtaio"]
    for data in data_items:
        result = await processor.process_data(data)
        print(f"'{data}'の処理結果: {result}")

# アプリケーションの実行
if __name__ == "__main__":
    asyncio.run(main())
```

このサンプルでは以下の機能を示しています:

1. `EventEmitter`を使用したイベント処理
2. `TTLCache`を使用したキャッシュ
3. `TaskExecutor`を使用したタスク実行
4. 適切なasync/awaitの使用

## 次のステップ

基本を理解したら、以下のステップに進むことができます:

1. [mtaioの基本機能](../api/core.md)についてさらに学ぶ
2. [高度な使用パターン](advanced-usage.md)を探る
3. [APIリファレンス](../api/index.md)を確認する
4. [リポジトリのサンプル](https://github.com/t3tra-dev/mtaio/tree/main/examples)を見る

## 一般的なパターン

mtaioアプリケーションでよく使用されるパターンを紹介します:

### リソース管理

```python
from mtaio.resources import RateLimiter

limiter = RateLimiter(10.0)  # 1秒あたり10回の操作

@limiter.limit
async def rate_limited_operation():
    # 処理内容をここに記述
    pass
```

### イベント駆動アーキテクチャ

```python
from mtaio.events import EventEmitter

emitter = EventEmitter()

@emitter.on("event_name")
async def handle_event(event):
    # イベント処理
    pass

# イベントの発行
await emitter.emit("event_name", data)
```

### キャッシュ戦略

```python
from mtaio.cache import TTLCache
from mtaio.decorators import with_cache

cache = TTLCache[str](default_ttl=300.0)  # 5分

@with_cache(cache)
async def cached_operation(key: str) -> str:
    # 重い処理
    return result
```

## ベストプラクティス

1. **型ヒント**: コード品質とIDE支援のために常に型ヒントを使用:
   ```python
   from mtaio.typing import AsyncFunc
   
   async def process_data(data: str) -> str:
       # 処理
       return result
   ```

2. **リソースのクリーンアップ**: 適切なリソースクリーンアップのためにasyncコンテキストマネージャを使用:
   ```python
   async with TaskExecutor() as executor:
       # executorを使用した処理
       pass  # リソースは自動的にクリーンアップされる
   ```

3. **エラー処理**: mtaioの例外階層を使用した適切なエラー処理:
   ```python
   from mtaio.exceptions import MTAIOError
   
   try:
       await operation()
   except MTAIOError as e:
       # mtaio固有のエラーを処理
       pass
   ```

4. **設定**: 設定を分離し、環境変数を使用:
   ```python
   import os
   from mtaio.cache import TTLCache
   
   cache = TTLCache[str](
       default_ttl=float(os.getenv('CACHE_TTL', '300')),
       max_size=int(os.getenv('CACHE_SIZE', '1000'))
   )
   ```

## ヘルプの入手

問題が発生した場合:

1. [トラブルシューティング](troubleshooting.md)ガイドを確認
2. [GitHubリポジトリ](https://github.com/t3tra-dev/mtaio/issues)で類似の問題を検索
3. 未解決の問題の場合は新しいissueを作成

次は[基本的な使い方](basic-usage.md)に進み、mtaioの機能についてより詳しく学びましょう。
