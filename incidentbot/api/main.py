from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from incidentbot.api.routes import incidents, widget
from incidentbot.configuration.settings import settings
from incidentbot.version import APP_VERSION


@asynccontextmanager
async def lifespan(app: FastAPI):
    from incidentbot.scheduler.core import process as task_scheduler
    from incidentbot.startup import (
        connect_platform,
        db_check,
        emit_startup_log,
        init_platform,
        post_startup_checks,
        startup_tasks,
    )

    db_check()
    startup_tasks()
    task_scheduler.start()
    init_platform()
    connect_platform()
    post_startup_checks()
    emit_startup_log()

    yield

    task_scheduler.scheduler.shutdown(wait=False)


app = FastAPI(
    title="incidentbot",
    summary="Incident management API",
    version=APP_VERSION,
    docs_url="/api/v1/docs" if settings.ENABLE_API_DOCS else None,
    openapi_url="/api/v1/openapi.json" if settings.ENABLE_API_DOCS else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": exc.errors(), "body": exc.body}),
    )


@app.get("/health")
async def health():
    return {"healthy": True}


app.include_router(incidents.router)
app.include_router(widget.router)
