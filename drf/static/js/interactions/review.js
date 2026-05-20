/**
 * 리뷰 API
 *
 * 의존: api.js (axios 인스턴스 `api`)
 *
 * 사용 예)
 *   ReviewAPI.create(restaurantId, "맛있어요!")
 *   ReviewAPI.update(reviewId, "더 맛있어요!")
 *   ReviewAPI.listByRestaurant(restaurantId)
 *   ReviewAPI.remove(reviewId)
 */

const ReviewAPI = (() => {
  /** 리뷰 작성 (식당당 1개) */
  async function create(restaurantId, content) {
    const { data } = await api.post("reviews/", {
      restaurant: restaurantId,
      content,
    });
    return data;
  }

  /** 리뷰 수정 (내 리뷰만) */
  async function update(reviewId, content) {
    const { data } = await api.patch(`reviews/${reviewId}/`, { content });
    return data;
  }

  /** 특정 식당의 리뷰 목록 조회 */
  async function listByRestaurant(restaurantId) {
    const { data } = await api.get("reviews/", {
      params: { restaurant_id: restaurantId },
    });
    return data;
  }

  /** 내 리뷰 목록 조회 */
  async function myReviews() {
    const { data } = await api.get("reviews/");
    return data;
  }

  /** 리뷰 삭제 (내 리뷰만) */
  async function remove(reviewId) {
    await api.delete(`reviews/${reviewId}/`);
  }

  return { create, update, listByRestaurant, myReviews, remove };
})();


/* ── 리뷰 폼 바인딩 예시 ──────────────────────────────────────
 *
 * <form id="review-form" data-restaurant-id="42">
 *   <textarea id="review-content" placeholder="리뷰를 작성하세요"></textarea>
 *   <button type="submit">등록</button>
 * </form>
 * <ul id="review-list"></ul>
 *
 * const form = document.getElementById("review-form");
 * const restaurantId = form.dataset.restaurantId;
 *
 * // 기존 리뷰 로드
 * ReviewAPI.listByRestaurant(restaurantId).then((reviews) => {
 *   const list = document.getElementById("review-list");
 *   list.innerHTML = reviews.map((r) =>
 *     `<li data-id="${r.id}"><b>${r.username}</b>: ${r.content}</li>`
 *   ).join("");
 * });
 *
 * // 리뷰 등록
 * form.addEventListener("submit", async (e) => {
 *   e.preventDefault();
 *   const content = document.getElementById("review-content").value.trim();
 *   if (!content) return;
 *   await ReviewAPI.create(restaurantId, content);
 *   location.reload();
 * });
 */
