from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from prometheus_fastapi_instrumentator import Instrumentator

from .db import init_db
from .schemas import AskRequest, AskResponse
from .services import generate_answer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Chat Service")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Prometheus metrics before startup
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)

@app.on_event("startup")
async def on_startup() -> None:
    await init_db()


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@limiter.limit("10/minute")
@app.post("/chat/ask", response_model=AskResponse)
async def chat_ask(request: Request, payload: AskRequest) -> AskResponse:
    try:
        answer, session_id = await generate_answer(payload.question, payload.session_id)
    except Exception as exc:  # broad for simplicity in MVP
        raise HTTPException(status_code=500, detail=str(exc))
    return AskResponse(answer=answer, session_id=session_id) 