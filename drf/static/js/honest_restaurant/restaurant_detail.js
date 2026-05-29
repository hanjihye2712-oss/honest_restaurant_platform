// ── 미디어 슬라이더 ───────────────────────────────────────────────────────────
var _slideIdx = 0;

function slideMedia(dir) {
  var slides = document.querySelectorAll('.media-slide');
  var total  = slides.length;
  if (total <= 1) return;
  slides[_slideIdx].classList.remove('active');
  _slideIdx = (_slideIdx + dir + total) % total;
  slides[_slideIdx].classList.add('active');
  var counter = document.getElementById('sliderCounter');
  if (counter) counter.textContent = (_slideIdx + 1) + ' / ' + total;
}

document.addEventListener('DOMContentLoaded', function () {

  // ── 슬라이더 초기화 ─────────────────────────────────────────
  var slides = document.querySelectorAll('.media-slide');
  if (slides.length > 0) slides[0].classList.add('active');

  // ── 업로드/삭제 후 스크롤 복원 ─────────────────────────────
  var scrollTarget = sessionStorage.getItem('scrollTo');
  if (scrollTarget) {
    sessionStorage.removeItem('scrollTo');
    var targetEl = document.getElementById(scrollTarget);
    if (targetEl) {
      setTimeout(function () {
        var top = targetEl.getBoundingClientRect().top + window.scrollY - 100;
        window.scrollTo({ top: top, behavior: 'smooth' });
      }, 100);
    }
  }

  // ── 미디어 삭제 (Axios) ─────────────────────────────────────
  document.querySelectorAll('.media-delete-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var url = this.dataset.deleteUrl;
      showConfirm('정말 삭제하시겠습니까?', function () {
        btn.disabled = true;
        axios.post(url, null, {
          headers: {
            'X-CSRFToken': getCsrf(),
            'X-Requested-With': 'XMLHttpRequest',
          }
        })
        .then(function () {
          window.location.href = window.location.pathname;
        })
        .catch(function () {
          showAlert('삭제 중 오류가 발생했습니다.');
          btn.disabled = false;
        });
      }); // showConfirm
    });
  });

  // ── 미디어 업로드 (Axios) ───────────────────────────────────
  document.querySelectorAll('.media-file-input').forEach(function (input) {
    input.addEventListener('change', function () {
      var files = Array.from(this.files || []);
      if (!files.length) return;

      var url = this.dataset.uploadUrl;
      input.disabled = true;

      // 파일을 순서대로 하나씩 업로드
      files.reduce(function (chain, file) {
        return chain.then(function () {
          var fd = new FormData();
          fd.append('file', file);
          return axios.post(url, fd, {
            headers: {
              'X-CSRFToken': getCsrf(),
              'X-Requested-With': 'XMLHttpRequest',
            }
          });
        });
      }, Promise.resolve())
        .then(function () {
          window.location.href = window.location.pathname;
        })
        .catch(function () {
          showAlert('업로드 중 오류가 발생했습니다.');
          input.disabled = false;
        });
    });
  });

  // ── 메뉴 페이지 넘기기 (5개씩 좌/우) ───────────────────────────
  var _menuPage  = 0;
  var PAGE_SIZE  = 7;

  function initMenuPager() {
    var posterRows = document.getElementById('menu-poster-rows');
    var pager      = document.getElementById('mp-pager');
    var prevBtn    = document.getElementById('mp-prev');
    var nextBtn    = document.getElementById('mp-next');
    var counter    = document.getElementById('mp-page-counter');
    if (!posterRows || !pager) return;

    var rows       = Array.from(posterRows.querySelectorAll('.mp-row'));
    var totalPages = Math.ceil(rows.length / PAGE_SIZE) || 1;
    _menuPage      = 0;

    function renderPage(page) {
      rows.forEach(function (row, idx) {
        row.style.display = (Math.floor(idx / PAGE_SIZE) === page) ? '' : 'none';
      });
      if (counter) counter.textContent = (page + 1) + ' / ' + totalPages;
      if (prevBtn)  prevBtn.disabled   = (page === 0);
      if (nextBtn)  nextBtn.disabled   = (page === totalPages - 1);
    }

    if (totalPages <= 1) {
      pager.style.display = 'none';
      rows.forEach(function (r) { r.style.display = ''; });
      return;
    }

    pager.style.display = 'flex';

    prevBtn.onclick = function () {
      if (_menuPage > 0) { _menuPage--; renderPage(_menuPage); }
    };
    nextBtn.onclick = function () {
      if (_menuPage < totalPages - 1) { _menuPage++; renderPage(_menuPage); }
    };

    renderPage(0);
  }

  initMenuPager();
  document.addEventListener('menu-poster-updated', initMenuPager);

  // ── 사진 앨범 (4×2 페이지 넘기기 + 라이트박스) ───────────────────
  (function () {
    var items        = Array.from(document.querySelectorAll('.dp-album-item'));
    var placeholders = Array.from(document.querySelectorAll('.dp-album-placeholder'));
    var lightbox = document.getElementById('dp-lightbox');
    var lbImg    = document.getElementById('dp-lb-img');
    var lbBg     = document.getElementById('dp-lightbox-bg');
    var lbClose  = document.getElementById('dp-lb-close');
    var lbPrev   = document.getElementById('dp-lb-prev');
    var lbNext   = document.getElementById('dp-lb-next');
    var nav      = document.getElementById('dp-album-nav');
    var prevBtn  = document.getElementById('dp-album-prev');
    var nextBtn  = document.getElementById('dp-album-next');
    var counter  = document.getElementById('dp-album-counter');

    var PER_PAGE   = 8; // 4열 × 2행
    var totalPages = Math.ceil(items.length / PER_PAGE) || 1;
    var albumPage  = 0;
    var srcs       = items.map(function (el) { return el.dataset.src; });
    var lbCurrent  = 0;

    // ── 앨범 페이지 렌더 ─────────────────────
    function renderAlbumPage(page) {
      items.forEach(function (item, idx) {
        item.style.display = Math.floor(idx / PER_PAGE) === page ? '' : 'none';
      });
      // 현재 페이지의 빈 슬롯만큼 placeholder 표시
      var startIdx    = page * PER_PAGE;
      var realOnPage  = Math.min(startIdx + PER_PAGE, items.length) - startIdx;
      var showPh      = Math.max(0, PER_PAGE - realOnPage);
      placeholders.forEach(function (p, i) {
        p.style.display = i < showPh ? '' : 'none';
      });
      if (counter) counter.textContent = (page + 1) + ' / ' + totalPages;
      if (prevBtn)  prevBtn.disabled   = (page === 0);
      if (nextBtn)  nextBtn.disabled   = (page === totalPages - 1);
    }

    if (totalPages > 1 && nav) {
      nav.style.display = 'flex';
      prevBtn.addEventListener('click', function () {
        if (albumPage > 0) { albumPage--; renderAlbumPage(albumPage); }
      });
      nextBtn.addEventListener('click', function () {
        if (albumPage < totalPages - 1) { albumPage++; renderAlbumPage(albumPage); }
      });
    }
    renderAlbumPage(0);

    // ── 라이트박스 (이미지 없으면 스킵) ─────
    if (!items.length || !lightbox) return;

    function openAt(idx) {
      lbCurrent = (idx + srcs.length) % srcs.length;
      lbImg.src = srcs[lbCurrent];
      lightbox.style.display = 'flex';
      document.body.style.overflow = 'hidden';
      lbPrev.style.display = srcs.length > 1 ? '' : 'none';
      lbNext.style.display = srcs.length > 1 ? '' : 'none';
    }
    function closeLb() {
      lightbox.style.display = 'none';
      document.body.style.overflow = '';
    }

    items.forEach(function (el, i) {
      el.addEventListener('click', function () { openAt(i); });
    });
    lbClose.addEventListener('click', closeLb);
    lbBg.addEventListener('click', closeLb);
    lbPrev.addEventListener('click', function () { openAt(lbCurrent - 1); });
    lbNext.addEventListener('click', function () { openAt(lbCurrent + 1); });
    document.addEventListener('keydown', function (e) {
      if (lightbox.style.display === 'none') return;
      if (e.key === 'ArrowLeft')  openAt(lbCurrent - 1);
      if (e.key === 'ArrowRight') openAt(lbCurrent + 1);
      if (e.key === 'Escape')     closeLb();
    });
  }());

  // ── 주소 / 전화번호 인라인 편집 ────────────────────────────────
  var dpBody       = document.getElementById('dp-body');
  var btnInfoEdit  = document.getElementById('btn-info-edit');

  if (dpBody && btnInfoEdit) {
    var dpBodyView    = document.getElementById('dp-body-view');
    var dpEditOverlay = document.getElementById('dp-edit-overlay');

    btnInfoEdit.addEventListener('click', enterInfoEdit);

    function enterInfoEdit() {
      var road  = dpBody.dataset.road;
      var jibun = dpBody.dataset.jibun;
      var phone = dpBody.dataset.phone;

      dpBodyView.style.display    = 'none';
      dpEditOverlay.style.display = 'none';
      dpBody.style.cursor         = 'default';

      var editDiv = document.createElement('div');
      editDiv.id        = 'dp-edit-form';
      editDiv.className = 'info-edit-form';
      editDiv.innerHTML =
        '<label class="info-edit-label"><span>도로명주소</span>' +
          '<input id="ie-road" class="info-edit-input" type="text" value="' + esc(road) + '" placeholder="도로명 주소"></label>' +
        '<label class="info-edit-label"><span>지번주소</span>' +
          '<input id="ie-jibun" class="info-edit-input" type="text" value="' + esc(jibun) + '" placeholder="지번 주소"></label>' +
        '<label class="info-edit-label"><span>전화번호</span>' +
          '<input id="ie-phone" class="info-edit-input" type="tel" value="' + esc(phone) + '" placeholder="예: 061-334-6788"></label>' +
        '<div class="info-edit-actions">' +
          '<button type="button" id="btn-info-save" class="info-save-btn">저장</button>' +
          '<button type="button" id="btn-info-cancel" class="info-cancel-btn">취소</button>' +
        '</div>';

      dpBody.insertBefore(editDiv, dpEditOverlay);
      document.getElementById('ie-road').focus();

      document.getElementById('btn-info-cancel').addEventListener('click', exitInfoEdit);
      document.getElementById('btn-info-save').addEventListener('click', saveInfoEdit);
    }

    function exitInfoEdit() {
      var editDiv = document.getElementById('dp-edit-form');
      if (editDiv) editDiv.remove();
      dpBodyView.style.display    = '';
      dpEditOverlay.style.display = '';
      dpBody.style.cursor         = '';
    }

    function saveInfoEdit() {
      var saveBtn = document.getElementById('btn-info-save');
      var road    = document.getElementById('ie-road').value.trim();
      var jibun   = document.getElementById('ie-jibun').value.trim();
      var phone   = document.getElementById('ie-phone').value.trim();

      saveBtn.disabled    = true;
      saveBtn.textContent = '저장 중…';

      var body = new URLSearchParams();
      body.append('address_road',  road);
      body.append('address_jibun', jibun);
      body.append('phone',         phone);

      axios.post(dpBody.dataset.updateUrl, body.toString(), {
        headers: {
          'Content-Type'     : 'application/x-www-form-urlencoded',
          'X-CSRFToken'      : getCsrf(),
          'X-Requested-With' : 'XMLHttpRequest',
        }
      })
      .then(function (res) {
        var d = res.data;
        dpBody.dataset.road  = d.address_road;
        dpBody.dataset.jibun = d.address_jibun;
        dpBody.dataset.phone = d.phone;

        var html = '';
        if (d.address_road)  html += '<strong>도로명</strong> ' + escHtml(d.address_road)  + '<br>';
        if (d.address_jibun) html += '<strong>지번</strong> '   + escHtml(d.address_jibun) + '<br>';
        html += '<strong>전화</strong> ';
        if (d.phone) {
          html += '<a href="tel:' + esc(d.phone) + '" style="color:var(--navy);font-weight:700;">' + escHtml(d.phone) + '</a><br>';
        } else {
          html += '-<br>';
        }
        dpBodyView.innerHTML = html;
        exitInfoEdit();
      })
      .catch(function (err) {
        var msg = '저장 중 오류가 발생했습니다.';
        if (err.response && err.response.data && err.response.data.errors) {
          msg = Object.values(err.response.data.errors).flat().join('\n');
        }
        showAlert(msg);
        saveBtn.disabled    = false;
        saveBtn.textContent = '저장';
      });
    }

    function escHtml(s) {
      return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }
    function esc(s) { return escHtml(s); }
  }

  // ── 리뷰 미작성 시 페이지 이탈 → 영수증 인증 취소 ───────────
  var meta = document.getElementById('detail-meta');
  if (meta && meta.dataset.canWrite === 'true' && meta.dataset.hasReview !== 'true') {
    var cancelUrl = meta.dataset.cancelUrl;

    // review_section.js 에서 성공 시 window._reviewSubmitting = true 로 세팅됨
    window._reviewSubmitting = false;

    window.addEventListener('beforeunload', function () {
      if (window._reviewSubmitting) return;
      var data = new FormData();
      data.append('csrfmiddlewaretoken', getCsrf());
      navigator.sendBeacon(cancelUrl, data);
    });
  }

  // ── 한줄 소개 편집 ─────────────────────────────────────────
  var pullWrap     = document.getElementById('dp-pull-wrap');
  if (pullWrap) {
    var taglineUrl  = pullWrap.dataset.taglineUrl;
    var pullText    = document.getElementById('dp-pull-text');
    var pullEditor  = document.getElementById('dp-pull-editor');
    var pullTA      = document.getElementById('dp-pull-textarea');
    var btnEdit     = document.getElementById('btn-tagline-edit');
    var btnRegen    = document.getElementById('btn-tagline-regen');
    var btnSave     = document.getElementById('btn-tagline-save');
    var btnCancel   = document.getElementById('btn-tagline-cancel');

    var pullOverlay = pullWrap.querySelector('.dp-pull-edit-overlay');

    function showEditor() {
      pullTA.value = pullText.textContent.replace(/^"|"$/g, '');
      pullText.style.display = 'none';
      if (pullOverlay) pullOverlay.style.display = 'none';
      pullEditor.style.display = 'block';
      pullTA.focus();
    }

    function hideEditor() {
      pullEditor.style.display = 'none';
      pullText.style.display = '';
      if (pullOverlay) pullOverlay.style.display = '';
    }

    btnEdit.addEventListener('click', showEditor);
    btnCancel.addEventListener('click', hideEditor);

    btnSave.addEventListener('click', function () {
      var val = pullTA.value.trim();
      if (!val) return;
      btnSave.disabled = true;
      axios.post(taglineUrl, { tagline: val }, {
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() }
      }).then(function (res) {
        pullText.textContent = '"' + res.data.tagline + '"';
        hideEditor();
      }).catch(function () {
        showAlert('저장 중 오류가 발생했습니다.');
      }).finally(function () {
        btnSave.disabled = false;
      });
    });

    btnRegen.addEventListener('click', function () {
      btnRegen.disabled = true;
      btnRegen.textContent = '생성 중…';
      axios.get(taglineUrl + '?regen=1', {
        headers: { 'X-CSRFToken': getCsrf() }
      }).then(function (res) {
        pullTA.value = res.data.tagline;
      }).catch(function () {
        showAlert('자동 생성 중 오류가 발생했습니다.');
      }).finally(function () {
        btnRegen.disabled = false;
        btnRegen.textContent = '↺ AI 생성';
      });
    });
  }

});

// ── 앵커 스크롤 오프셋 ────────────────────────────────────────────────────────
var _hash = window.location.hash;
if (_hash === '#review-section' || _hash === '#media-slider') {
  history.scrollRestoration = 'manual';
  window.scrollTo(0, 0);
  window.addEventListener('load', function () {
    setTimeout(function () {
      var targetId = _hash === '#media-slider' ? 'media-slider' : 'review-section';
      var el = document.getElementById(targetId);
      if (el) {
        var top = el.getBoundingClientRect().top + window.scrollY - 100;
        window.scrollTo({ top: top, behavior: 'smooth' });
      }
    }, 50);
  });
}
