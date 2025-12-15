# niri

Small Python client library and CLI helpers for niri IPC.

## Why

- Provide a thin Unix-socket JSON client (`NiriRequests`)
- Provide an event stream helper (`event_stream`, `EventDispatcher`)
- Provide CLI fallbacks for actions affected by IPC regressions

## Develop

- Create env: `pixi install`
- Run a quick check: `pixi run python -m compileall -q src`

