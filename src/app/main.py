import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.api import main_router
from app.core.common import configure_logging
from app.workers.worker import Worker

configure_logging()

stop_event = asyncio.Event()
worker = Worker(stop_event)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    worker_task = asyncio.create_task(worker.worker_loop())
    yield
    # shutdown
    stop_event.set()
    await worker_task


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.include_router(main_router)

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
