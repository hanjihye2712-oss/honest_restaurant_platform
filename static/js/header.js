// ── 전역 CSRF 토큰 추출 (모든 페이지에서 재사용) ─────────────────────────────
function getCsrf() {
  return (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';
}

// ── 사이드 패널 (헤더 아래 오른쪽 슬라이딩) ─────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  var hamburger = document.getElementById('btn-sidenav');
  var overlay   = document.getElementById('sidenav-overlay');
  var sidenav   = document.getElementById('sidenav');
  var wrapper   = document.querySelector('.hdr-wrapper');

  if (!hamburger || !sidenav || !overlay) return;

  // 헤더 높이만큼 패널 top 설정
  function setTop() {
    var h = wrapper ? wrapper.getBoundingClientRect().bottom : 0;
    sidenav.style.top = h + 'px';
    overlay.style.top = h + 'px';
  }

  function openNav() {
    setTop();
    sidenav.classList.add('open');
    overlay.classList.add('open');
    sidenav.setAttribute('aria-hidden', 'false');
    hamburger.setAttribute('aria-expanded', 'true');
  }

  function closeNav() {
    sidenav.classList.remove('open');
    overlay.classList.remove('open');
    sidenav.setAttribute('aria-hidden', 'true');
    hamburger.setAttribute('aria-expanded', 'false');
  }

  hamburger.addEventListener('click', function (e) {
    e.stopPropagation();
    sidenav.classList.contains('open') ? closeNav() : openNav();
  });

  overlay.addEventListener('click', closeNav);

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeNav();
  });

  // goOwner()에서 호출할 수 있도록 전역 노출
  window.closeNav = closeNav;
});

function goOwner() {
  if (typeof window.closeNav === 'function') window.closeNav();
  location.href = '/dashboard/';
}

document.addEventListener('DOMContentLoaded', function () {
  var logoutBtn = document.getElementById('btn-logout');
  if (!logoutBtn) return;

  logoutBtn.addEventListener('click', function () {
    if (!confirm('로그아웃 하시겠습니까?')) return;

    axios.post('/accounts/api/ajax-logout/', {}, {
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrf(),
      }
    })
      .then(function () {
        window.location.href = '/';
        location.reload(true);
      })
      .catch(function () {
        window.location.href = '/';
        location.reload(true);
      });
  });
});
