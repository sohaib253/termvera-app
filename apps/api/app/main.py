import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes import (
    analysis,
    auth,
    clauserisk_demo,
    clauserisk_exports,
    comparisons,
    contracts,
    dashboard,
    demo,
    desktop,
    documents,
    exports,
    help,
    license,
    me,
    projects,
    requirements,
    risk_findings,
    samples,
)
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.session import AsyncSessionLocal
from app.services import document as document_service
from app.services.clauserisk import pipeline as pipeline_service

settings = get_settings()
setup_logging(settings.environment, settings.log_file)
logger = logging.getLogger("tenderguard.api")

@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # A restart kills any in-flight analysis background task. Reconcile those
    # rows before serving traffic so an interrupted run shows as failed and
    # re-runnable rather than spinning forever.
    async with AsyncSessionLocal() as db:
        await document_service.fail_interrupted_extractions(db)
        await pipeline_service.fail_interrupted_analyses(db)
    yield


app = FastAPI(title=f"{settings.app_name} API", version="0.1.0", lifespan=lifespan)

if settings.is_desktop:
    # The desktop server only ever serves this machine. Refusing any other
    # Host header stops a web page from reaching it via DNS rebinding (a
    # hostile domain re-pointed at 127.0.0.1), which matters because the
    # desktop build signs its user in without a password.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "request_id": getattr(request.state, "request_id", None),
            }
        },
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "message": "Request validation failed.",
                "details": exc.errors(),
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.exception("Unhandled error", extra={"request_id": request_id})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "message": "An unexpected error occurred. Please try again or contact support.",
                "request_id": request_id,
            }
        },
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(me.router)
app.include_router(dashboard.router)
app.include_router(samples.router)
app.include_router(projects.router)
app.include_router(documents.router)
app.include_router(requirements.router)
app.include_router(analysis.router)
app.include_router(exports.router)
app.include_router(demo.router)
app.include_router(license.router)
app.include_router(contracts.router)
app.include_router(risk_findings.router)
app.include_router(comparisons.router)
app.include_router(clauserisk_exports.router)
app.include_router(clauserisk_demo.router)
app.include_router(desktop.router)
app.include_router(help.router)


# The desktop build serves the exported web app from this same process and
# origin, so there is no second server and no CORS. Mounted last so every
# /api route above takes precedence; html=True serves index.html for
# directory paths and 404.html for unknown ones.
if settings.web_dist_dir and Path(settings.web_dist_dir).is_dir():
    app.mount("/", StaticFiles(directory=settings.web_dist_dir, html=True), name="web")
