from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.session import dispose_engine
from app.logging_conf import configure_logging
from app.middleware.access_log import AccessLogMiddleware
from app.middleware.auth_context import AuthContextMiddleware
from app.routers import admin, assets, auth, comments, exports, presentations, shares, versions

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    yield
    await dispose_engine()


app = FastAPI(
    title="promptDeck API",
    version="0.1.0",
    description="Internal presentation collaboration API (v1 scaffold).",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(AuthContextMiddleware)
app.add_middleware(AccessLogMiddleware)

api = APIRouter(prefix="/api/v1")
api.include_router(auth.router, prefix="/auth", tags=["auth"])
api.include_router(admin.router, prefix="/admin", tags=["admin"])
api.include_router(presentations.router)
api.include_router(versions.router)
api.include_router(comments.router)
api.include_router(shares.router)
api.include_router(exports.router)
app.include_router(api)
app.include_router(assets.router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
