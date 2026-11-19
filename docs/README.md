# Project documentation

This folder documents the current AI Voice Interview Agent implementation.
Use the source files as the final authority when behavior changes.

## Guides

- [Architecture and data flow](architecture.md) — runtime components, interview lifecycle, audio path, and data handling.
- [Module catalog](modules.md) — responsibilities of the backend, frontend, prompts, and test modules.
- [HTTP and WebSocket API](api.md) — HTTP routes and the browser interview protocol.
- [Configuration and local development](configuration.md) — environment variables and Windows setup.
- [Testing and verification](testing.md) — automated test groups and live/manual checks.

## Start here

1. Follow [configuration and local development](configuration.md) to prepare Python, Node.js, and `.env`.
2. Read [architecture and data flow](architecture.md) before changing interview, media, or provider behavior.
3. Use the [module catalog](modules.md) to locate the implementation.
4. Check [testing and verification](testing.md) before submitting changes.

The repository root [README](../README.md) remains the quick-start guide.
