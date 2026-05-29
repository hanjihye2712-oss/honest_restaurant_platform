(function () {
  'use strict';

  var p1El = document.getElementById('id_password1');
  var p2El = document.getElementById('id_password2');

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

  function rule(ulId, ruleKey, pass) {
    var li = document.querySelector('#' + ulId + ' [data-rule="' + ruleKey + '"]');
    if (!li) return;
    li.classList.toggle('pass', pass);
    li.classList.toggle('fail', !pass);
  }

  function checkPassword() {
    var v = p1El ? p1El.value : '';
    rule('rules-password1', 'len',     v.length >= 8);
    rule('rules-password1', 'letter',  /[a-zA-Z]/.test(v));
    rule('rules-password1', 'digit',   /[0-9]/.test(v));
    rule('rules-password1', 'special', /[!@#$%^&*()\-_=+\[\]{};:'",.<>/?`~\\|]/.test(v));
    if (p2El && p2El.value.length > 0) checkConfirm();
  }

  function checkConfirm() {
    var v1 = p1El ? p1El.value : '';
    var v2 = p2El ? p2El.value : '';
    rule('rules-password2', 'match', v2 === v1 && v2.length > 0);
  }

  if (p1El) p1El.addEventListener('input', checkPassword);
  if (p2El) p2El.addEventListener('input', checkConfirm);
}());
