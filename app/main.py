from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from strawberry.http.ides import get_graphql_ide_html

from app.api.router import api_router
from app.api.routes.health import router as health_router
from app.api.routes.resources import router as resource_router
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.graphql_api import graphql_router
from app.middleware.request_context import RequestContextMiddleware


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.LOG_LEVEL)
    app = FastAPI(
        title=settings.app_name,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )
    app.dependency_overrides[get_settings] = lambda: settings
    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)

    @app.get("/graphql", include_in_schema=False, response_class=HTMLResponse)
    async def graphql_ide() -> HTMLResponse:
        return HTMLResponse(get_graphql_ide_html("graphiql"))

    app.include_router(health_router)
    app.include_router(api_router)
    app.include_router(resource_router)
    app.include_router(graphql_router, prefix="/graphql")

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"message": settings.app_name}

    return app


app = create_app()
