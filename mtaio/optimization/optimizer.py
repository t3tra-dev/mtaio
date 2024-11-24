"""
Asynchronous performance optimization implementation.

This module provides components for optimizing async operations:

* Optimizer: Main optimizer class
* Parameter: Parameter definition for optimization
* OptimizationStrategy: Optimization strategy interface
* OptimizationResult: Optimization result container
"""

from typing import (
    Dict,
    List,
    Optional,
    Any,
    Callable,
    Awaitable,
    Union,
    TypeVar,
    Protocol,
    runtime_checkable,
)
from dataclasses import dataclass
import asyncio
import time
import random
from enum import Enum, auto
from ..exceptions import OptimizationError

T = TypeVar("T")


class ParameterType(Enum):
    """Parameter types for optimization."""

    INTEGER = auto()
    FLOAT = auto()
    CATEGORICAL = auto()


@dataclass
class Parameter:
    """
    Parameter definition for optimization.

    :param name: Parameter name
    :type name: str
    :param type: Parameter type
    :type type: ParameterType
    :param min_value: Minimum value (for numeric types)
    :type min_value: Optional[Union[int, float]]
    :param max_value: Maximum value (for numeric types)
    :type max_value: Optional[Union[int, float]]
    :param choices: Possible values (for categorical type)
    :type choices: Optional[List[Any]]
    """

    name: str
    type: ParameterType
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    choices: Optional[List[Any]] = None
    step: Optional[Union[int, float]] = None


@dataclass
class OptimizationResult:
    """
    Container for optimization results.

    :param parameters: Optimized parameters
    :type parameters: Dict[str, Any]
    :param score: Optimization score
    :type score: float
    :param history: Optimization history
    :type history: List[Dict[str, Any]]
    """

    parameters: Dict[str, Any]
    score: float
    history: List[Dict[str, Any]]
    iterations: int
    elapsed_time: float
    improvement: float


@runtime_checkable
class OptimizationStrategy(Protocol):
    """Protocol for optimization strategies."""

    async def optimize(
        self,
        parameters: List[Parameter],
        objective: Callable[[Dict[str, Any]], Awaitable[float]],
        iterations: int,
    ) -> OptimizationResult:
        """
        Optimize parameters.

        :param parameters: Parameters to optimize
        :type parameters: List[Parameter]
        :param objective: Objective function to minimize
        :type objective: Callable[[Dict[str, Any]], Awaitable[float]]
        :param iterations: Number of iterations
        :type iterations: int
        :return: Optimization result
        :rtype: OptimizationResult
        """
        ...


class GridSearchStrategy:
    """Grid search optimization strategy."""

    async def optimize(
        self,
        parameters: List[Parameter],
        objective: Callable[[Dict[str, Any]], Awaitable[float]],
        iterations: int,
    ) -> OptimizationResult:
        """Perform grid search optimization."""
        start_time = time.monotonic()
        best_params: Optional[Dict[str, Any]] = None
        best_score = float("inf")
        history = []

        # Generate grid points
        param_grid = self._generate_grid(parameters, iterations)

        # Evaluate each point
        for params in param_grid:
            score = await objective(params)
            history.append({"parameters": params.copy(), "score": score})

            if score < best_score:
                best_score = score
                best_params = params.copy()

        elapsed_time = time.monotonic() - start_time
        improvement = history[0]["score"] - best_score if history else 0

        return OptimizationResult(
            parameters=best_params or {},
            score=best_score,
            history=history,
            iterations=len(param_grid),
            elapsed_time=elapsed_time,
            improvement=improvement,
        )

    def _generate_grid(
        self, parameters: List[Parameter], iterations: int
    ) -> List[Dict[str, Any]]:
        """Generate grid points for parameters."""
        grid_points = []

        for param in parameters:
            if param.type == ParameterType.CATEGORICAL:
                points = param.choices or []
            else:
                points = self._generate_numeric_points(param, iterations)
            grid_points.append((param.name, points))

        # Generate all combinations
        combinations = []
        self._generate_combinations(grid_points, {}, 0, combinations)
        return combinations

    def _generate_numeric_points(
        self, param: Parameter, iterations: int
    ) -> List[Union[int, float]]:
        """Generate numeric points for a parameter."""
        if param.min_value is None or param.max_value is None:
            return []

        points = []
        step = param.step or ((param.max_value - param.min_value) / (iterations - 1))

        current = param.min_value
        while current <= param.max_value:
            if param.type == ParameterType.INTEGER:
                points.append(int(current))
            else:
                points.append(current)
            current += step

        return points

    def _generate_combinations(
        self,
        grid_points: List[tuple],
        current: Dict[str, Any],
        index: int,
        result: List[Dict[str, Any]],
    ) -> None:
        """Generate all parameter combinations."""
        if index == len(grid_points):
            result.append(current.copy())
            return

        name, points = grid_points[index]
        for point in points:
            current[name] = point
            self._generate_combinations(grid_points, current, index + 1, result)


