"""
리뷰 분류 엔드포인트 테스트 (골목장인 태그 + 대시보드 태그 + AI 카테고리)

실행: fastapi/ 디렉토리에서
    .venv/bin/python -m pytest tests/test_review_classifier.py -v

주의: 최초 실행 시 mDeBERTa 모델 다운로드(~500MB)가 진행됩니다.
"""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


# ─── 응답 스펙 검증 ───────────────────────────────────────────────────────────

def test_response_shape(client):
    """응답 필드 구조와 타입이 스펙대로인지 확인."""
    resp = client.post("/review-classifier/analyze", json={"text": "맛있어요"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["alley_tags"],           list)
    assert isinstance(data["alley_tag_scores"],     dict)
    assert isinstance(data["dashboard_tags"],       list)
    assert isinstance(data["ai_positive_keywords"], list)
    assert isinstance(data["ai_negative_keywords"], list)
    # alley_tag_scores는 항상 4개 키를 가져야 함
    assert len(data["alley_tag_scores"]) == 4
    for score in data["alley_tag_scores"].values():
        assert 0.0 <= score <= 1.0


# ─── 대시보드 태그: 키워드 매칭 ─────────────────────────────────────────────

@pytest.mark.parametrize("text,expected_tags", [
    ("음식이 너무 맛있어요. 양도 푸짐하고 가성비 최고!",
     ["맛있어요", "양이 많아요", "가성비 좋아요"]),
    ("너무 짜고 기름졌어요. 위생도 별로였어요.",
     ["짜요", "기름져요"]),
    ("친절하고 빠르게 나왔어요. 혼밥하기도 좋아요.",
     ["친절해요", "빠른 서비스", "혼밥 가능해요"]),
    ("불친절했고 오래 기다렸어요. 다시는 안 올 것 같아요.",
     ["불친절해요", "느린 서비스", "재방문 없어요"]),
])
def test_dashboard_tags(client, text, expected_tags):
    resp = client.post("/review-classifier/analyze", json={"text": text})
    assert resp.status_code == 200
    detected = resp.json()["dashboard_tags"]
    for tag in expected_tags:
        assert tag in detected, f"'{tag}'이 감지되지 않음. 감지된 태그: {detected}"


# ─── AI 카테고리: 긍정 ───────────────────────────────────────────────────────

@pytest.mark.parametrize("text,expected_positive", [
    ("정말 청결하고 위생적이에요.",         ["위생"]),
    ("꼭 다시 올게요. 단골이 될 것 같아요.", ["재방문"]),
    ("사장님이 너무 친절하고 배려가 넘쳐요.", ["응대"]),
    ("주문하자마자 바로 나왔어요. 신속해요.", ["회전율"]),
])
def test_ai_positive_keywords(client, text, expected_positive):
    resp = client.post("/review-classifier/analyze", json={"text": text})
    assert resp.status_code == 200
    detected = resp.json()["ai_positive_keywords"]
    for kw in expected_positive:
        assert kw in detected, f"'{kw}'이 긍정에 없음. 감지된 긍정: {detected}"


# ─── AI 카테고리: 부정 ───────────────────────────────────────────────────────

@pytest.mark.parametrize("text,expected_negative", [
    ("바퀴벌레가 나왔어요. 너무 지저분해요.",             ["위생"]),
    ("다시는 안 올 것 같아요. 두 번은 안 오겠어요.",     ["재방문"]),
    ("직원이 무뚝뚝하고 불친절했어요.",                  ["응대"]),
    ("한참을 기다렸는데 음식이 늦게 나왔어요.",           ["회전율"]),
])
def test_ai_negative_keywords(client, text, expected_negative):
    resp = client.post("/review-classifier/analyze", json={"text": text})
    assert resp.status_code == 200
    detected = resp.json()["ai_negative_keywords"]
    for kw in expected_negative:
        assert kw in detected, f"'{kw}'이 부정에 없음. 감지된 부정: {detected}"


# ─── 골목장인 태그: mDeBERTa zero-shot ────────────────────────────────────────

def test_alley_tag_local_recommendation(client):
    """'현지인 추천' 태그가 의미적으로 유사한 텍스트에서 높은 점수를 받는지 확인."""
    text = "여기 동네 사람들만 알아요. 외지인들한테는 알려지기 싫은 단골 맛집이에요."
    resp = client.post("/review-classifier/analyze", json={"text": text})
    assert resp.status_code == 200
    data   = resp.json()
    scores = data["alley_tag_scores"]
    assert "현지인 추천" in scores
    # 의미적으로 명확한 케이스 — 최소 0.4 이상 기대
    assert scores["현지인 추천"] >= 0.4, f"점수 낮음: {scores['현지인 추천']}"


def test_alley_tag_hidden_gem(client):
    """'나만 알고 싶은' 태그 테스트."""
    text = "아직 아무도 모르는 숨겨진 맛집. 유명해지면 안 되는데 ㅠㅠ"
    resp = client.post("/review-classifier/analyze", json={"text": text})
    assert resp.status_code == 200
    scores = resp.json()["alley_tag_scores"]
    assert scores["나만 알고 싶은"] >= 0.4, f"점수 낮음: {scores['나만 알고 싶은']}"


def test_alley_tag_scores_sum_reasonable(client):
    """multi_label=True이므로 점수 합이 1을 초과할 수 있음을 확인."""
    text = "현지인 단골 맛집. 가성비 최고고 사장님도 친절해요."
    resp = client.post("/review-classifier/analyze", json={"text": text})
    assert resp.status_code == 200
    scores = resp.json()["alley_tag_scores"]
    # multi_label이므로 개별 점수가 모두 0~1 범위여야 함
    for tag, score in scores.items():
        assert 0.0 <= score <= 1.0, f"{tag} 점수 범위 이상: {score}"


# ─── 복합 시나리오 ─────────────────────────────────────────────────────────────

def test_full_alley_master_candidate(client):
    """골목장인 배지 후보 리뷰: alley_tags가 1개 이상 탐지되는지 확인."""
    text = (
        "동네에서만 알려진 숨은 맛집이에요. "
        "사장님이 너무 친절하시고, 양도 엄청 푸짐하고 가성비가 진짜 최고예요."
    )
    resp = client.post("/review-classifier/analyze", json={"text": text})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["alley_tags"]) >= 1, f"alley_tags 미탐지: {data['alley_tag_scores']}"
    assert len(data["dashboard_tags"]) >= 1


# ─── 입력 유효성 ─────────────────────────────────────────────────────────────

def test_empty_text(client):
    resp = client.post("/review-classifier/analyze", json={"text": ""})
    assert resp.status_code == 422


def test_missing_text(client):
    resp = client.post("/review-classifier/analyze", json={})
    assert resp.status_code == 422


def test_too_long_text(client):
    resp = client.post("/review-classifier/analyze", json={"text": "가" * 5001})
    assert resp.status_code == 422
