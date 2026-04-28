#!/usr/bin/env bash
set -euo pipefail
financial-report generate --ticker MSFT --as-of 2026-04-28 --format all --out-dir out