class RandomSearchStrategy:
    """Random search optimization strategy."""

    async def optimize(
        self,
        parameters: List[Parameter],
        objective: Callable[[Dict[str, Any]], Awaitable[float]],
        iterations: int,
    ) -> OptimizationResult:
        """Perform random search optimization."""
        start_time = time.monotonic()
        best_params: Optional[Dict[str, Any]] = None
        best_score = float("inf")
        history = []

        for _ in range(iterations):
            # Generate random parameters
            params = self._generate_random_params(parameters)
            score = await objective(params)
            history.append({"parameters": params.copy(), "score": score})

            if score < best_score:
                best_score = score
                best_params = params.copy()

        elapsed_time = time.monotonic() - start_time
        improvement = history[0]["score"] - best_score if history else 0

        return OptimizationResult(
            parameters=best_params or {},
            score=best_score,
            history=history,
            iterations=iterations,
            elapsed_time=elapsed_time,
            improvement=improvement,
        )

    def _generate_random_params(self, parameters: List[Parameter]) -> Dict[str, Any]:
        """Generate random parameters."""
        params = {}
        for param in parameters:
            if param.type == ParameterType.CATEGORICAL:
                params[param.name] = random.choice(param.choices or [])
            elif param.type == ParameterType.INTEGER:
                if param.min_value is not None and param.max_value is not None:
                    params[param.name] = random.randint(
                        int(param.min_value), int(param.max_value)
                    )
            else:  # FLOAT
                if param.min_value is not None and param.max_value is not None:
                    params[param.name] = random.uniform(
                        param.min_value, param.max_value
                    )
        return params


