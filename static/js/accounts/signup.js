(function () {
  'use strict';

  var SIGNUP_URL = '/accounts/api/ajax-signup/';

  var usernameEl  = document.getElementById('id_username');
  var password1El = document.getElementById('id_password1');
  var password2El = document.getElementById('id_password2');
  var signupBtn   = document.getElementById('btn-signup');

  // 에러 표시 헬퍼
  var fieldErrorMap = {
    username : 'err-username',
    password1: 'err-password1',
    password2: 'err-password2',
  };

  function clearErrors() {
    Object.values(fieldErrorMap).forEach(function (id) {
      var el = document.getElementById(id);
      if (el) { el.innerHTML = ''; el.style.display = 'none'; }
    });
    var box = document.getElementById('signup-error');
    if (box) box.style.display = 'none';
  }

  function showFieldErrors(errors) {
    Object.keys(errors).forEach(function (field) {
      var elId = fieldErrorMap[field];
      if (elId) {
        var ul = document.getElementById(elId);
        if (!ul) return;
        var msgs = errors[field];
        ul.innerHTML = msgs.map(function (m) {
          return '<li style="font-size:12px;color:var(--red);font-weight:700;">' + m + '</li>';
        }).join('');
        ul.style.display = 'block';
      }
    });
  }

  function showGlobalError(msg) {
    var box = document.getElementById('signup-error');
    if (!box) return;
    box.innerHTML = '<p style="font-size:12px;color:var(--red);font-weight:700;margin:0;">' + msg + '</p>';
    box.style.display = 'block';
  }

  function doSignup() {
    clearErrors();

    var username  = usernameEl  ? usernameEl.value.trim()  : '';
    var password1 = password1El ? password1El.value        : '';
    var password2 = password2El ? password2El.value        : '';

    if (!username || !password1 || !password2) {
      showGlobalError('모든 항목을 입력해주세요.');
      return;
    }

    signupBtn.disabled = true;

    axios.post(SIGNUP_URL, {
      username : username,
      password1: password1,
      password2: password2,
    }, {
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrf(),
      }
    })
      .then(function (resp) {
        window.location.href = resp.data.redirect || '/';
      })
      .catch(function (err) {
        signupBtn.disabled = false;
        if (err.response && err.response.data && err.response.data.errors) {
          showFieldErrors(err.response.data.errors);
        } else {
          var msg = (err.response && err.response.data && err.response.data.detail)
            ? err.response.data.detail
            : '가입 중 오류가 발생했습니다.';
          showGlobalError(msg);
        }
      });
  }

  if (signupBtn) signupBtn.addEventListener('click', doSignup);

  [usernameEl, password1El, password2El].forEach(function (el) {
    if (el) el.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') doSignup();
    });
  });
})();
