from contextlib import asynccontextmanager

from fastapi import FastAPI

from models.fake_review       import load_models   as load_fake_review_models
from models.review_classifier import load_pipeline as load_review_classifier
from models.sentiment         import load_pipeline as load_sentiment_model
from routers                  import fake_review, review_classifier, sentiment


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_sentiment_model()     # 감성 분석 모델 (koelectra)
    load_fake_review_models()  # 번역 모델(Helsinki-NLP) + 가짜 탐지 모델
    load_review_classifier()   # 리뷰 분류 모델 (mDeBERTa zero-shot)
    yield


app = FastAPI(
    title="AI 분석 API",
    description="한국어 식당 리뷰 감성 분석 + 가짜 리뷰 탐지 + 리뷰 분류",
    version="3.0.0",
    lifespan=lifespan,
)

app.include_router(sentiment.router)          # /analyze, /health
app.include_router(fake_review.router)        # /fake-review/detect
app.include_router(review_classifier.router)  # /review-classifier/analyze
