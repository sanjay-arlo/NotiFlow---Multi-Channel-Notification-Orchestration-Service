# Verification

For local validation:

```bash
pytest -q
python -m compileall -q app scripts
```

For container validation, start the Docker Compose services and verify the API health endpoint before testing external providers.