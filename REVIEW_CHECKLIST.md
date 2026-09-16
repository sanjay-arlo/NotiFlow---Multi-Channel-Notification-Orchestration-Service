# Repository review checklist

Before merging changes, verify:

- README commands match repository paths.
- `.env` and credentials are never committed.
- Generated Python bytecode is ignored and removed from tracking.
- Tests pass in CI.
- External-provider claims are clearly distinguished from local simulations.
