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

  /* ── 눈 아이콘: 클릭 시 2초 표시 후 자동 숨김 ── */
  var EYE_OPEN   = '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>';
  var EYE_CLOSED = '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>'
    + '<path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>'
    + '<line x1="1" y1="1" x2="23" y2="23"/>';

  document.querySelectorAll('.btn-eye').forEach(function (btn) {
    var timer = null;
    btn.addEventListener('click', function () {
      var inp = document.getElementById(btn.dataset.target);
      if (!inp) return;
      var svg = btn.querySelector('svg');
      if (inp.type === 'text') {
        clearTimeout(timer);
        inp.type = 'password';
        svg.innerHTML = EYE_OPEN;
        return;
      }
      inp.type = 'text';
      svg.innerHTML = EYE_CLOSED;
      timer = setTimeout(function () {
        inp.type = 'password';
        svg.innerHTML = EYE_OPEN;
      }, 2000);
    });
  });
})();
