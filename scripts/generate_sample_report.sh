#!/usr/bin/env bash
set -euo pipefail
financial-report generate --ticker AAPL --as-of 2026-04-28 --format all --out-dir out
