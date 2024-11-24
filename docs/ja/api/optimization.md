# 最適化APIリファレンス

`mtaio.optimization`モジュールは、非同期操作のパラメータとパフォーマンスを最適化するためのツールを提供します。

## Optimizer

### 基本的な使い方

```python
from mtaio.optimization import Optimizer, Parameter, ParameterType

# 最適化するパラメータの定義
parameters = [
    Parameter(
        name="batch_size",
        type=ParameterType.INTEGER,
        min_value=1,
        max_value=100
    ),
    Parameter(
        name="workers",
        type=ParameterType.INTEGER,
        min_value=1,
        max_value=10
    ),
    Parameter(
        name="strategy",
        type=ParameterType.CATEGORICAL,
        choices=["fast", "balanced", "thorough"]
    )
]

# 目的関数の定義
async def objective(params: dict) -> float:
    # パラメータでベンチマークを実行
    result = await run_benchmark(
        batch_size=params["batch_size"],
        workers=params["workers"],
        strategy=params["strategy"]
    )
    return result.execution_time

# パラメータの最適化
optimizer = Optimizer()
result = await optimizer.optimize(parameters, objective)
print(f"最適なパラメータ: {result.parameters}")
```

### クラスリファレンス

```python
class Optimizer:
    def __init__(
        self,
        strategy: Optional[OptimizationStrategy] = None
    ):
        """
        オプティマイザーを初期化します。

        Args:
            strategy: 使用する最適化戦略（デフォルト: RandomSearchStrategy）
        """

    async def optimize(
        self,
        parameters: List[Parameter],
        objective: Callable[[Dict[str, Any]], Awaitable[float]],
        iterations: int = 100,
        timeout: Optional[float] = None,
    ) -> OptimizationResult:
        """
        パラメータを最適化します。

        Args:
            parameters: 最適化するパラメータ
            objective: 最小化する目的関数
            iterations: 反復回数
            timeout: オプションのタイムアウト（秒）

        Returns:
            最適化結果
        """
```

## パラメータ

### パラメータ定義

```python
@dataclass
class Parameter:
    name: str
    type: ParameterType
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    choices: Optional[List[Any]] = None
    step: Optional[Union[int, float]] = None

class ParameterType(Enum):
    INTEGER = auto()      # 整数値
    FLOAT = auto()        # 浮動小数点値
    CATEGORICAL = auto()  # カテゴリ値
```

### パラメータの例

```python
# 数値パラメータ
batch_size = Parameter(
    name="batch_size",
    type=ParameterType.INTEGER,
    min_value=1,
    max_value=1000,
    step=10  # オプションのステップサイズ
)

learning_rate = Parameter(
    name="learning_rate",
    type=ParameterType.FLOAT,
    min_value=0.0001,
    max_value=0.1
)

# カテゴリパラメータ
algorithm = Parameter(
    name="algorithm",
    type=ParameterType.CATEGORICAL,
    choices=["sgd", "adam", "rmsprop"]
)
```

## 最適化戦略

### 利用可能な戦略

#### GridSearchStrategy

パラメータの組み合わせを体系的に探索します。

```python
from mtaio.optimization import GridSearchStrategy

optimizer = Optimizer(strategy=GridSearchStrategy())
result = await optimizer.optimize(parameters, objective)
```

#### RandomSearchStrategy

パラメータの組み合わせをランダムにサンプリングします。

```python
from mtaio.optimization import RandomSearchStrategy

optimizer = Optimizer(strategy=RandomSearchStrategy())
result = await optimizer.optimize(parameters, objective)
```

#### BayesianStrategy

ベイズ最適化を使用してパラメータを探索します。

```python
from mtaio.optimization import BayesianStrategy

optimizer = Optimizer(
    strategy=BayesianStrategy(
        exploration_rate=0.1
    )
)
result = await optimizer.optimize(parameters, objective)
```

### カスタム戦略

カスタム最適化戦略の実装:

```python
class CustomStrategy(OptimizationStrategy):
    async def optimize(
        self,
        parameters: List[Parameter],
        objective: Callable[[Dict[str, Any]], Awaitable[float]],
        iterations: int,
    ) -> OptimizationResult:
        best_params = None
        best_score = float("inf")
        history = []

        for _ in range(iterations):
            # パラメータの生成
            params = self.generate_params(parameters)
            
            # 目的関数の評価
            score = await objective(params)
            history.append({"parameters": params, "score": score})
            
            # 最良結果の更新
            if score < best_score:
                best_score = score
                best_params = params

        return OptimizationResult(
            parameters=best_params,
            score=best_score,
            history=history,
            iterations=iterations
        )
```

