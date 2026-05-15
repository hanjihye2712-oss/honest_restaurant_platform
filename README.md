# 정직식당 (Honest Restaurant)

> 정부인증 기반 정직한 동네 가게 발굴 플랫폼


---

## 프로젝트 구조

```
project/
├── mysite/                  # Django 설정 (settings, urls)
├── accounts/                # 회원가입·로그인·JWT 인증
│   ├── models.py            # UserProfile (역할 관리)
│   ├── authentication.py    # HttpOnly 쿠키 기반 JWT 인증
│   ├── context_processors.py
│   └── views.py             # JWT API 뷰
├── honest_restaurant/       # 메인 앱
│   ├── models.py            # 식당·리뷰·영수증인증·미디어
│   ├── views.py             # 템플릿 뷰 + API 뷰셋
│   └── templates/
│       ├── base.html
│       ├── partials/        # header, footer
│       └── restaurants/     # index, list, detail, verify
├── static/
│   ├── css/                 # base, header, footer, index, restaurant_list
│   └── img/                 # 음식 이미지 (김밥, 칼국수 등)
└── requirements.txt
```

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| Backend | Django 6.0.4 |
| REST API | Django REST Framework 3.17.1 |
| 인증 | JWT (djangorestframework-simplejwt 5.4.0) |
| DB | SQLite3 |
| Frontend | Django Template + Vanilla CSS/JS |

---

## 주요 기능

### 1. 메인 페이지 (`/`)
- 오늘 발굴된 정직 가게 카드 목록 (12개)
- 가게 상세 / 영수증 인증 / 사장님 대시보드 섹션 전환
- 비로그인 유저는 카드 클릭 시 로그인 페이지로 이동

### 2. 식당 목록 페이지 (`/restaurants/`)
- 서울시 공공데이터 기반 식당 목록
- 자치구 / 업태 필터링, 가게명·주소 검색
- 페이지네이션 (20개씩)

### 3. 식당 상세 페이지 (`/restaurants/<pk>/`)
- 식당 정보, 신뢰 증명서, 메뉴 등록가
- 이미지/동영상 업로드 (사장님·관리자 전용)
- 영수증 인증 후 리뷰 작성 가능

### 4. 영수증 인증 (`/restaurants/<pk>/verify/`)
- 영수증 이미지 업로드 → 관리자 검토 후 승인
- 인증 완료 시 리뷰 작성 권한 부여

### 5. JWT 인증 API

| 메서드 | URL | 설명 |
|--------|-----|------|
| POST | `/accounts/api/login/` | 로그인 → JWT 쿠키 발급 |
| POST | `/accounts/api/logout/` | 로그아웃 → 토큰 블랙리스트 + 쿠키 삭제 |
| POST | `/accounts/api/token/refresh/` | Access 토큰 갱신 |
| GET | `/accounts/api/me/` | 현재 유저 정보 조회 |

---

## JWT 보안 설정

| 항목 | 값 |
|------|-----|
| Access Token 유효기간 | 15분 (운영) |
| Refresh Token 유효기간 | 7일 (운영) |
| 토큰 로테이션 | 활성화 |
| 블랙리스트 | 활성화 |
| 저장 방식 | HttpOnly 쿠키 (XSS 방어) |
| SameSite | Lax (CSRF 방어) |
| 로그인 Rate Limit | 5회/분 |

> 개발 환경에서는 Access Token을 24시간으로 늘려 설정되어 있습니다.
> 운영 배포 전 `settings.py`에서 `ACCESS_TOKEN_LIFETIME = timedelta(minutes=15)`로 변경하세요.

---

## 사용자 권한 구조

| 역할 | 값 | 사장님 전용 버튼 | 미디어 업로드 | 리뷰 작성 |
|------|-----|:-:|:-:|:-:|
| 손님 | `guest` | X | X | 인증 후 가능 |
| 사장님 | `owner` | O | O | 인증 후 가능 |
| 관리자 | `admin` | O | O | 인증 후 가능 |

역할 변경: Django Admin (`/admin/`) → 유저 선택 → 역할 섹션에서 변경

---

## 로컬 실행 방법

```bash
# 1. 가상환경 활성화
source .venv/bin/activate

# 2. 패키지 설치
pip install -r requirements.txt

# 3. DB 마이그레이션
python manage.py migrate

# 4. 슈퍼유저 생성
python manage.py createsuperuser

# 5. 서버 실행
python manage.py runserver
```

접속: http://127.0.0.1:8000

---

## 환경 변수 (`.env`)

```
SEOUL_API_KEY=서울시_공공데이터_API_키
```

---

## 데이터 출처

서울 열린데이터광장 `LOCALDATA_072404`
