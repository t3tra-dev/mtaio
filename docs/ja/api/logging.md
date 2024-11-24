# ロギングAPIリファレンス

`mtaio.logging`モジュールは、様々なハンドラーとフォーマッターをサポートする非同期ロギング機能を提供します。

## AsyncLogger

非同期ロギング機能を提供するメインのロギングクラスです。

### 基本的な使い方

```python
from mtaio.logging import AsyncLogger, AsyncFileHandler

# ロガーの作成
logger = AsyncLogger("app")

# ハンドラーの追加
handler = AsyncFileHandler("app.log")
await logger.add_handler(handler)

# メッセージのログ記録
await logger.info("アプリケーションが起動しました")
await logger.error("エラーが発生しました", extra={"詳細": "エラー情報"})
```

### クラスリファレンス

```python
class AsyncLogger:
    def __init__(
        self,
        name: str,
        level: int = logging.NOTSET,
        handlers: Optional[List[AsyncLogHandler]] = None
    ):
        """
        非同期ロガーを初期化します。

        Args:
            name: ロガー名
            level: 最小ログレベル
            handlers: オプションのハンドラーリスト
        """

    async def debug(
        self,
        message: str,
        *,
        exc_info: Optional[tuple] = None,
        stack_info: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ) -> None:
        """デバッグメッセージを記録します。"""

    async def info(self, message: str, **kwargs) -> None:
        """情報メッセージを記録します。"""

    async def warning(self, message: str, **kwargs) -> None:
        """警告メッセージを記録します。"""

    async def error(self, message: str, **kwargs) -> None:
        """エラーメッセージを記録します。"""

    async def critical(self, message: str, **kwargs) -> None:
        """重大メッセージを記録します。"""
```

## ハンドラー

### AsyncFileHandler

非同期I/Oを使用したファイルベースのログハンドラー。

```python
from mtaio.logging import AsyncFileHandler

handler = AsyncFileHandler(
    filename="app.log",
    mode="a",
    encoding="utf-8",
    max_bytes=10_000_000,  # 10MB
    backup_count=5
)

# フォーマッターの追加
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
```

### AsyncRotatingFileHandler

ローテーション機能を持つファイルハンドラー。

```python
from mtaio.logging import AsyncRotatingFileHandler

handler = AsyncRotatingFileHandler(
    filename="app.log",
    max_bytes=1_000_000,  # 1MB
    backup_count=3,
    encoding="utf-8"
)
```

### AsyncJsonFileHandler

JSON形式でログを出力するファイルハンドラー。

```python
from mtaio.logging import AsyncJsonFileHandler

handler = AsyncJsonFileHandler(
    filename="app.log.json",
    encoder_cls=json.JSONEncoder
)

# ログエントリはJSON形式で書き込まれます
await logger.info(
    "ユーザーアクション",
    extra={
        "user_id": "123",
        "action": "ログイン"
    }
)
```

## ログレコード

### LogRecord

ログレコードデータのコンテナ。

```python
@dataclass
class LogRecord:
    level: int
    message: str
    timestamp: float
    logger_name: str
    extra: Dict[str, Any]
    exc_info: Optional[tuple] = None
    stack_info: Optional[str] = None

    @property
    def levelname(self) -> str:
        """レベル名を取得します。"""
        return logging.getLevelName(self.level)
```

## 高度な機能

### トランザクションログ

関連するログメッセージをトランザクションでグループ化:

```python
async with logger.transaction(exc_level=logging.ERROR):
    # このブロック内のすべてのログがグループ化されます
    await logger.info("トランザクションを開始")
    await process_data()
    await logger.info("トランザクション完了")
```

### バッチログ記録

複数のメッセージを効率的に記録:

```python
messages = [
    "処理を開始",
    "ステップ1完了",
    "ステップ2完了",
    "処理終了"
]

await logger.batch(logging.INFO, messages)
```

### エラーログ記録

コンテキスト付きの包括的なエラーログ記録:

