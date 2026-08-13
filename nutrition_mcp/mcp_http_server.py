import contextlib
import logging
from collections.abc import AsyncIterator

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

from nutrition_mcp.mcp_server import NutritionMCPServer

logger = logging.getLogger(__name__)


def create_app() -> Starlette:
    """Create and configure the Starlette application."""
    nutrition_server = NutritionMCPServer()

    async def healthz(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    async def readyz(request: Request) -> JSONResponse:
        if nutrition_server.nutrition_db is None:
            try:
                from database import NutritionDB
                nutrition_server.nutrition_db = NutritionDB(
                    nutrition_server.db_path, enable_llm=False
                )
            except Exception:
                return JSONResponse({"status": "not ready"}, status_code=503)
        return JSONResponse({"status": "ready"})

    session_manager = StreamableHTTPSessionManager(
        app=nutrition_server.server,
        json_response=True,
    )

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        async with session_manager.run():
            logger.info("MCP HTTP server started on port 8080")
            yield
        nutrition_server.cleanup()

    return Starlette(
        routes=[
            Route("/healthz", healthz),
            Route("/readyz", readyz),
            Mount("/mcp", app=session_manager.handle_request),
        ],
        lifespan=lifespan,
    )


app = create_app()


def main():
    uvicorn.run(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
