import logging

import uvicorn

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.achievements import achievements_router
from routes.ratings import ratings_router
from routes.users import users_router

logging.basicConfig(level=logging.INFO, filename="log.log")


async def lifespan():
    # await db_init()
    ...
    # yield


app = FastAPI(
    title="BGITU Achievements",
    version="1",
    on_startup=[lifespan],
    docs_url="/docs",
    redoc_url=None,
)


app.include_router(users_router)
app.include_router(achievements_router)
app.include_router(ratings_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: изменить на prod`e
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
