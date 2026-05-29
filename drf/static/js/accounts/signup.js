(function () {
  'use strict';

  var SIGNUP_URL = '/accounts/api/ajax-signup/';

  var usernameEl  = document.getElementById('id_username');
  var password1El = document.getElementById('id_password1');
  var password2El = document.getElementById('id_password2');
  var signupBtn   = document.getElementById('btn-signup');
  var checkBtn    = document.getElementById('btn-check-username');
  var msgEl       = document.getElementById('msg-username');

  /* ── 아이디 중복확인 ── */
  var usernameVerified = false;

  function setMsg(text, ok) {
    msgEl.textContent = text;
    msgEl.style.color = ok ? '#1a7a3e' : 'var(--red)';
    msgEl.style.display = 'block';
    usernameVerified = ok;
  }

  if (checkBtn) {
    checkBtn.addEventListener('click', function () {
      var v = usernameEl.value.trim();
      if (!v) { setMsg('아이디를 입력해주세요.', false); return; }
      if (v.length < 4 || v.length > 20 || !/^[a-zA-Z0-9_]+$/.test(v)) {
        setMsg('아이디 형식을 확인해주세요.', false); return;
      }
      checkBtn.disabled = true;
      checkBtn.textContent = '확인 중…';
      axios.get('/accounts/api/check-username/?username=' + encodeURIComponent(v))
        .then(function (res) { setMsg(res.data.detail, res.data.available); })
        .catch(function () { setMsg('확인 중 오류가 발생했습니다.', false); })
        .finally(function () {
          checkBtn.disabled = false;
          checkBtn.textContent = '중복확인';
        });
    });
  }

  if (usernameEl) {
    usernameEl.addEventListener('input', function () {
      usernameVerified = false;
      if (msgEl) msgEl.style.display = 'none';
      checkUsername();
    });
  }

  /* ── 실시간 유효성 표시 ── */
  function rule(ulId, ruleKey, pass) {
    var li = document.querySelector('#' + ulId + ' [data-rule="' + ruleKey + '"]');
    if (!li) return;
    li.classList.toggle('pass', pass);
    li.classList.toggle('fail', !pass);
  }

  function checkUsername() {
    var v = usernameEl ? usernameEl.value : '';
    rule('rules-username', 'len',  v.length >= 4 && v.length <= 20);
    rule('rules-username', 'char', v.length > 0 && /^[a-zA-Z0-9_]*$/.test(v));
  }

  function checkPassword() {
    var v = password1El ? password1El.value : '';
    rule('rules-password1', 'len',     v.length >= 8);
    rule('rules-password1', 'letter',  /[a-zA-Z]/.test(v));
    rule('rules-password1', 'digit',   /[0-9]/.test(v));
    rule('rules-password1', 'special', /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?`~]/.test(v));
    if (password2El && password2El.value.length > 0) checkConfirm();
  }

  function checkConfirm() {
    var v1 = password1El ? password1El.value : '';
    var v2 = password2El ? password2El.value : '';
    rule('rules-password2', 'match', v2 === v1 && v2.length > 0);
  }

  if (password1El) password1El.addEventListener('input', checkPassword);
  if (password2El) password2El.addEventListener('input', checkConfirm);

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

  /* ── 에러 표시 헬퍼 ── */
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
        ul.innerHTML = errors[field].map(function (m) {
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

  /* ── 가입 실행 ── */
  function doSignup() {
    clearErrors();
    var username  = usernameEl  ? usernameEl.value.trim() : '';
    var password1 = password1El ? password1El.value       : '';
    var password2 = password2El ? password2El.value       : '';

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
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() }
    })
      .then(function (resp) { window.location.href = resp.data.redirect || '/'; })
      .catch(function (err) {
        signupBtn.disabled = false;
        if (err.response && err.response.data && err.response.data.errors) {
          showFieldErrors(err.response.data.errors);
        } else {
          var msg = (err.response && err.response.data && err.response.data.detail)
            ? err.response.data.detail : '가입 중 오류가 발생했습니다.';
          showGlobalError(msg);
        }
      });
  }

  /* ── 가입 버튼: 중복확인 통과 여부 capture 단계에서 먼저 검사 ── */
  if (signupBtn) {
    signupBtn.addEventListener('click', function (e) {
      if (!usernameVerified) {
        if (msgEl) {
          msgEl.textContent = '아이디 중복확인을 완료해주세요.';
          msgEl.style.color = 'var(--red)';
          msgEl.style.display = 'block';
        }
        e.stopImmediatePropagation();
      }
    }, true);

    signupBtn.addEventListener('click', doSignup);
  }

  [usernameEl, password1El, password2El].forEach(function (el) {
    if (el) el.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') doSignup();
    });
  });
})();
