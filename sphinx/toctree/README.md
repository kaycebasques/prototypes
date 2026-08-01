# toctree

## Build

```
uv run sphinx-build --fresh-env --write-all --fail-on-warning --builder html . _build/html
```

## Serve

```
python3 -m http.server -d _build/html 8000
```
