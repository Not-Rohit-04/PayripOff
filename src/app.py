from dotenv import load_dotenv

load_dotenv()
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from .db import create_db_and_table, get_async_session
from src.routers.auth import router as auth_router
from src.routers.groups import router as group_router
from .routers.expenses import router as expense_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_table()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(auth_router)
app.include_router(group_router)
app.include_router(expense_router)


@app.get("/health-check")
async def health_check():
    return {"status": "OK"}
