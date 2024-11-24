"""
Test optimizer implementation.
"""

import pytest
from mtaio.optimization import Optimizer, Parameter, ParameterType, GridSearchStrategy
from mtaio.exceptions import OptimizationError


@pytest.mark.asyncio
async def test_optimizer_basic():
    """Test basic optimization."""
    optimizer = Optimizer(strategy=GridSearchStrategy())

    parameters = [
        Parameter("x", ParameterType.FLOAT, 0, 1),
        Parameter("y", ParameterType.FLOAT, 0, 1),
    ]

    async def objective(params):
        x = params["x"]
        y = params["y"]
        return (x - 0.5) ** 2 + (y - 0.5) ** 2

    result = await optimizer.optimize(parameters, objective, iterations=5)

    assert 0 <= result.parameters["x"] <= 1
    assert 0 <= result.parameters["y"] <= 1


@pytest.mark.asyncio
async def test_optimizer_invalid_params():
    """Test optimizer with invalid parameters."""
    optimizer = Optimizer()

    parameters = [Parameter("x", ParameterType.FLOAT)]  # Missing min/max

    async def objective(params):
        return 0

    with pytest.raises(OptimizationError):
        await optimizer.optimize(parameters, objective)
