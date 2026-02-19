# TASK-001: Setup Infrastructure
**Complexity:** Simple

## Add Dependencies (`pyproject.toml`)

**Production:**
- `fastapi>=0.100.0`
- `uvicorn>=0.23.0`
- `pydantic>=2.0.0`

**Dev:**
- `pytest-asyncio>=0.21.0`
- `httpx>=0.24.0`

## Create Directory Structure

```
src/omniforge/
    api/
        __init__.py
        routes/
            __init__.py
        middleware/
            __init__.py
    chat/
        __init__.py

tests/
    api/
        __init__.py
    chat/
        __init__.py
```

All `__init__.py` files can be empty initially.

## Configure pytest-asyncio (`pyproject.toml`)

Add to `[tool.pytest.ini_options]`:
```toml
asyncio_mode = "auto"
```

## Verification

```bash
pip install -e ".[dev]"
python -c "import fastapi; import uvicorn; import pydantic; import httpx; import pytest_asyncio"
ls src/omniforge/api/__init__.py src/omniforge/chat/__init__.py tests/api/__init__.py tests/chat/__init__.py
```
