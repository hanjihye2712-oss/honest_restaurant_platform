import os

# 감성 분석 모델
MODEL_NAME = "Copycats/koelectra-base-v3-generalized-sentiment-analysis"

# 번역 모델 (한국어 → 영어)
TRANSLATION_MODEL_NAME = "Helsinki-NLP/opus-mt-ko-en"

# 가짜 리뷰 탐지 모델 (LABEL_0=정상, LABEL_1=스팸/가짜)
FAKE_REVIEW_MODEL_NAME = "mrm8488/bert-tiny-finetuned-sms-spam-detection"
