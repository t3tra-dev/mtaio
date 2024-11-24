# API Reference

mtaio provides a comprehensive set of APIs for building asynchronous applications. This reference documents all the modules and their components in detail.

## Core Components

- [Core](core.md): Fundamental components for asynchronous operations, including task execution and queues
- [Cache](cache.md): In-memory and distributed caching mechanisms
- [Events](events.md): Event emitting and handling system
- [Data](data.md): Data processing and transformation tools
- [Resources](resources.md): System resource management utilities

## Protocol Support

- [Protocols](protocols.md): Network protocol implementations (ASGI, MQTT, mail)

## Development Tools

- [Monitoring](monitoring.md): System monitoring and performance profiling
- [Logging](logging.md): Asynchronous logging functionality
- [Optimization](optimization.md): Performance optimization utilities
- [Exceptions](exceptions.md): Error handling and exception hierarchy

## Type System

- [Typing](typing.md): Type definitions and protocols
- [Decorators](decorators.md): Utility decorators for enhancing async functions

## Module Organization

The API is organized into logical modules, each focusing on a specific aspect of async programming:

```
mtaio/
├── core/        # Core async functionality
├── cache/       # Caching implementations
├── events/      # Event handling system
├── data/        # Data processing tools
├── protocols/   # Protocol implementations
├── resources/   # Resource management
├── monitoring/  # System monitoring
├── logging/     # Logging utilities
├── typing/      # Type definitions
└── decorators/  # Utility decorators
```

## Using the API

Each module's documentation includes:

- Detailed class and function references
- Usage examples
- Best practices
- Common patterns
- Error handling
- Performance considerations

Select a module from the navigation menu to view its detailed documentation.

## API Stability

mtaio follows semantic versioning (SemVer):

- Major version changes (x.0.0) may include breaking API changes
- Minor version changes (0.x.0) add functionality in a backward-compatible manner
- Patch version changes (0.0.x) include backward-compatible bug fixes

Any breaking changes will be clearly documented in the release notes.
