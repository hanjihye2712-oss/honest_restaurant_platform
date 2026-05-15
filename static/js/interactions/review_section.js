/**
 * 리뷰 섹션 — Axios 기반 CRUD
 * 의존: api.js (axios 인스턴스 `api`), rating.js (StarRating)
 */
(function () {
  'use strict';

  var section = document.getElementById('review-section');
  if (!section) return;

  var restaurantId = section.dataset.restaurantId;

  // ── 이벤트 위임 (수정 열기/닫기, 저장, 삭제) ─────────────────
  section.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-action]');
    if (!btn) return;

    var action    = btn.dataset.action;
    var reviewId  = btn.dataset.reviewId;

    if      (action === 'edit')        openEditForm(reviewId);
    else if (action === 'cancel-edit') closeEditForm(reviewId);
    else if (action === 'update')      handleUpdate(btn, reviewId);
    else if (action === 'delete')      handleDelete(reviewId);
  });

  // ── 리뷰 등록 ────────────────────────────────────────────────
  var submitBtn = document.getElementById('btn-review-submit');
  if (submitBtn) {
    submitBtn.addEventListener('click', function () {
      var scoreInput   = document.getElementById('score-input');
      var contentEl    = document.getElementById('review-content');
      var scoreError   = document.getElementById('score-error');
      var contentError = document.getElementById('content-error');

      var score   = parseInt(scoreInput ? scoreInput.value : '', 10);
      var content = contentEl ? contentEl.value.trim() : '';
      var valid   = true;

      if (!score || score < 1 || score > 5) {
        scoreError.style.display = 'block';
        valid = false;
      } else {
        scoreError.style.display = 'none';
      }

      if (!content) {
        contentError.style.display = 'block';
        valid = false;
      } else {
        contentError.style.display = 'none';
      }

      if (!valid) return;

      submitBtn.disabled = true;

      api.post('reviews/', { restaurant: restaurantId, content: content })
        .then(function () {
          return api.post('ratings/', { restaurant: restaurantId, score: score });
        })
        .then(function () {
          window._reviewSubmitting = true;
          window.location.replace(
            window.location.pathname + '?sort=latest#review-section'
          );
        })
        .catch(function (err) {
          console.error(err);
          var msg = (err.response && err.response.data && err.response.data.detail)
            ? err.response.data.detail
            : '등록 중 오류가 발생했습니다.';
          alert(msg);
          submitBtn.disabled = false;
        });
    });
  }

  // ── 수정 폼 열기 ─────────────────────────────────────────────
  function openEditForm(id) {
    var view = document.querySelector('#review-' + id + ' .review-view');
    var form = document.getElementById('edit-form-' + id);
    if (!view || !form) return;

    view.style.display = 'none';
    form.style.display = 'block';

    // 별점 위젯 재초기화 (현재 점수 기준)
    form.querySelectorAll('[data-rating]').forEach(function (el) {
      var score = Number(el.dataset.currentScore) || null;
      StarRating.create(el, null, score);
    });
  }

  // ── 수정 폼 닫기 ─────────────────────────────────────────────
  function closeEditForm(id) {
    var form = document.getElementById('edit-form-' + id);
    var view = document.querySelector('#review-' + id + ' .review-view');
    if (form) form.style.display = 'none';
    if (view) view.style.display = 'block';
  }

  // ── 리뷰 수정 저장 (SQLite 동시쓰기 방지를 위해 순차 실행) ──────
  function handleUpdate(saveBtn, reviewId) {
    var scoreInput = document.getElementById('edit-score-' + reviewId);
    var contentEl  = document.getElementById('edit-content-' + reviewId);

    var score   = parseInt(scoreInput ? scoreInput.value : '', 10);
    var content = contentEl ? contentEl.value.trim() : '';

    if (!content) {
      alert('내용을 입력해주세요.');
      return;
    }

    saveBtn.disabled = true;

    api.patch('reviews/' + reviewId + '/', { content: content })
      .then(function () {
        if (score >= 1 && score <= 5) {
          return api.post('ratings/', { restaurant: restaurantId, score: score });
        }
        return Promise.resolve();
      })
      .then(function () {
        window.location.reload();
      })
      .catch(function (err) {
        console.error(err);
        var msg = (err.response && err.response.data && err.response.data.detail)
          ? err.response.data.detail
          : '수정 중 오류가 발생했습니다.';
        alert(msg);
        saveBtn.disabled = false;
      });
  }

  // ── 리뷰 삭제 ────────────────────────────────────────────────
  function handleDelete(reviewId) {
    if (!confirm('정말 삭제하시겠습니까?\n리뷰, 별점, 영수증 인증이 모두 삭제됩니다.')) return;

    api.post('restaurants/' + restaurantId + '/review/', {
      action: 'delete',
      review_id: reviewId,
    })
      .then(function () {
        window.location.replace(window.location.pathname + '#review-section');
      })
      .catch(function (err) {
        console.error(err);
        alert('삭제 중 오류가 발생했습니다.');
      });
  }

})();
