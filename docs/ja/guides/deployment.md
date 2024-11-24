# デプロイガイド

このガイドでは、本番環境でmtaioアプリケーションをデプロイする際のベストプラクティスと考慮事項について説明します。

## 環境設定

### システム要件

- Python 3.11以降
- オペレーティングシステム: Pythonをサポートする任意のプラットフォーム(Linux, macOS, Windows)
- メモリ: ワークロードに依存、推奨最小512MB
- CPU: 最低1コア、並行処理には2コア以上を推奨

### 環境変数

環境変数を使用してアプリケーションを設定:

```python
import os
from mtaio.core import TaskExecutor
from mtaio.cache import TTLCache

# 環境変数から設定を読み込み
config = {
    "max_workers": int(os.getenv("MTAIO_MAX_WORKERS", "4")),
    "cache_ttl": float(os.getenv("MTAIO_CACHE_TTL", "300")),
    "cache_size": int(os.getenv("MTAIO_CACHE_SIZE", "1000")),
    "log_level": os.getenv("MTAIO_LOG_LEVEL", "INFO"),
}

# 設定でコンポーネントを初期化
executor = TaskExecutor(max_workers=config["max_workers"])
cache = TTLCache[str](
    default_ttl=config["cache_ttl"],
    max_size=config["cache_size"]
)
```

## 本番環境の設定

### ロギング設定

本番環境用のロギング設定:

```python
import logging
from mtaio.logging import AsyncFileHandler

async def setup_logging():
    logger = logging.getLogger("mtaio")
    logger.setLevel(logging.INFO)
    
    # ローテーション付きファイルハンドラ
    handler = AsyncFileHandler(
        filename="app.log",
        max_bytes=10_000_000,  # 10MB
        backup_count=5
    )
    
    # フォーマットの追加
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
```

### リソース管理

本番環境用のリソース制限の設定:

```python
from mtaio.resources import (
    RateLimiter,
    ConcurrencyLimiter,
    TimeoutManager
)

async def configure_resources():
    # レート制限
    rate_limiter = RateLimiter(
        rate=float(os.getenv("MTAIO_RATE_LIMIT", "100")),  # 1秒あたりのリクエスト数
        burst=int(os.getenv("MTAIO_BURST_LIMIT", "200"))
    )
    
    # 同時実行制限
    concurrency_limiter = ConcurrencyLimiter(
        limit=int(os.getenv("MTAIO_CONCURRENCY_LIMIT", "50"))
    )
    
    # タイムアウト管理
    timeout_manager = TimeoutManager(
        default_timeout=float(os.getenv("MTAIO_DEFAULT_TIMEOUT", "30"))
    )
    
    return rate_limiter, concurrency_limiter, timeout_manager
```

## ヘルスモニタリング

ヘルスチェックとモニタリングの実装:

```python
from mtaio.monitoring import ResourceMonitor
from mtaio.events import EventEmitter

class HealthMonitor:
    def __init__(self):
        self.monitor = ResourceMonitor()
        self.emitter = EventEmitter()
        
    async def start(self):
        # モニタリングのしきい値を設定
        self.monitor.set_threshold("cpu_usage", 80.0)  # CPU 80%
        self.monitor.set_threshold("memory_usage", 90.0)  # メモリ 90%
        
        @self.monitor.on_threshold_exceeded
        async def handle_threshold(metric, value, threshold):
            await self.emitter.emit("health_alert", {
                "metric": metric,
                "value": value,
                "threshold": threshold
            })
        
        await self.monitor.start()
    
    async def get_health_status(self) -> dict:
        stats = await self.monitor.get_current_stats()
        return {
            "status": "healthy" if stats.cpu.usage_percent < 80 else "degraded",
            "cpu_usage": stats.cpu.usage_percent,
            "memory_usage": stats.memory.percent,
            "uptime": stats.uptime
        }
```

## エラー処理

包括的なエラー処理の実装:

```python
from mtaio.exceptions import MTAIOError
from typing import Optional

class ErrorHandler:
    def __init__(self):
        self.logger = logging.getLogger("mtaio.errors")
    
    async def handle_error(
        self,
        error: Exception,
        context: Optional[dict] = None
    ) -> None:
        if isinstance(error, MTAIOError):
            # mtaio固有のエラーを処理
            await self._handle_mtaio_error(error, context)
        else:
            # 予期しないエラーを処理
            await self._handle_unexpected_error(error, context)
    
    async def _handle_mtaio_error(
        self,
        error: MTAIOError,
        context: Optional[dict]
    ) -> None:
        self.logger.error(
            "mtaioエラーが発生しました",
            extra={
                "error_type": type(error).__name__,
                "message": str(error),
                "context": context
            }
        )
    
    async def _handle_unexpected_error(
        self,
        error: Exception,
        context: Optional[dict]
    ) -> None:
        self.logger.critical(
            "予期しないエラーが発生しました",
            exc_info=error,
            extra={"context": context}
        )
```

## デプロイ例

完全なデプロイ設定の例:

```python
import asyncio
from contextlib import AsyncExitStack

async def main():
    # リソースクリーンアップ用のexit stackを初期化
    async with AsyncExitStack() as stack:
        # ロギングの設定
        await setup_logging()
        logger = logging.getLogger("mtaio")
        
        try:
            # リソースの設定
            rate_limiter, concurrency_limiter, timeout_manager = (
                await configure_resources()
            )
            
            # ヘルスモニタリングの設定
            health_monitor = HealthMonitor()
            await stack.enter_async_context(health_monitor)
            
            # エラー処理の設定
            error_handler = ErrorHandler()
            
            # アプリケーションコンポーネントの初期化
            app = Application(
                rate_limiter=rate_limiter,
                concurrency_limiter=concurrency_limiter,
                timeout_manager=timeout_manager,
                error_handler=error_handler
            )
            
            # アプリケーションの起動
            await app.start()
            logger.info("アプリケーションが正常に起動しました")
            
            # シャットダウンシグナルを待機
            await asyncio.Event().wait()
            
        except Exception as e:
            logger.critical("アプリケーションの起動に失敗しました", exc_info=e)
            raise

if __name__ == "__main__":
    asyncio.run(main())
```

## デプロイチェックリスト

本番環境にデプロイする前に確認すべき項目:

1. **設定**
    - ✓ 環境変数が正しく設定されているか
    - ✓ リソース制限が適切に設定されているか
    - ✓ ロギングが適切なレベルとローテーションで設定されているか

2. **モニタリング**
    - ✓ ヘルスチェックが実装されているか
    - ✓ メトリクス収集が設定されているか
    - ✓ アラートのしきい値が設定されているか

3. **エラー処理**
    - ✓ 包括的なエラー処理が実装されているか
    - ✓ エラーロギングが設定されているか
    - ✓ リカバリー手順が文書化されているか

4. **パフォーマンス**
    - ✓ キャッシュ設定が最適化されているか
    - ✓ リソース制限が調整されているか
    - ✓ 同時実行の制限が設定されているか

5. **セキュリティ**
    - ✓ 機密データが適切に保護されているか
    - ✓ アクセス制御が実装されているか
    - ✓ ネットワークセキュリティが設定されているか

## 次のステップ

- [モニタリングガイド](../api/monitoring.md)でデプロイのモニタリングを行う
- [トラブルシューティング](troubleshooting.md)で一般的な問題を確認する
- サポートについては[コミュニティディスカッション](https://github.com/t3tra-dev/mtaio/discussions)に参加する