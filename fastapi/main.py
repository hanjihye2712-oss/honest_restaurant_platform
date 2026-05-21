from contextlib import asynccontextmanager
from fastapi import FastAPI

from models.sentiment   import load_pipeline as load_sentiment_model
from models.fake_review import load_model    as load_fake_review_model
from routers            import sentiment, fake_review


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_sentiment_model()    # 감성 분석 모델
    load_fake_review_model()  # 가짜 리뷰 탐지 모델
    yield


app = FastAPI(
    title="AI 분석 API",
    description="한국어 식당 리뷰 감성 분석 + 가짜 리뷰 탐지",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(sentiment.router)    # /analyze, /health
app.include_router(fake_review.router)  # /fake-review/detect
