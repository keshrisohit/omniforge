# TASK-008: Quality Verification
**Complexity:** Simple | **Depends on:** TASK-007

## Run All Quality Checks

Execute each check and fix any issues:

```bash
# 1. Run tests with coverage
pytest --cov=src/omniforge --cov-report=term-missing

# 2. Verify coverage > 80%
pytest --cov=src/omniforge --cov-fail-under=80

# 3. Format code
black .

# 4. Lint and auto-fix
ruff check . --fix

# 5. Type check
mypy src/
```

## Expected Results

| Check | Expected Result |
|-------|-----------------|
| pytest | All tests pass |
| coverage | >= 80% |
| black | No changes needed (or apply formatting) |
| ruff | No errors (or fix them) |
| mypy | No type errors |

## Fix Common Issues

- **Missing type annotations**: Add return types and parameter types
- **Import errors**: Check `__init__.py` exports
- **Line length**: Break long lines at 100 chars
- **Unused imports**: Remove them

## Final Verification

All commands should pass without errors:
```bash
pytest && black --check . && ruff check . && mypy src/
```
