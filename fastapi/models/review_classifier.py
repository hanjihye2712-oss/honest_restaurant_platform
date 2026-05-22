import logging

from transformers import pipeline, Pipeline

from config import REVIEW_CLASSIFIER_MODEL_NAME

logger = logging.getLogger(__name__)

_clf: Pipeline | None = None

# ── 골목장인 배지 후보 라벨 ──────────────────────────────────────────────
# key: DB에 저장될 태그명  /  value: mDeBERTa에 넘기는 설명형 레이블
ALLEY_LABELS: dict[str, str] = {
    "현지인 추천":    "현지 주민이 단골로 자주 찾는 맛집",
    "나만 알고 싶은": "아직 널리 알려지지 않은 숨겨진 맛집",
    "친절함":        "사장님과 직원이 친절하고 따뜻한 식당",
    "혜자로운":       "가격 대비 음식 양이 많고 가성비가 뛰어난 식당",
}

ALLEY_THRESHOLD = 0.5  # 이 점수 이상이면 해당 태그 인정

HYPOTHESIS_TEMPLATE = "이 리뷰는 {}에 관한 내용이다."

# ── 사장님 대시보드 태그 키워드 사전 (1차 매칭) ──────────────────────────
DASHBOARD_KEYWORDS: dict[str, list[str]] = {
    "맛있어요":     ["맛있", "맛남", "맛 좋", "맛이 좋", "맛이 끝", "맛나"],
    "매워요":      ["매워", "맵다", "매운", "칼칼", "얼얼", "화끈"],
    "짜요":        ["짜다", "짜게", "짜요", "짜서", "짜고", "간이 세", "짭짤"],
    "싱거워요":    ["싱겁", "심심한", "싱거", "간이 약"],
    "달아요":      ["달다", "달아요", "단맛", "달콤"],
    "기름져요":    ["기름", "느끼"],
    "양이 많아요":  ["양이 많", "푸짐", "넉넉", "양많", "배부"],
    "양이 적어요":  ["양이 적", "양이 부족", "조금 적"],
    "위생적이에요": ["깨끗", "위생적", "청결", "정갈"],
    "불결해요":    ["더럽", "지저분", "바퀴", "머리카락", "곰팡이", "불결"],
    "친절해요":    ["친절", "따뜻하게 맞", "배려"],
    "불친절해요":  ["불친절", "무뚝뚝", "차갑게", "쌀쌀맞"],
    "빠른 서비스": ["빨리 나", "빠르게 나", "신속", "바로 나", "금방 나"],
    "느린 서비스": ["오래 기다", "늦게 나", "한참 기다"],
    "재방문이에요": ["또 올", "다시 올", "재방문", "단골", "꼭 다시"],
    "재방문 없어요": ["다시는", "안 올", "두 번은 안", "다시 안"],
    "가성비 좋아요": ["가성비", "가격 대비", "저렴한데", "싼데 맛"],
    "비싸요":      ["비싸", "가격이 높", "돈이 아까"],
    "혼밥 가능해요": ["혼밥", "혼자 와도", "혼자서도"],
    "분위기 좋아요": ["분위기", "인테리어", "아늑"],
}

# ── AI 점수 카테고리 키워드 (1차 매칭) ────────────────────────────────
AI_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "위생_긍정":   ["깨끗", "위생적", "청결", "정갈", "신선"],
    "위생_부정":   ["더럽", "지저분", "바퀴", "머리카락", "곰팡이", "불결"],
    "재방문_긍정": ["또 올", "다시 올", "재방문", "단골", "꼭 다시"],
    "재방문_부정": ["다시는", "안 올", "두 번은 안", "다시 안"],
    "응대_긍정":   ["친절", "따뜻", "배려", "정성껏", "잘 챙겨"],
    "응대_부정":   ["불친절", "무뚝뚝", "차갑게", "쌀쌀맞", "무시"],
    "회전율_긍정": ["빨리 나", "신속", "바로 나", "금방 나"],
    "회전율_부정": ["오래 기다", "늦게 나", "한참 기다"],
}


def load_pipeline() -> Pipeline:
    global _clf
    logger.info("리뷰 분류 모델 로딩 중: %s", REVIEW_CLASSIFIER_MODEL_NAME)
    _clf = pipeline(
        "zero-shot-classification",
        model=REVIEW_CLASSIFIER_MODEL_NAME,
    )
    logger.info("리뷰 분류 모델 로딩 완료")
    return _clf


def get_pipeline() -> Pipeline:
    if _clf is None:
        raise RuntimeError("리뷰 분류 모델이 로드되지 않았습니다. lifespan 설정을 확인하세요.")
    return _clf


_NEG_PREFIXES = ("불", "안", "못")  # 바로 앞에 붙으면 부정 의미


def _match_keywords(text: str, keyword_dict: dict[str, list[str]]) -> list[str]:
    results = []
    for tag, kws in keyword_dict.items():
        for kw in kws:
            pos = text.find(kw)
            if pos == -1:
                continue
            # "불친절" → "친절" 오탐 방지: 부정 접두어 바로 앞에 붙은 경우 스킵
            if pos > 0 and text[pos - 1] in _NEG_PREFIXES:
                continue
            results.append(tag)
            break
    return results


def classify(text: str) -> dict:
    clf = get_pipeline()

    # ── 1. 골목장인 태그: mDeBERTa zero-shot (의미 기반) ────────────
    alley_result = clf(
        text,
        candidate_labels=list(ALLEY_LABELS.values()),
        multi_label=True,
        hypothesis_template=HYPOTHESIS_TEMPLATE,
    )
    desc_to_key = {v: k for k, v in ALLEY_LABELS.items()}
    alley_tag_scores: dict[str, float] = {
        desc_to_key[label]: round(float(score), 4)
        for label, score in zip(alley_result["labels"], alley_result["scores"])
    }
    alley_tags = [tag for tag, score in alley_tag_scores.items() if score >= ALLEY_THRESHOLD]

    # ── 2. 대시보드 태그: 키워드 사전 매칭 ──────────────────────────
    dashboard_tags = _match_keywords(text, DASHBOARD_KEYWORDS)

    # ── 3. AI 카테고리: 키워드 매칭 후 긍정/부정 분리 ────────────────
    ai_positive_keywords: list[str] = []
    ai_negative_keywords: list[str] = []
    for category, kws in AI_CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in kws):
            cat_name, sentiment = category.rsplit("_", 1)
            if sentiment == "긍정":
                ai_positive_keywords.append(cat_name)
            else:
                ai_negative_keywords.append(cat_name)

    return {
        "alley_tags":            alley_tags,
        "alley_tag_scores":      alley_tag_scores,
        "dashboard_tags":        dashboard_tags,
        "ai_positive_keywords":  list(set(ai_positive_keywords)),
        "ai_negative_keywords":  list(set(ai_negative_keywords)),
    }
