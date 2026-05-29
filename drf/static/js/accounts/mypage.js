(function () {
  'use strict';

  var overlay = document.getElementById('modal-edit-profile');
  var btnOpen = document.getElementById('btn-edit-profile');
  var btnClose = document.getElementById('btn-modal-close');
  var alertEl = document.getElementById('mp-alert');
  var form    = document.getElementById('form-edit-profile');

  if (!overlay || !form) return;

  btnOpen.addEventListener('click', function () { overlay.classList.add('open'); });
  btnClose.addEventListener('click', function () { overlay.classList.remove('open'); });
  overlay.addEventListener('click', function (e) {
    if (e.target === overlay) overlay.classList.remove('open');
  });

  function showAlert(msg, type) {
    alertEl.textContent = msg;
    alertEl.className = 'mp-alert ' + type;
    alertEl.style.display = 'block';
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var data = {
      first_name: form.querySelector('[name="first_name"]').value.trim(),
      email:      form.querySelector('[name="email"]').value.trim(),
    };
    axios.patch('/accounts/api/me/update/', data, {
      headers: { 'X-CSRFToken': form.querySelector('[name="csrfmiddlewaretoken"]').value }
    })
      .then(function () {
        showAlert('저장되었습니다.', 'success');
        setTimeout(function () { location.reload(); }, 800);
      })
      .catch(function (err) {
        var msg = (err.response && err.response.data && err.response.data.detail)
          || '저장 중 오류가 발생했습니다.';
        showAlert(msg, 'error');
      });
  });
})();
