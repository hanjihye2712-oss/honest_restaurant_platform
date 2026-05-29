/**
 * 리뷰 섹션 — Axios 기반 CRUD (이미지 최대 3장)
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
    if (btn) {
      var action   = btn.dataset.action;
      var reviewId = btn.dataset.reviewId;
      if      (action === 'edit')        openEditForm(reviewId);
      else if (action === 'cancel-edit') closeEditForm(reviewId);
      else if (action === 'update')      handleUpdate(btn, reviewId);
      else if (action === 'delete')      handleDelete(reviewId);
    }
  });

  // ── 리뷰 등록 ─────────────────────────────────────────────────
  var submitBtn  = document.getElementById('btn-review-submit');
  var imageInput = document.getElementById('review-image-input');
  var previewArea = document.getElementById('review-image-previews');

  // 선택된 이미지 파일 목록 (최대 3장)
  var selectedFiles = [];

  function renderCreatePreviews() {
    if (!previewArea) return;
    previewArea.innerHTML = '';
    selectedFiles.forEach(function (file, idx) {
      var url = URL.createObjectURL(file);
      var wrap = document.createElement('div');
      wrap.className = 'review-preview-item';
      var img = document.createElement('img');
      img.src = url;
      img.onload = function () { URL.revokeObjectURL(url); };
      var rm = document.createElement('button');
      rm.type = 'button';
      rm.className = 'review-image-remove';
      rm.title = '사진 제거';
      rm.textContent = '✕';
      rm.addEventListener('click', function () {
        selectedFiles.splice(idx, 1);
        renderCreatePreviews();
      });
      wrap.appendChild(img);
      wrap.appendChild(rm);
      previewArea.appendChild(wrap);
    });
    previewArea.style.display = selectedFiles.length ? 'flex' : 'none';
  }

  if (imageInput) {
    imageInput.addEventListener('change', function () {
      var newFiles = Array.from(this.files);
      newFiles.forEach(function (f) {
        if (selectedFiles.length < 3) selectedFiles.push(f);
      });
      this.value = '';
      renderCreatePreviews();
    });
  }

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

      var fd = new FormData();
      fd.append('restaurant', restaurantId);
      fd.append('content', content);
      var fields = ['image', 'image_2', 'image_3'];
      selectedFiles.forEach(function (file, idx) {
        if (idx < 3) fd.append(fields[idx], file);
      });

      axios.post('/api/interactions/reviews/', fd, {
        headers: { 'X-CSRFToken': getCsrf() }
      })
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
          showAlert(msg);
          submitBtn.disabled = false;
        });
    });
  }

  // ── 수정 폼 열기 ───────────────────────────────────────────────
  // 수정 폼별 선택 이미지 (reviewId → File[])
  var editSelectedFiles = {};

  function openEditForm(id) {
    var view = document.querySelector('#review-' + id + ' .review-view');
    var form = document.getElementById('edit-form-' + id);
    if (!view || !form) return;

    view.style.display = 'none';
    form.style.display = 'block';

    editSelectedFiles[id] = editSelectedFiles[id] || [];
    bindEditImageInput(id);

    form.querySelectorAll('[data-rating]').forEach(function (el) {
      var score = Number(el.dataset.currentScore) || null;
      StarRating.create(el, null, score);
    });
  }

  function closeEditForm(id) {
    var form = document.getElementById('edit-form-' + id);
    var view = document.querySelector('#review-' + id + ' .review-view');
    if (form) form.style.display = 'none';
    if (view) view.style.display = 'block';
  }

  function bindEditImageInput(id) {
    var inp = document.getElementById('edit-image-' + id);
    if (!inp || inp._bound) return;
    inp._bound = true;
    inp.addEventListener('change', function () {
      var newFiles = Array.from(this.files);
      editSelectedFiles[id] = editSelectedFiles[id] || [];
      newFiles.forEach(function (f) {
        if (editSelectedFiles[id].length < 3) editSelectedFiles[id].push(f);
      });
      this.value = '';
      renderEditPreviews(id);
    });
  }

  function renderEditPreviews(id) {
    var area = document.getElementById('edit-image-previews-' + id);
    if (!area) return;
    area.innerHTML = '';
    var files = editSelectedFiles[id] || [];
    files.forEach(function (file, idx) {
      var url = URL.createObjectURL(file);
      var wrap = document.createElement('div');
      wrap.className = 'review-preview-item';
      var img = document.createElement('img');
      img.src = url;
      img.onload = function () { URL.revokeObjectURL(url); };
      var rm = document.createElement('button');
      rm.type = 'button';
      rm.className = 'review-image-remove';
      rm.title = '사진 제거';
      rm.textContent = '✕';
      rm.addEventListener('click', function () {
        editSelectedFiles[id].splice(idx, 1);
        renderEditPreviews(id);
      });
      wrap.appendChild(img);
      wrap.appendChild(rm);
      area.appendChild(wrap);
    });
    area.style.display = files.length ? 'flex' : 'none';
  }

  // ── 리뷰 수정 저장 ─────────────────────────────────────────────
  function handleUpdate(saveBtn, reviewId) {
    var scoreInput = document.getElementById('edit-score-' + reviewId);
    var contentEl  = document.getElementById('edit-content-' + reviewId);

    var score   = parseInt(scoreInput ? scoreInput.value : '', 10);
    var content = contentEl ? contentEl.value.trim() : '';

    if (!content) {
      showAlert('내용을 입력해주세요.');
      return;
    }

    saveBtn.disabled = true;

    var fd = new FormData();
    fd.append('content', content);

    // 기존 이미지 삭제 체크박스
    var clearFields = ['image', 'image_2', 'image_3'];
    clearFields.forEach(function (field, i) {
      var chk = document.getElementById('edit-image-clear-' + reviewId + '-' + (i + 1));
      if (chk && chk.checked) {
        fd.append(field, '');
      }
    });

    // 새로 선택한 이미지 (빈 슬롯에 순서대로 채움)
    var newFiles = editSelectedFiles[reviewId] || [];
    newFiles.forEach(function (file, idx) {
      if (idx < 3) fd.append(clearFields[idx], file);
    });

    axios.patch('/api/interactions/reviews/' + reviewId + '/', fd, {
      headers: { 'X-CSRFToken': getCsrf() }
    })
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
        showAlert(msg);
        saveBtn.disabled = false;
      });
  }

  // ── 리뷰 삭제 ──────────────────────────────────────────────────
  function handleDelete(reviewId) {
    showConfirm('정말 삭제하시겠습니까?\n리뷰, 별점, 영수증 인증이 모두 삭제됩니다.', function () {
    axios.post(
      '/api/interactions/restaurants/' + restaurantId + '/review/',
      JSON.stringify({ action: 'delete', review_id: reviewId }),
      {
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrf(),
          'X-Requested-With': 'XMLHttpRequest',
        }
      }
    )
      .then(function () {
        window.location.replace(window.location.pathname + '#review-section');
      })
      .catch(function (err) {
        console.error(err);
        var status = err.response ? err.response.status : 'network';
        var msg = (err.response && err.response.data && err.response.data.detail)
          ? err.response.data.detail
          : '삭제 중 오류가 발생했습니다. (' + status + ')';
        showAlert(msg);
      });
    }); // showConfirm
  }

})();
