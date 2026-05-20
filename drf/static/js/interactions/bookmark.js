/**
 * 북마크 API
 *
 * 의존: api.js (axios 인스턴스 `api`)
 *
 * 사용 예)
 *   BookmarkAPI.toggle(restaurantId)
 *   BookmarkAPI.list()
 *   BookmarkAPI.remove(bookmarkId)
 */

const BookmarkAPI = (() => {
  /** 북마크 토글 (추가 ↔ 취소) */
  async function toggle(restaurantId) {
    const { data } = await api.post("bookmarks/toggle/", { restaurant: restaurantId });
    return data; // { bookmarked: true|false, id? }
  }

  /** 내 북마크 목록 조회 */
  async function list() {
    const { data } = await api.get("bookmarks/");
    return data;
  }

  /** 북마크 직접 삭제 (bookmarkId 기준) */
  async function remove(bookmarkId) {
    await api.delete(`bookmarks/${bookmarkId}/`);
  }

  return { toggle, list, remove };
})();


/* ── 하트 버튼 UI ─────────────────────────────────────────────
 *
 * HTML:
 *   <div class="heart-wrap" id="heart-wrap" data-label="저장하기">
 *     <button class="btn-heart" id="btn-bookmark" data-restaurant-id="42">♡</button>
 *   </div>
 */

document.addEventListener('DOMContentLoaded', function () {
  var btn  = document.getElementById('btn-bookmark');
  var wrap = document.getElementById('heart-wrap');
  if (!btn) return;

  btn.addEventListener('click', async function () {
    var result = await BookmarkAPI.toggle(btn.dataset.restaurantId);
    if (result.bookmarked) {
      btn.classList.add('bookmarked');
      btn.classList.remove('no-hover');
      if (wrap) wrap.dataset.label = '저장 취소하기';
    } else {
      btn.classList.remove('bookmarked');
      btn.classList.add('no-hover');
      btn.addEventListener('mouseleave', function onLeave() {
        btn.classList.remove('no-hover');
        btn.removeEventListener('mouseleave', onLeave);
      });
      if (wrap) wrap.dataset.label = '저장하기';
    }
    // 클릭 직후 툴팁 숨김 — 마우스가 떠났다 돌아올 때만 표시
    if (wrap) {
      wrap.classList.add('no-tooltip');
      wrap.addEventListener('mouseleave', function onLeave() {
        wrap.classList.remove('no-tooltip');
        wrap.removeEventListener('mouseleave', onLeave);
      });
    }
  });
});
