from incidentbot.api.routes import (
    health,
    incident,
    job,
    login,
    maintenance_window,
    pager,
    setting,
    users,
)
from incidentbot.configuration.settings import settings, __version__

from fastapi import (
    APIRouter,
    FastAPI,
    Request,
    status,
)
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

"""
Run Init Tasks
"""

app = FastAPI(
    title="incidentbot",
    summary="Incident Bot API",
    version=__version__,
    docs_url="/docs" if settings.api.enable_docs_endpoint else None,
    openapi_url=(
        "/openapi.json" if settings.api.enable_openapi_endpoint else None
    ),
    redoc_url="/redoc" if settings.api.enable_redoc_endpoint else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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


"""
Router
"""

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])

if settings.api.enabled:
    api_router.include_router(incident.router, tags=["incident"])
    api_router.include_router(job.router, tags=["job"])
    api_router.include_router(login.router, tags=["login"])
    api_router.include_router(
        maintenance_window.router, tags=["maintenance_window"]
    )
    api_router.include_router(pager.router, tags=["pager"])
    api_router.include_router(setting.router, tags=["setting"])
    api_router.include_router(users.router, tags=["users"])

app.include_router(api_router, prefix=settings.api.v1_str)
