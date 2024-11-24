# mtaioドキュメント

mtaio(Multi-threaded Async I/O)は効率的な非同期アプリケーションを構築するための包括的なPythonフレームワークです。非同期I/O操作、イベント処理、キャッシュ、モニタリングなどを扱うための堅牢なツールとユーティリティを提供します。

## 主な機能

- **非同期優先設計**: Pythonの`asyncio`を基盤に最適なパフォーマンスを実現
- **リソース管理**: レート制限とタイムアウト制御を備えた効率的なシステムリソース管理
- **イベント処理**: イベント駆動型アプリケーションを構築するための堅牢なイベントエミッターとハンドラーシステム
- **キャッシュシステム**: TTLと分散キャッシュをサポートする柔軟なキャッシュ機能
- **プロトコルサポート**: ASGI、MQTT、メールプロトコルの組み込みサポート
- **モニタリングとプロファイリング**: システム監視とパフォーマンスプロファイリングのための包括的なツール
- **型安全性**: mypyとの互換性を持つ完全な型ヒントサポート
- **拡張可能なアーキテクチャ**: 特定のニーズに合わせて簡単に拡張・カスタマイズ可能

## 使用例

```python
from mtaio.core import TaskExecutor
from mtaio.cache import TTLCache
from mtaio.events import EventEmitter

# 並行性制御付きのタスク実行
async with TaskExecutor() as executor:
    results = await executor.gather(
        task1(), 
        task2(),
        limit=5  # 最大同時実行タスク数
    )

# TTL付きキャッシュ
cache = TTLCache[str](
    default_ttl=300.0,  # 5分
    max_size=1000
)
await cache.set("key", "value")
value = await cache.get("key")

# イベント処理
emitter = EventEmitter()

@emitter.on("user_login")
async def handle_login(event):
    user = event.data
    print(f"ユーザー {user.name} がログインしました")

await emitter.emit("user_login", user_data)
```

## ドキュメント構成

このドキュメントは以下のセクションで構成されています:

- **[はじめに](guides/getting-started.md)**: mtaioの簡単な紹介
- **[インストール](guides/installation.md)**: インストール手順と要件
- **[基本的な使い方](guides/basic-usage.md)**: 基本的な概念と使用パターン
- **[高度な使い方](guides/advanced-usage.md)**: 詳細なガイドと高度な機能
- **[APIリファレンス](api/cache.md)**: 完全なAPI仕様
- **[デプロイメント](guides/deployment.md)**: 本番環境へのデプロイメントガイドライン
- **[トラブルシューティング](guides/troubleshooting.md)**: 一般的な問題と解決方法

## ヘルプの入手

- **GitHub Issues**: バグ報告や機能リクエストは[GitHubリポジトリ](https://github.com/t3tra-dev/mtaio)で受け付けています
- **ドキュメント**: 上記の包括的なドキュメントセクションをご覧ください
- **サンプル**: リポジトリの[examplesディレクトリ](https://github.com/t3tra-dev/mtaio/tree/main/examples)をご確認ください

## 動作要件

- Python 3.11以降
- OS: プラットフォーム非依存

## ライセンス

mtaioはMITライセンスの下で公開されています。詳細は[LICENSE](https://github.com/t3tra-dev/mtaio/blob/main/LICENSE)ファイルをご覧ください。
