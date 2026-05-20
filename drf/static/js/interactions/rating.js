/**
 * 별점 API
 *
 * 의존: api.js (axios 인스턴스 `api`)
 *
 * 사용 예)
 *   RatingAPI.save(restaurantId, 4)       // 등록 또는 수정 (upsert)
 *   RatingAPI.listByRestaurant(restaurantId)
 *   RatingAPI.remove(ratingId)
 */

const RatingAPI = (() => {
  /** 별점 등록 또는 수정 (식당당 1개, upsert) */
  async function save(restaurantId, score) {
    const { data } = await api.post("ratings/", {
      restaurant: restaurantId,
      score,
    });
    return data;
  }

  /** 특정 식당의 전체 별점 목록 조회 */
  async function listByRestaurant(restaurantId) {
    const { data } = await api.get("ratings/", {
      params: { restaurant_id: restaurantId },
    });
    return data;
  }

  /** 내가 준 별점 목록 조회 */
  async function myRatings() {
    const { data } = await api.get("ratings/");
    return data;
  }

  /** 별점 삭제 (ratingId 기준) */
  async function remove(ratingId) {
    await api.delete(`ratings/${ratingId}/`);
  }

  return { save, listByRestaurant, myRatings, remove };
})();


/* ── 별점 UI 바인딩 예시 ──────────────────────────────────────
 *
 * <div class="star-rating" data-restaurant-id="42">
 *   <span class="star" data-score="1">★</span>
 *   <span class="star" data-score="2">★</span>
 *   <span class="star" data-score="3">★</span>
 *   <span class="star" data-score="4">★</span>
 *   <span class="star" data-score="5">★</span>
 * </div>
 *
 * document.querySelectorAll(".star-rating").forEach((container) => {
 *   const restaurantId = container.dataset.restaurantId;
 *   container.querySelectorAll(".star").forEach((star) => {
 *     star.addEventListener("click", async () => {
 *       const score = Number(star.dataset.score);
 *       const result = await RatingAPI.save(restaurantId, score);
 *       console.log("저장된 별점:", result.score);
 *     });
 *   });
 * });
 */


/* ── 별점 UI 컴포넌트 ───────────────────────────────────────── */

const StarRating = (() => {
  const TOTAL = 5;

  /**
   * 별점 위젯 생성
   * container    : HTMLElement  — 위젯을 삽입할 요소
   * restaurantId : number|null  — 폼 모드일 때는 null
   * currentScore : number|null  — 현재 선택된 별점
   */
  function create(container, restaurantId, currentScore = null) {
    container.innerHTML = "";

    for (let score = 1; score <= TOTAL; score++) {
      const btn = document.createElement("button");
      btn.type          = "button";
      btn.className     = "star-btn";
      btn.dataset.score = score;
      btn.setAttribute("aria-label", `${score}점`);

      btn.addEventListener("mouseenter", () => _render(container, score));
      btn.addEventListener("mouseleave", () => _render(container, currentScore));
      btn.addEventListener("click",      () => _onSelect(container, restaurantId, score));

      container.appendChild(btn);
    }
    _render(container, currentScore);
  }

  // hover/선택 상태에 따라 ★/☆ 및 active 클래스 다시 그리기
  function _render(container, score) {
    container.querySelectorAll(".star-btn").forEach((btn) => {
      const filled = Number(btn.dataset.score) <= score;
      btn.textContent = filled ? "★" : "☆";
      btn.classList.toggle("active", filled);
    });
  }

  async function _onSelect(container, restaurantId, score) {
    // 폼 모드: hidden input에 값만 세팅하고 API 호출 안 함
    const formFieldId = container.dataset.formField;
    if (formFieldId) {
      const input = document.getElementById(formFieldId);
      if (input) input.value = score;
      create(container, null, score);
      return;
    }
    // API 모드: 서버에 저장
    const result = await RatingAPI.save(restaurantId, score);
    container.dataset.ratingId = result.id;
    create(container, restaurantId, result.score);
  }

  /**
   * 페이지 내 [data-rating] 속성이 붙은 요소를 자동 초기화
   *
   * API 모드:  <div data-rating data-restaurant-id="42" data-current-score="3"></div>
   * 폼 모드:   <div data-rating data-form-field="score-input" data-current-score="3"></div>
   *             + <input type="hidden" id="score-input" name="score">
   */
  function init() {
    document.querySelectorAll("[data-rating]").forEach((el) => {
      const restaurantId = Number(el.dataset.restaurantId) || null;
      const currentScore = Number(el.dataset.currentScore) || null;
      create(el, restaurantId, currentScore);
    });
  }

  return { init, create };
})();

document.addEventListener("DOMContentLoaded", () => StarRating.init());


/* ── CSS ─────────────────────────────────────────────────────
 *
 * .star-btn {
 *   background : none;
 *   border     : none;
 *   font-size  : 1.5rem;
 *   color      : #ccc;
 *   cursor     : pointer;
 *   padding    : 0 2px;
 *   transition : color 0.1s;
 * }
 * .star-btn.selected,
 * .star-btn.hovered {
 *   color : #f5a623;
 * }
 */
