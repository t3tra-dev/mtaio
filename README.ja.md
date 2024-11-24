[[英語/English](README.md)]

# `mtaio` - Multi-threaded Async I/O Framework

#### !! `Python3.11+で動作します` !!

`mtaio`は効率的な並行アプリケーションを構築するための高レベルな抽象化を提供する、包括的な非同期I/Oフレームワークです。

## 特徴

- **非同期コア**
  - 並行性制御付きタスク実行
  - 柔軟なキュー実装(優先度、LIFO)
  - ラッチ同期プリミティブ

- **キャッシュ**
  - 複数の退避ポリシー(LRU, LFU, FIFO)を持つTTLベースのキャッシュ
  - ノードレプリケーション付き分散キャッシュ
  - 自動キャッシュクリーンアップと監視

- **データ処理**
  - リアクティブデータ処理のためのObservableパターン
  - カスタマイズ可能なステージを持つパイプライン処理
  - ストリーム処理とオペレータ

- **イベント処理**
  - 優先度サポート付き非同期イベントエミッタ
  - チャネルベースの通信
  - Pub/subパターン実装

- **プロトコルサポート**
  - ASGIアプリケーションフレームワーク
  - MQTTクライアント実装
  - 非同期IMAPとSMTPクライアント

- **リソース管理**
  - トークンバケットアルゴリズムによるレート制限
  - 並行性制限
  - タイムアウト管理
  - リソース監視

## インストール

```bash
pip install mtaio
```

## クイックスタート

以下は、主要な機能を示す簡単な例です:

```python
from mtaio.core import TaskExecutor, RateLimiter, TimeoutManager

async def main():
    # レート制限付きタスク実行器を作成
    executor = TaskExecutor()
    limiter = RateLimiter(rate=10.0)  # 1秒あたり10操作

    @limiter.limit
    async def process_item(item):
        # タイムアウト付きで処理
        async with TimeoutManager(5.0) as tm:
            result = await tm.run(some_operation(item))
            return result

    # 複数のアイテムを並行して処理
    items = range(100)
    results = await executor.map(process_item, items, limit=5)

if __name__ == "__main__":
    asyncio.run(main())
```

## ドキュメント

### コアコンポーネント

#### `TaskExecutor`

`TaskExecutor`は並行性制御付きのコルーチン実行メソッドを提供します:

```python
from mtaio.core import TaskExecutor

async def example():
    executor = TaskExecutor()
    
    # 並行性制限付きで複数のコルーチンを実行
    results = await executor.gather(
        coro1(),
        coro2(),
        limit=5
    )
```

#### キャッシュ

`mtaio`は柔軟なキャッシュソリューションを提供します:

```python
from mtaio.cache import TTLCache, DistributedCache

async def cache_example():
    # シンプルなTTLキャッシュ
    cache = TTLCache[str](
        default_ttl=60.0,
        max_size=1000
    )s
    
    # 分散キャッシュ
    dist_cache = DistributedCache[str](
        nodes=[
            ('localhost', 5000),
            ('localhost', 5001)
        ]
    )
```

#### イベント処理

イベントシステムは優先度付きイベント処理をサポートします:

```python
from mtaio.events import EventEmitter

async def event_example():
    emitter = EventEmitter()

    @emitter.on("user_login")
    async def handle_login(event):
        user = event.data
        print(f"ユーザー {user.name} がログインしました")

    await emitter.emit("user_login", user_data)
```

### 高度な機能

#### リソース管理

レート制限とタイムアウトでリソース使用を制御します:

```python
from mtaio.resources import ResourceLimiter

async def resource_example():
    limiter = ResourceLimiter(
        rate=10.0,      # 1秒あたり10リクエスト
        concurrency=5   # 最大5同時実行
    )

    @limiter.limit
    async def limited_operation():
        await process_request()
```

#### モニタリング

システムリソースとアプリケーションパフォーマンスを監視します:

```python
from mtaio.monitoring import ResourceMonitor

async def monitor_example():
    monitor = ResourceMonitor()

    @monitor.on_threshold_exceeded
    async def handle_alert(metric, value, threshold):
        print(f"アラート: {metric} がしきい値を超えました")

    await monitor.start()
```

## 貢献

`mtaio`への貢献は大歓迎です！以下の手順に従って貢献できます:

1. リポジトリをフォークします: [github.com/t3tra-dev/mtaio](https://github.com/t3tra-dev/mtaio)
2. フィーチャーブランチを作成します: `git checkout -b feat/your-feature`
3. 変更をコミットします: `git commit -m 'Add a new feature'`
4. ブランチをプッシュします: `git push origin feat/your-feature`
5. プルリクエストを送信します。

サポートや質問については、リポジトリの[Issuesセクション](https://github.com/t3tra-dev/mtaio/issues)に問題を報告してください。

## ライセンス

このプロジェクトはMITライセンスの下で提供されています - 詳細は[LICENSE](LICENSE)ファイルをご覧ください。
