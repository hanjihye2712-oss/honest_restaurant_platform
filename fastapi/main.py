from contextlib import asynccontextmanager
from fastapi import FastAPI
from model import load_pipeline
from router import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_pipeline()
    yield


app = FastAPI(
    title="감성 분석 API",
    description="한국어 식당 리뷰 긍정/부정 분류",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)
