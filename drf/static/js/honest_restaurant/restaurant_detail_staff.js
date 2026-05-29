(function () {
  'use strict';

  var btn = document.getElementById('btn-manage-register');
  if (!btn) return;

  btn.addEventListener('click', function () {
    var pk   = btn.dataset.restaurantId;
    var name = btn.dataset.restaurantName;
    showConfirm('"' + name + '"을 관리 매장으로 등록하시겠습니까?', function () {
      btn.disabled = true;
      btn.textContent = '등록 중…';

      fetch('/sales/api/register-restaurant/' + pk + '/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '',
        },
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.status === 'created') {
            btn.outerHTML = '<span class="btn-manage-tag">✓ 관리 중</span>';
            showConfirm('등록 완료! 어드민에서 사장님 정보를 추가하시겠습니까?', function () {
              window.open(data.admin_url, '_blank');
            });
          } else if (data.status === 'already') {
            btn.outerHTML = '<span class="btn-manage-tag">✓ 관리 중</span>';
            showAlert(data.message);
          } else {
            showAlert(data.error || '오류가 발생했습니다.');
            btn.disabled = false;
            btn.textContent = '⊕ 관리 매장 등록';
          }
        })
        .catch(function () {
          showAlert('네트워크 오류가 발생했습니다.');
          btn.disabled = false;
          btn.textContent = '⊕ 관리 매장 등록';
        });
    });
  });
})();
