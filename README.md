# financial-reports

Production-oriented pipeline to generate deterministic DCF-based equity reports.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
make test
financial-report generate --ticker MSFT --as-of 2026-04-28 --format all --out-dir ./out
```

## Make targets

- `make lint`
- `make format`
- `make typecheck`
- `make test`
- `make run-sample`