## 結果

### OptimizationResult

最適化結果のコンテナ:

```python
@dataclass
class OptimizationResult:
    parameters: Dict[str, Any]  # 見つかった最適パラメータ
    score: float                # 最良の目的関数スコア
    history: List[Dict[str, Any]]  # 最適化の履歴
    iterations: int             # 実行された総反復回数
    elapsed_time: float        # 要した総時間
    improvement: float         # 初期スコアからの改善度
```

## 高度な機能

### パラメータ空間の制約

```python
from mtaio.optimization import Optimizer, Parameter

# 依存関係のあるパラメータの定義
async def objective(params: dict) -> float:
    if params["use_feature"] and params["feature_count"] > 0:
        # 指定された数の機能を使用
        pass
    return score

parameters = [
    Parameter(
        name="use_feature",
        type=ParameterType.CATEGORICAL,
        choices=[True, False]
    ),
    Parameter(
        name="feature_count",
        type=ParameterType.INTEGER,
        min_value=0,
        max_value=10
    )
]
```

### 多目的最適化

```python
async def multi_objective(params: dict) -> float:
    # 複数のメトリクスを計算
    latency = await measure_latency(params)
    memory = await measure_memory(params)
    
    # 重み付けしてメトリクスを結合
    return 0.7 * latency + 0.3 * memory
```

## 統合例

### パフォーマンス最適化

```python
from mtaio.optimization import Optimizer
from mtaio.core import TaskExecutor

class PerformanceOptimizer:
    def __init__(self):
        self.optimizer = Optimizer()
        self.executor = TaskExecutor()
    
    async def optimize_performance(self):
        parameters = [
            Parameter("concurrency", ParameterType.INTEGER, 1, 20),
            Parameter("batch_size", ParameterType.INTEGER, 1, 1000)
        ]
        
        async def objective(params):
            async with self.executor:
                start_time = time.time()
                await self.executor.gather(
                    *tasks,
                    limit=params["concurrency"]
                )
                return time.time() - start_time
        
        return await self.optimizer.optimize(parameters, objective)
```

### リソース最適化

```python
from mtaio.optimization import Optimizer
from mtaio.monitoring import ResourceMonitor

class ResourceOptimizer:
    def __init__(self):
        self.optimizer = Optimizer()
        self.monitor = ResourceMonitor()
    
    async def optimize_resources(self):
        parameters = [
            Parameter("memory_limit", ParameterType.INTEGER, 100, 1000),
            Parameter("cpu_limit", ParameterType.INTEGER, 1, 8)
        ]
        
        async def objective(params):
            # リソースの設定
            await self.configure_limits(params)
            
            # ワークロードの実行
            await self.run_workload()
            
            # リソースメトリクスの取得
            stats = await self.monitor.get_current_stats()
            return stats.memory.used / stats.memory.total
        
        return await self.optimizer.optimize(parameters, objective)
```

## ベストプラクティス

### パラメータの設定

```python
# 妥当なパラメータ範囲の定義
parameters = [
    Parameter(
        name="timeout",
        type=ParameterType.FLOAT,
        min_value=0.1,
        max_value=10.0,
        step=0.1  # 細かすぎる粒度を避ける
    )
]

# 適切なパラメータ型の使用
categorical_param = Parameter(
    name="strategy",
    type=ParameterType.CATEGORICAL,
    choices=["fast", "balanced"]  # 限定された選択肢
)
```

### 目的関数の設計

```python
async def robust_objective(params: dict) -> float:
    try:
        # 複数回の評価実行
        scores = []
        for _ in range(3):
            score = await evaluate(params)
            scores.append(score)
        
        # 平均スコアを返す
        return statistics.mean(scores)
    except Exception as e:
        # エラーを適切に処理
        logger.error(f"評価に失敗しました: {e}")
        return float("inf")
```

## 関連項目

- 基本機能については[コアAPIリファレンス](core.md)を参照
- パフォーマンスモニタリングについては[モニタリングAPIリファレンス](monitoring.md)を参照
- サンプルコードは[サンプルリポジトリ](https://github.com/t3tra-dev/mtaio/tree/main/examples/optimization.py)を参照
