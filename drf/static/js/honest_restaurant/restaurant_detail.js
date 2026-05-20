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
      if (!confirm('정말 삭제하시겠습니까?')) return;

      var url = this.dataset.deleteUrl;
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
          alert('삭제 중 오류가 발생했습니다.');
          btn.disabled = false;
        });
    });
  });

  // ── 미디어 업로드 (Axios) ───────────────────────────────────
  document.querySelectorAll('.media-file-input').forEach(function (input) {
    input.addEventListener('change', function () {
      if (!this.files || !this.files[0]) return;

      var formData = new FormData();
      formData.append('file', this.files[0]);
      var url = this.dataset.uploadUrl;

      axios.post(url, formData, {
        headers: {
          'X-CSRFToken': getCsrf(),
          'X-Requested-With': 'XMLHttpRequest',
        }
      })
        .then(function () {
          window.location.href = window.location.pathname;
        })
        .catch(function () { alert('업로드 중 오류가 발생했습니다.'); });
    });
  });

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
