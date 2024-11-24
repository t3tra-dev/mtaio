"""
Data processing examples for mtaio library.

This example demonstrates:
- Pipeline processing
- Stream operations
- Observable pattern
"""

import asyncio
from typing import Dict, Any
from mtaio.data import (
    Pipeline,
    Stage,
    Stream,
    Observable,
    Change,
)


class ValidationStage(Stage[Dict[str, Any], Dict[str, Any]]):
    """
    Pipeline stage that validates user data.
    """

    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate user data.

        :param data: User data to validate
        :return: Validated data
        :raises ValueError: If data is invalid
        """
        if "name" not in data:
            raise ValueError("Missing name field")
        if len(data["name"]) < 2:
            raise ValueError("Name too short")
        return data


class EnrichmentStage(Stage[Dict[str, Any], Dict[str, Any]]):
    """
    Pipeline stage that enriches user data.
    """

    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich user data with additional information.

        :param data: User data to enrich
        :return: Enriched data
        """
        data["status"] = "active"
        data["timestamp"] = "2024-01-01"
        return data


async def pipeline_example() -> None:
    """
    Demonstrates data processing pipeline usage.
    """
    # Create and configure pipeline
    pipeline = Pipeline[Dict[str, Any], Dict[str, Any]]()
    pipeline.add_stage(ValidationStage())
    pipeline.add_stage(EnrichmentStage())

    # Process data through pipeline
    async with pipeline:
        input_data = {"name": "John Doe", "age": 30}
        result = await pipeline.process(input_data)
        print(f"Processed data: {result}")

        # Process multiple items
        items = [{"name": "Jane Doe", "age": 25}, {"name": "Bob Smith", "age": 35}]
        results = await pipeline.process_many(items)
        print(f"Batch results: {results}")


async def stream_example() -> None:
    """
    Demonstrates stream processing operations.
    """
    # Create stream from data
    numbers = range(1, 6)
    stream = Stream.from_iterable(numbers)

    # Apply transformations
    result = await (
        stream.map(lambda x: x * 2)  # Double numbers
        .filter(lambda x: x > 5)  # Keep numbers > 5
        .reduce(lambda acc, x: acc + x)  # Sum remaining numbers
    )
    print(f"Stream result: {result}")

    # Demonstrate batching
    stream = Stream.from_iterable(range(1, 8))
    async for batch in stream.batch(size=3):
        print(f"Batch: {batch}")


class UserData(Observable[Dict[str, Any]]):
    """
    Observable user data store.
    """

    def __init__(self) -> None:
        """Initialize user data store."""
        super().__init__()
        self._data: Dict[str, Dict[str, Any]] = {}

    async def update_user(self, user_id: str, data: Dict[str, Any]) -> None:
        """
        Update user data and notify observers.

        :param user_id: User identifier
        :param data: Updated user data
        """
        old_data = self._data.get(user_id)
        self._data[user_id] = data
        await self.notify(
            Change(
                type="update", path=f"users.{user_id}", value=data, old_value=old_data
            )
        )


async def observable_example() -> None:
    """
    Demonstrates observable pattern usage.
    """
    users = UserData()

    # Register observer
    @users.on_change
    async def handle_user_change(change: Change[Dict[str, Any]]) -> None:
        """Handle user data changes."""
        print(f"User change: {change.path}")
        print(f"New value: {change.value}")
        print(f"Old value: {change.old_value}")

    # Update user data
    await users.update_user("user1", {"name": "John", "age": 30})
    await users.update_user("user1", {"name": "John", "age": 31})


async def main() -> None:
    """
    Run all data processing examples.
    """
    print("=== Pipeline Example ===")
    await pipeline_example()

    print("\n=== Stream Example ===")
    await stream_example()

    print("\n=== Observable Example ===")
    await observable_example()


if __name__ == "__main__":
    asyncio.run(main())
