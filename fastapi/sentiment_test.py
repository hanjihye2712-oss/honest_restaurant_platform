"""
HuggingFace 한국어 감성 분석 모델 테스트
모델: Copycats/koelectra-base-v3-generalized-sentiment-analysis
레이블: LABEL_0 = 부정 / LABEL_1 = 긍정 (이진 분류)
"""

from transformers import pipeline

MODEL_NAME = "Copycats/koelectra-base-v3-generalized-sentiment-analysis"


def load_pipeline():
    print(f"모델 로딩 중: {MODEL_NAME}")
    clf = pipeline("text-classification", model=MODEL_NAME)
    print("로딩 완료!\n")
    return clf


def to_korean(label: str) -> str:
    return "긍정" if label == "1" else "부정"


def analyze(clf, texts: list[str]):
    results = clf(texts)
    for text, result in zip(texts, results):
        polarity = to_korean(result["label"])
        score    = result["score"]
        bar      = "█" * int(score * 20)
        print(f"  입력  : {text}")
        print(f"  결과  : {polarity}  신뢰도: {score:.4f}  {bar}")
        print()


TEST_CASES = [
    # 명확한 긍정
    "오늘 정말 맛있는 음식을 먹었어요. 최고였습니다!",
    "서비스가 너무 친절하고 음식도 훌륭했어요.",
    "가성비 갑! 재방문 의사 있어요.",
    "친구들이랑 왔는데 분위기도 좋고 맛도 좋았어요.",
    # 명확한 부정
    "음식이 너무 짜고 맛없었어요. 다시는 안 갈 것 같아요.",
    "서비스가 불친절하고 기다리는 시간도 너무 길었습니다.",
    "위생 상태가 너무 안 좋아서 충격받았어요.",
    "음식이 식어서 나왔어요. 돈 아깝습니다.",
    # 애매한 케이스
    "웨이팅이 길었지만 맛은 최고였어요.",
    "가격은 좀 비싸지만 맛은 있어요.",
    "그냥 평범해요. 특별하지는 않아요.",
    "맛없지는 않았어요.",
]


if __name__ == "__main__":
    clf = load_pipeline()

    print("=" * 60)
    print("식당 리뷰 감성 분석 테스트")
    print(f"모델: {MODEL_NAME}")
    print("=" * 60 + "\n")

    analyze(clf, TEST_CASES)

    print("=" * 60)
    print("직접 입력 테스트  (빈 줄 입력 시 종료)")
    print("=" * 60 + "\n")
    while True:
        user_input = input("리뷰 입력 > ").strip()
        if not user_input:
            break
        analyze(clf, [user_input])
