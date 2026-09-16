# Contributing

## Before opening a pull request

- Keep README commands aligned with actual repository paths.
- Do not commit `.env` files, credentials or provider tokens.
- Do not commit generated Python bytecode or local caches.
- Add or update tests for behaviour changes.
- Keep documentation explicit about prototype, simulation and production boundaries.

## Local checks

```bash
pytest -q
python -m compileall -q app scripts
```
