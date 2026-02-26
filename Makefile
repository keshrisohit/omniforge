.PHONY: test test-fast test-full test-cov lint fmt typecheck

# Fast unit tests only — skips integration folder + docker/eval markers (~30-60s)
test:
	pytest --no-cov -q --ignore=tests/integration -m "not docker and not eval"

# Full parallel test run — all tests, no coverage (~4 min)
test-full:
	pytest --no-cov -q

# Full run with coverage report
test-cov:
	pytest -q

# Code quality
lint:
	ruff check .

fmt:
	black .

typecheck:
	mypy src/
