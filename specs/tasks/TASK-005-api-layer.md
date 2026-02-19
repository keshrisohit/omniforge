# TASK-005: API Layer
**Complexity:** Medium | **Depends on:** TASK-004

## Chat Endpoint (`src/omniforge/api/routes/chat.py`)

1. Create `router = APIRouter(prefix="/api/v1", tags=["chat"])`

2. **Helper: _stream_response(request, http_request) -> AsyncIterator[str]**
   - Call `_chat_service.process_chat(request)`
   - Check `await http_request.is_disconnected()` each iteration
   - Break loop if client disconnected

3. **@router.post("/chat") async def chat(request: Request, body: ChatRequest)**
   - Return `StreamingResponse` with:
     - `media_type="text/event-stream"`
     - Headers: `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`

4. Export router in `src/omniforge/api/routes/__init__.py`

## Error Handler Middleware (`src/omniforge/api/middleware/error_handler.py`)

1. **setup_error_handlers(app: FastAPI) -> None**

2. Handle `ChatError` - return JSONResponse with status_code, code, message

3. Handle `PydanticValidationError` - format errors, return 400

4. Handle generic `Exception` - log, return 500 with "internal_error"

## FastAPI App Factory (`src/omniforge/api/app.py`)

1. **create_app() -> FastAPI**
   - Title: "OmniForge Chat API"
   - Version: "0.1.0"
   - Add CORS middleware (allow_origins=["*"] for dev)
   - Call `setup_error_handlers(app)`
   - Include chat router
   - Add health check: `@app.get("/health")` returning `{"status": "healthy"}`

2. Create module-level `app = create_app()` for uvicorn

## Verification

```bash
mypy src/omniforge/api/
uvicorn omniforge.api.app:app --port 8000 &
sleep 2
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/v1/chat -H "Content-Type: application/json" -d '{"message": "Hello"}'
pkill -f "uvicorn omniforge"
```
