"""
FastAPI 감성 분석 엔드포인트 테스트
실행: fastapi/ 디렉토리에서
    .venv/bin/python -m pytest tests/ -v
"""

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


# ─── 헬스 체크 ───────────────────────────────────────────────────

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ─── 긍정 케이스 ─────────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "오늘 정말 맛있는 음식을 먹었어요. 최고였습니다!",
    "서비스가 너무 친절하고 음식도 훌륭했어요.",
    "가성비 갑! 재방문 의사 있어요.",
])
def test_positive(client, text):
    resp = client.post("/analyze", json={"text": text})
    assert resp.status_code == 200
    data = resp.json()
    assert data["label"] == "긍정"
    assert 0.0 <= data["score"] <= 1.0


# ─── 부정 케이스 ─────────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "음식이 너무 짜고 맛없었어요. 다시는 안 갈 것 같아요.",
    "서비스가 불친절하고 기다리는 시간도 너무 길었습니다.",
    "위생 상태가 너무 안 좋아서 충격받았어요.",
])
def test_negative(client, text):
    resp = client.post("/analyze", json={"text": text})
    assert resp.status_code == 200
    data = resp.json()
    assert data["label"] == "부정"
    assert 0.0 <= data["score"] <= 1.0


# ─── 입력 유효성 ─────────────────────────────────────────────────

def test_empty_text(client):
    resp = client.post("/analyze", json={"text": ""})
    assert resp.status_code == 422


def test_missing_text(client):
    resp = client.post("/analyze", json={})
    assert resp.status_code == 422


def test_too_long_text(client):
    resp = client.post("/analyze", json={"text": "가" * 5001})
    assert resp.status_code == 422
