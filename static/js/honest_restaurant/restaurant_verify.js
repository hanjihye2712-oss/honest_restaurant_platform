(function () {
  'use strict';

  var fileInput  = document.getElementById('id_receipt_image');
  var submitBtn  = document.getElementById('verify-submit-btn');
  var errorDiv   = document.getElementById('verify-error');
  var wrap       = document.querySelector('.verify-center-wrap');

  if (!fileInput || !submitBtn || !wrap) return;

  var submitUrl = wrap.dataset.submitUrl;

  // ── 파일 선택 시 미리보기 ───────────────────────────────────
  fileInput.addEventListener('change', function () {
    if (!this.files || !this.files[0]) return;
    var file = this.files[0];
    var title = document.getElementById('upload-title');
    var sub   = document.getElementById('upload-sub');
    if (title) title.textContent = file.name;
    if (sub)   sub.textContent   = (file.size / 1024 / 1024).toFixed(1) + 'MB';
  });

  // ── 인증 제출 ────────────────────────────────────────────────
  submitBtn.addEventListener('click', function () {
    if (!fileInput.files || !fileInput.files[0]) {
      showError('영수증 이미지를 선택해주세요.');
      return;
    }

    var formData = new FormData();
    formData.append('receipt_image', fileInput.files[0]);

    submitBtn.disabled = true;

    axios.post(submitUrl, formData, {
      headers: {
        'X-CSRFToken': getCsrf(),
        'X-Requested-With': 'XMLHttpRequest',
      }
    })
      .then(function (resp) {
        window.location.href = resp.data.redirect;
      })
      .catch(function (err) {
        submitBtn.disabled = false;
        if (err.response && err.response.data && err.response.data.errors) {
          var msgs = Object.values(err.response.data.errors).join(' ');
          showError(msgs);
        } else {
          showError('업로드 중 오류가 발생했습니다.');
        }
      });
  });

  function showError(msg) {
    if (!errorDiv) return;
    errorDiv.textContent = msg;
    errorDiv.style.display = 'block';
  }
})();
