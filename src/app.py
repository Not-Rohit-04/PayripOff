from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from .db import create_db_and_table, get_async_session
from src.routers.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_table()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(auth_router)


@app.get("/health-check")
async def health_check():
    return {"status": "OK"}
