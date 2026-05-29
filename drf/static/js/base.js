/* ── 맨 위로 버튼 ── */
(function () {
  'use strict';

  var btn = document.getElementById('scroll-top-btn');
  if (!btn) return;

  window.addEventListener('scroll', function () {
    btn.classList.toggle('visible', window.scrollY > 300);
  }, { passive: true });

  btn.addEventListener('click', function () {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
}());

/* ── 전역 커스텀 모달 (showAlert / showConfirm) ── */
(function () {
  'use strict';

  var overlay   = document.getElementById('g-modal-overlay');
  var msgEl     = document.getElementById('g-modal-msg');
  var okBtn     = document.getElementById('g-modal-ok');
  var cancelBtn = document.getElementById('g-modal-cancel');
  var _ok = null, _cancel = null;

  function close() {
    overlay.style.display = 'none';
    cancelBtn.style.display = 'none';
  }

  okBtn.addEventListener('click', function () {
    close();
    if (_ok) { var cb = _ok; _ok = null; cb(); }
  });

  cancelBtn.addEventListener('click', function () {
    close();
    if (_cancel) { var cb = _cancel; _cancel = null; cb(); }
  });

  window.showAlert = function (msg, callback) {
    msgEl.textContent = msg;
    cancelBtn.style.display = 'none';
    overlay.style.display = 'flex';
    _ok = callback || null;
    _cancel = null;
    okBtn.focus();
  };

  window.showConfirm = function (msg, onOk, onCancel) {
    msgEl.textContent = msg;
    cancelBtn.style.display = 'inline-block';
    overlay.style.display = 'flex';
    _ok = onOk || null;
    _cancel = onCancel || null;
    cancelBtn.focus();
  };
}());
