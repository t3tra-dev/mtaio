"""
Optimization examples for mtaio library.

This example demonstrates:
- Parameter optimization
- Common optimization strategies
- Performance tuning
"""

import asyncio
from typing import Dict, Any
from mtaio.optimization import (
    Optimizer,
    Parameter,
    ParameterType,
)


async def simple_optimization_example() -> None:
    """
    Demonstrates basic parameter optimization.
    """
    # Define parameters to optimize
    parameters = [
        Parameter(
            name="batch_size", type=ParameterType.INTEGER, min_value=1, max_value=100
        ),
        Parameter(
            name="learning_rate",
            type=ParameterType.FLOAT,
            min_value=0.0001,
            max_value=0.1,
        ),
        Parameter(
            name="optimizer",
            type=ParameterType.CATEGORICAL,
            choices=["sgd", "adam", "rmsprop"],
        ),
    ]

    # Define objective function to minimize
    async def objective(params: Dict[str, Any]) -> float:
        """
        Simulate model training and return loss.

        :param params: Parameters to evaluate
        :return: Loss value (lower is better)
        """
        # Simulate training with given parameters
        batch_size = params["batch_size"]
        learning_rate = params["learning_rate"]
        optimizer = params["optimizer"]

        # Simulate some computation
        await asyncio.sleep(0.1)

        # Return simulated loss (lower is better)
        loss = (
            (batch_size - 50) ** 2 / 2500  # Optimal batch size around 50
            + (learning_rate - 0.01) ** 2 * 100  # Optimal learning rate around 0.01  # noqa
            + (0.1 if optimizer == "adam" else 0.3)  # Prefer adam optimizer  # noqa
        )
        return loss

    # Create and run optimizer
    optimizer = Optimizer()
    result = await optimizer.optimize(
        parameters=parameters, objective=objective, iterations=10
    )

    # Display results
    print("Optimization Results:")
    print(f"Best parameters: {result.parameters}")
    print(f"Best score: {result.score:.4f}")
    print(f"Total iterations: {result.iterations}")
    print(f"Improvement: {result.improvement:.4f}")


async def performance_tuning_example() -> None:
    """
    Demonstrates optimization for performance tuning.
    """
    # Define performance-related parameters
    parameters = [
        Parameter(name="workers", type=ParameterType.INTEGER, min_value=1, max_value=8),
        Parameter(
            name="queue_size", type=ParameterType.INTEGER, min_value=10, max_value=1000
        ),
        Parameter(
            name="chunk_size", type=ParameterType.INTEGER, min_value=1, max_value=100
        ),
    ]

    # Define performance objective
    async def performance_objective(params: Dict[str, Any]) -> float:
        """
        Simulate system performance and return metric.

        :param params: System parameters to evaluate
        :return: Performance metric (lower is better)
        """
        workers = params["workers"]
        queue_size = params["queue_size"]
        chunk_size = params["chunk_size"]

        # Simulate workload processing
        await asyncio.sleep(0.1)

        # Return simulated performance metric
        # Combine multiple factors (lower is better)
        metric = (
            1.0 / workers  # More workers generally better
            + queue_size / 10000  # Memory usage penalty  # noqa
            + 1.0 / chunk_size  # Larger chunks generally better  # noqa
        )
        return metric

    # Run optimization
    optimizer = Optimizer()
    result = await optimizer.optimize(
        parameters=parameters, objective=performance_objective, iterations=10
    )

    print("Performance Tuning Results:")
    print(f"Best configuration: {result.parameters}")
    print(f"Performance score: {result.score:.4f}")


async def main() -> None:
    """
    Run all optimization examples.
    """
    print("=== Simple Optimization Example ===")
    await simple_optimization_example()

    print("\n=== Performance Tuning Example ===")
    await performance_tuning_example()


if __name__ == "__main__":
    asyncio.run(main())
