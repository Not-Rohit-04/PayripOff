from fastapi import FastAPI 
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from .db import create_db_and_table , get_async_session


@asynccontextmanager
async def lifespan(app:FastAPI):
    await create_db_and_table()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/health-check")
async def health_check():
    return {"status": "OK"}