.PHONY: lint format typecheck test run-sample

lint:
	ruff check .
	black --check .

format:
	black .
	ruff check --fix .

typecheck:
	mypy src

test:
	pytest -q --cov=src --cov-report=term-missing

run-sample:
	bash scripts/generate_sample_report.sh