class BayesianStrategy:
    """Simple Bayesian optimization strategy."""

    def __init__(self, exploration_rate: float = 0.1):
        """
        Initialize the strategy.

        :param exploration_rate: Rate of exploration vs exploitation
        :type exploration_rate: float
        """
        self.exploration_rate = exploration_rate
        self.observations: List[Dict[str, Any]] = []

    async def optimize(
        self,
        parameters: List[Parameter],
        objective: Callable[[Dict[str, Any]], Awaitable[float]],
        iterations: int,
    ) -> OptimizationResult:
        """Perform Bayesian optimization."""
        start_time = time.monotonic()
        best_params: Optional[Dict[str, Any]] = None
        best_score = float("inf")
        history = []

        # Initial random exploration
        initial_points = max(3, iterations // 4)
        random_strategy = RandomSearchStrategy()

        for _ in range(initial_points):
            params = random_strategy._generate_random_params(parameters)
            score = await objective(params)
            self.observations.append({"parameters": params.copy(), "score": score})
            history.append({"parameters": params.copy(), "score": score})

            if score < best_score:
                best_score = score
                best_params = params.copy()

        # Bayesian optimization
        for _ in range(iterations - initial_points):
            if random.random() < self.exploration_rate:
                # Exploration
                params = random_strategy._generate_random_params(parameters)
            else:
                # Exploitation
                params = self._estimate_next_point(parameters)

            score = await objective(params)
            self.observations.append({"parameters": params.copy(), "score": score})
            history.append({"parameters": params.copy(), "score": score})

            if score < best_score:
                best_score = score
                best_params = params.copy()

        elapsed_time = time.monotonic() - start_time
        improvement = history[0]["score"] - best_score if history else 0

        return OptimizationResult(
            parameters=best_params or {},
            score=best_score,
            history=history,
            iterations=iterations,
            elapsed_time=elapsed_time,
            improvement=improvement,
        )

    def _estimate_next_point(self, parameters: List[Parameter]) -> Dict[str, Any]:
        """Estimate next point based on observations."""
        if not self.observations:
            return {}

        # Sort observations by score
        sorted_obs = sorted(self.observations, key=lambda x: x["score"])

        # Take the best performing parameters and add some noise
        best_params = sorted_obs[0]["parameters"].copy()

        for param in parameters:
            if param.type == ParameterType.CATEGORICAL:
                if random.random() < 0.3:  # 30% chance to try different category
                    best_params[param.name] = random.choice(param.choices or [])
            else:
                if param.min_value is not None and param.max_value is not None:
                    noise = (param.max_value - param.min_value) * 0.1
                    value = best_params[param.name] + random.gauss(0, noise)
                    value = max(param.min_value, min(param.max_value, value))

                    if param.type == ParameterType.INTEGER:
                        value = int(round(value))

                    best_params[param.name] = value

        return best_params


class Optimizer:
    """
    Performance optimizer for async operations.

    Example::

        optimizer = Optimizer()

        # Define parameters to optimize
        parameters = [
            Parameter("batch_size", ParameterType.INTEGER, 1, 100),
            Parameter("workers", ParameterType.INTEGER, 1, 10),
            Parameter("strategy", ParameterType.CATEGORICAL, choices=["fast", "balanced", "thorough"])
        ]

        # Define objective function
        async def objective(params):
            result = await run_benchmark(params)
            return result.execution_time

        # Run optimization
        result = await optimizer.optimize(parameters, objective)
        print(f"Best parameters: {result.parameters}")
    """

    def __init__(self, strategy: Optional[OptimizationStrategy] = None):
        """
        Initialize the optimizer.

        :param strategy: Optimization strategy to use
        :type strategy: Optional[OptimizationStrategy]
        """
        self.strategy = strategy or RandomSearchStrategy()

    async def optimize(
        self,
        parameters: List[Parameter],
        objective: Callable[[Dict[str, Any]], Awaitable[float]],
        iterations: int = 100,
        timeout: Optional[float] = None,
    ) -> OptimizationResult:
        """
        Optimize parameters.

        :param parameters: Parameters to optimize
        :type parameters: List[Parameter]
        :param objective: Objective function to minimize
        :type objective: Callable[[Dict[str, Any]], Awaitable[float]]
        :param iterations: Number of iterations
        :type iterations: int
        :param timeout: Optional timeout in seconds
        :type timeout: Optional[float]
        :return: Optimization result
        :rtype: OptimizationResult
        """
        # Validate parameters
        for param in parameters:
            if param.type in (ParameterType.INTEGER, ParameterType.FLOAT):
                if param.min_value is None or param.max_value is None:
                    raise OptimizationError(
                        f"Parameter {param.name} requires min_value and max_value"
                    )
            elif param.type == ParameterType.CATEGORICAL:
                if not param.choices:
                    raise OptimizationError(f"Parameter {param.name} requires choices")

        # Run optimization with timeout if specified
        if timeout is not None:
            try:
                async with asyncio.timeout(timeout):
                    return await self.strategy.optimize(
                        parameters, objective, iterations
                    )
            except asyncio.TimeoutError:
                raise OptimizationError("Optimization timeout exceeded")
        else:
            return await self.strategy.optimize(parameters, objective, iterations)

    @classmethod
    def create_grid_search(cls) -> "Optimizer":
        """Create optimizer with grid search strategy."""
        return cls(GridSearchStrategy())

    @classmethod
    def create_random_search(cls) -> "Optimizer":
        """Create optimizer with random search strategy."""
        return cls(RandomSearchStrategy())

    @classmethod
    def create_bayesian(cls, exploration_rate: float = 0.1) -> "Optimizer":
        """Create optimizer with Bayesian strategy."""
        return cls(BayesianStrategy(exploration_rate))
