# Installation Guide

This guide covers how to install mtaio in your Python environment.

## Requirements

- Python 3.11 or later
- No additional dependencies required

## Installation Methods

### Using pip

The simplest way to install mtaio is using pip:

```bash
pip install mtaio
```

### Using Poetry

If you're using Poetry for your project:

```bash
poetry add mtaio
```

### Using pipenv

For Pipenv users:

```bash
pipenv install mtaio
```

## Verifying Installation

You can verify your installation by running Python and importing mtaio:

```python
import mtaio
print(mtaio.__version__)  # Should display the current version
```

## Version Check

mtaio requires Python 3.11 or later. You can check your Python version using:

```bash
python --version
```

If you're using an older version of Python, you'll need to upgrade before installing mtaio.

## Features

mtaio comes with all modules included by default:

- Core functionality (`mtaio.core`)
- Caching system (`mtaio.cache`)
- Event handling (`mtaio.events`)
- Data processing (`mtaio.data`)
- Protocol implementations (`mtaio.protocols`)
- Resource management (`mtaio.resources`)
- Monitoring tools (`mtaio.monitoring`)
- Logging utilities (`mtaio.logging`)
- Type definitions (`mtaio.typing`)
- Decorator utilities (`mtaio.decorators`)
- Exception handling (`mtaio.exceptions`)

No additional packages need to be installed as all functionality is included in the base package.

## Development Installation

For development purposes, you can install mtaio directly from the source:

```bash
git clone https://github.com/t3tra-dev/mtaio.git
cd mtaio
pip install -e .
```

## Uninstallation

If you need to uninstall mtaio:

```bash
pip uninstall mtaio
```

## Next Steps

After installation, you can:

1. Read the [Getting Started Guide](getting-started.md) for an introduction to mtaio
2. Check out [Basic Usage](basic-usage.md) for common usage patterns
3. Explore the [API Reference](../api/index.md) for detailed documentation

## Troubleshooting

If you encounter any installation issues:

1. Ensure you're using Python 3.11 or later
2. Check that pip is up to date: `pip install --upgrade pip`
3. If installing from source, ensure you have Git installed

If problems persist, please check our [Troubleshooting Guide](troubleshooting.md) or [open an issue](https://github.com/t3tra-dev/mtaio/issues) on GitHub.