```python
try:
    await operation()
except Exception as e:
    await logger.error(
        "操作に失敗しました",
        exc_info=True,
        extra={
            "operation_id": "123",
            "詳細": str(e)
        }
    )
```

## ベストプラクティス

### ハンドラーの設定

```python
async def setup_logging():
    # ロガーの作成
    logger = AsyncLogger("app", level=logging.INFO)
    
    # すべてのログ用のファイルハンドラー
    file_handler = AsyncRotatingFileHandler(
        "app.log",
        max_bytes=10_000_000,
        backup_count=5
    )
    file_handler.setLevel(logging.DEBUG)
    
    # 重要なログ用のJSONハンドラー
    json_handler = AsyncJsonFileHandler("important.log.json")
    json_handler.setLevel(logging.ERROR)
    
    # ハンドラーの追加
    await logger.add_handler(file_handler)
    await logger.add_handler(json_handler)
    
    return logger
```

### コンテキスト付きログ記録

```python
class RequestLogger:
    def __init__(self, logger: AsyncLogger):
        self.logger = logger
    
    async def log_request(
        self,
        request_id: str,
        message: str,
        **kwargs
    ) -> None:
        await self.logger.info(
            message,
            extra={
                "request_id": request_id,
                **kwargs
            }
        )
```

### 構造化ログ記録

```python
class StructuredLogger:
    def __init__(self, logger: AsyncLogger):
        self.logger = logger
    
    async def log_event(
        self,
        event_name: str,
        **data: Any
    ) -> None:
        await self.logger.info(
            f"イベント: {event_name}",
            extra={
                "event_type": event_name,
                "event_data": data,
                "timestamp": time.time()
            }
        )
```

## パフォーマンスの考慮事項

1. **バッチ処理**
   ```python
   # 効率的なバッチログ記録
   async def log_operations(operations: List[str]):
       await logger.batch(
           logging.INFO,
           [f"操作: {op}" for op in operations]
       )
   ```

2. **ログレベルのフィルタリング**
   ```python
   # 適切なログレベルの設定
   logger.setLevel(logging.INFO)  # 本番環境
   handler.setLevel(logging.ERROR)  # 重要なエラーのみ
   ```

3. **非同期ハンドラーの管理**
   ```python
   # ハンドラーの適切なクリーンアップ
   async def cleanup_logging():
       for handler in logger.handlers:
           await handler.stop()
           await handler.close()
   ```

## エラー処理

```python
from mtaio.exceptions import LoggingError

try:
    await logger.info("メッセージ")
except LoggingError as e:
    print(f"ログ記録に失敗しました: {e}")
    # 標準ロギングにフォールバック
    import logging
    logging.error("フォールバックログメッセージ")
```

## 統合例

### Webアプリケーションのログ記録

```python
class WebAppLogger:
    def __init__(self):
        self.logger = AsyncLogger("webapp")
        self.setup_handlers()
    
    async def log_request(self, request, response):
        await self.logger.info(
            f"リクエスト: {request.method} {request.path}",
            extra={
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration": response.duration
            }
        )
```

### タスク監視

```python
class TaskLogger:
    def __init__(self, logger: AsyncLogger):
        self.logger = logger
    
    @contextmanager
    async def track_task(self, task_id: str):
        start_time = time.time()
        try:
            await self.logger.info(f"タスク {task_id} 開始")
            yield
            duration = time.time() - start_time
            await self.logger.info(
                f"タスク {task_id} 完了",
                extra={"duration": duration}
            )
        except Exception as e:
            await self.logger.error(
                f"タスク {task_id} 失敗",
                exc_info=True,
                extra={"duration": time.time() - start_time}
            )
```

## 関連項目

- 基本機能については[コアAPIリファレンス](core.md)を参照
- エラー処理については[例外APIリファレンス](exceptions.md)を参照
- サンプルコードは[サンプルリポジトリ](https://github.com/t3tra-dev/mtaio/tree/main/examples/logging.py)を参照
