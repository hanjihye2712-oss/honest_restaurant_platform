import os

# 감성 분석 모델
MODEL_NAME = "Copycats/koelectra-base-v3-generalized-sentiment-analysis"

# 번역 모델 (한국어 → 영어)
TRANSLATION_MODEL_NAME = "Helsinki-NLP/opus-mt-ko-en"

# 가짜 리뷰 탐지 모델 (REAL=정상, FAKE=가짜)
FAKE_REVIEW_MODEL_NAME = "theArijitDas/distilbert-finetuned-fake-reviews"

# 리뷰 분류 모델 (골목장인 태그 zero-shot)
REVIEW_CLASSIFIER_MODEL_NAME = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
