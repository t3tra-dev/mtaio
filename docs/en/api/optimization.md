# Optimization API Reference

The `mtaio.optimization` module provides tools for optimizing parameters and performance of async operations.

## Optimizer

### Basic Usage

```python
from mtaio.optimization import Optimizer, Parameter, ParameterType

# Define parameters to optimize
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

# Define objective function
async def objective(params: dict) -> float:
    # Run benchmark with parameters
    result = await run_benchmark(
        batch_size=params["batch_size"],
        workers=params["workers"],
        strategy=params["strategy"]
    )
    return result.execution_time

# Optimize parameters
optimizer = Optimizer()
result = await optimizer.optimize(parameters, objective)
print(f"Best parameters: {result.parameters}")
```

### Class Reference

```python
class Optimizer:
    def __init__(
        self,
        strategy: Optional[OptimizationStrategy] = None
    ):
        """
        Initialize optimizer.

        Args:
            strategy: Optimization strategy to use (default: RandomSearchStrategy)
        """

    async def optimize(
        self,
        parameters: List[Parameter],
        objective: Callable[[Dict[str, Any]], Awaitable[float]],
        iterations: int = 100,
        timeout: Optional[float] = None,
    ) -> OptimizationResult:
        """
        Optimize parameters.

        Args:
            parameters: Parameters to optimize
            objective: Objective function to minimize
            iterations: Number of iterations
            timeout: Optional timeout in seconds

        Returns:
            Optimization result
        """
```

## Parameters

### Parameter Definition

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
    INTEGER = auto()      # Integer values
    FLOAT = auto()        # Floating point values
    CATEGORICAL = auto()  # Categorical values
```

### Parameter Examples

```python
# Numeric parameters
batch_size = Parameter(
    name="batch_size",
    type=ParameterType.INTEGER,
    min_value=1,
    max_value=1000,
    step=10  # Optional step size
)

learning_rate = Parameter(
    name="learning_rate",
    type=ParameterType.FLOAT,
    min_value=0.0001,
    max_value=0.1
)

# Categorical parameters
algorithm = Parameter(
    name="algorithm",
    type=ParameterType.CATEGORICAL,
    choices=["sgd", "adam", "rmsprop"]
)
```

## Optimization Strategies

### Available Strategies

#### GridSearchStrategy

Systematically explores parameter combinations.

```python
from mtaio.optimization import GridSearchStrategy

optimizer = Optimizer(strategy=GridSearchStrategy())
result = await optimizer.optimize(parameters, objective)
```

#### RandomSearchStrategy

Randomly samples parameter combinations.

```python
from mtaio.optimization import RandomSearchStrategy

optimizer = Optimizer(strategy=RandomSearchStrategy())
result = await optimizer.optimize(parameters, objective)
```

#### BayesianStrategy

Uses Bayesian optimization for parameter search.

```python
from mtaio.optimization import BayesianStrategy

optimizer = Optimizer(
    strategy=BayesianStrategy(
        exploration_rate=0.1
    )
)
result = await optimizer.optimize(parameters, objective)
```

### Custom Strategy

Implement custom optimization strategy:

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
            # Generate parameters
            params = self.generate_params(parameters)
            
            # Evaluate objective
            score = await objective(params)
            history.append({"parameters": params, "score": score})
            
            # Update best result
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

## Results

### OptimizationResult

Container for optimization results:

```python
@dataclass
class OptimizationResult:
    parameters: Dict[str, Any]  # Best parameters found
    score: float                # Best objective score
    history: List[Dict[str, Any]]  # Optimization history
    iterations: int             # Total iterations performed
    elapsed_time: float        # Total time taken
    improvement: float         # Improvement from initial score
```

## Advanced Features

### Parameter Space Constraints

```python
from mtaio.optimization import Optimizer, Parameter

# Define dependent parameters
async def objective(params: dict) -> float:
    if params["use_feature"] and params["feature_count"] > 0:
        # Use feature with specified count
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

### Multi-Objective Optimization

```python
async def multi_objective(params: dict) -> float:
    # Calculate multiple metrics
    latency = await measure_latency(params)
    memory = await measure_memory(params)
    
    # Combine metrics with weights
    return 0.7 * latency + 0.3 * memory
```

## Integration Examples

### Performance Optimization

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

### Resource Optimization

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
            # Configure resources
            await self.configure_limits(params)
            
            # Run workload
            await self.run_workload()
            
            # Get resource metrics
            stats = await self.monitor.get_current_stats()
            return stats.memory.used / stats.memory.total
        
        return await self.optimizer.optimize(parameters, objective)
```

## Best Practices

### Parameter Configuration

```python
# Define reasonable parameter ranges
parameters = [
    Parameter(
        name="timeout",
        type=ParameterType.FLOAT,
        min_value=0.1,
        max_value=10.0,
        step=0.1  # Avoid too fine granularity
    )
]

# Use appropriate parameter types
categorical_param = Parameter(
    name="strategy",
    type=ParameterType.CATEGORICAL,
    choices=["fast", "balanced"]  # Limited choices
)
```

### Objective Function Design

```python
async def robust_objective(params: dict) -> float:
    try:
        # Multiple evaluation runs
        scores = []
        for _ in range(3):
            score = await evaluate(params)
            scores.append(score)
        
        # Return average score
        return statistics.mean(scores)
    except Exception as e:
        # Handle failures gracefully
        logger.error(f"Evaluation failed: {e}")
        return float("inf")
```

## See Also

- [Core API Reference](core.md) for base functionality
- [Monitoring API Reference](monitoring.md) for performance monitoring
- [Examples Repository](https://github.com/t3tra-dev/mtaio/tree/main/examples/optimization.py)
