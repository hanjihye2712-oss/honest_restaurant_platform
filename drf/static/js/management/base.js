/**
 * management/base.js
 * ===================
 * 모든 관리자 페이지 공통 동작
 * - 사이드바 sticky (헤더 높이 동적 반영)
 * - 실시간 시계
 */
'use strict';

document.addEventListener('DOMContentLoaded', function () {

  // ── 사이드바 sticky: 헤더 높이만큼 top 오프셋 적용
  var sidebar    = document.querySelector('.mgmt-sidebar');
  var hdrWrapper = document.querySelector('.hdr-wrapper');
  if (sidebar && hdrWrapper) {
    function setSidebarTop() {
      var h = hdrWrapper.getBoundingClientRect().height;
      sidebar.style.top    = h + 'px';
      sidebar.style.height = 'calc(100vh - ' + h + 'px)';
    }
    setSidebarTop();
    window.addEventListener('resize', setSidebarTop);
  }

  // ── 실시간 시계
  var clockEl = document.getElementById('mgmt-clock');
  if (clockEl) {
    function tick() {
      var now = new Date();
      var p   = function (n) { return String(n).padStart(2, '0'); };
      clockEl.textContent =
        now.getFullYear() + '.' + p(now.getMonth() + 1) + '.' + p(now.getDate()) +
        '  ' + p(now.getHours()) + ':' + p(now.getMinutes()) + ':' + p(now.getSeconds());
    }
    tick();
    setInterval(tick, 1000);
  }

});
