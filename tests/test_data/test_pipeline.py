"""
Test pipeline implementation.
"""

import pytest
from mtaio.data import Pipeline, FilterStage, MapStage
from mtaio.exceptions import PipelineError


@pytest.mark.asyncio
async def test_pipeline_basic():
    """Test basic pipeline operations."""
    pipeline = Pipeline()

    # Add stages
    pipeline.add_stage(MapStage(lambda x: x * 2))
    pipeline.add_stage(FilterStage(lambda x: x > 5))

    async with pipeline:
        result = await pipeline.process(3)
        assert result == 6


@pytest.mark.asyncio
async def test_pipeline_error():
    """Test pipeline error handling."""
    pipeline = Pipeline()

    def failing_map(x):
        raise ValueError("Test error")

    pipeline.add_stage(MapStage(failing_map))

    with pytest.raises(PipelineError):
        async with pipeline:
            await pipeline.process(1)
