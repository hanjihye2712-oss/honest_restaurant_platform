(function () {
  'use strict';

  var meta      = document.getElementById('login-meta');
  var loginUrl  = meta ? meta.dataset.loginUrl  : '/accounts/api/ajax-login/';
  var nextUrl   = meta ? meta.dataset.next       : '/';

  var usernameEl = document.getElementById('id_username');
  var passwordEl = document.getElementById('id_password');
  var loginBtn   = document.getElementById('btn-login');
  var errorBox   = document.getElementById('login-error');

  function showError(msg) {
    if (!errorBox) return;
    errorBox.querySelector('p').textContent = msg;
    errorBox.style.display = 'block';
  }

  function clearError() {
    if (errorBox) errorBox.style.display = 'none';
  }

  function doLogin() {
    clearError();

    var username = usernameEl ? usernameEl.value.trim() : '';
    var password = passwordEl ? passwordEl.value       : '';

    if (!username || !password) {
      showError('아이디와 비밀번호를 입력하세요.');
      return;
    }

    loginBtn.disabled = true;

    axios.post(loginUrl, { username: username, password: password, next: nextUrl }, {
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrf(),
      }
    })
      .then(function (resp) {
        window.location.href = resp.data.redirect || '/';
      })
      .catch(function (err) {
        loginBtn.disabled = false;
        var msg = (err.response && err.response.data && err.response.data.detail)
          ? err.response.data.detail
          : '로그인 중 오류가 발생했습니다.';
        showError(msg);
      });
  }

  if (loginBtn) loginBtn.addEventListener('click', doLogin);

  [usernameEl, passwordEl].forEach(function (el) {
    if (el) el.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') doLogin();
    });
  });
})();
