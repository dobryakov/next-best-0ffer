from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

from app.middleware.observability import ObservabilityMiddleware, configure_structlog
from app.routes import customers as customers_routes
from app.routes import events as events_routes
from app.routes import health as health_routes
from infra.config.settings import Settings, get_settings

SERVICE_NAME = "nbo-api"


def create_app() -> FastAPI:
    settings = get_settings()
    configure_structlog(settings.log_level)

    app = FastAPI(
        title="Next Best Offer API",
        version="0.1.0",
        default_response_class=JSONResponse,
    )

    app.state.settings = settings

    app.add_middleware(ObservabilityMiddleware, service_name=SERVICE_NAME)
    app.include_router(health_routes.router)
    app.include_router(customers_routes.router)
    app.include_router(events_routes.router)

    @app.get("/_/settings", tags=["internal"], include_in_schema=False)
    def read_settings(current: Settings = Depends(get_settings)) -> dict[str, str | int]:
        return {
            "environment": current.environment,
            "log_level": current.log_level,
            "api_port": current.api_port,
        }

    return app


app = create_app()


