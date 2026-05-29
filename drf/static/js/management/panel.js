/**
 * management/panel.js
 * ====================
 * 서브페이지 전용 — 필터 버튼 토글, 인라인 검색
 */
'use strict';

document.addEventListener('DOMContentLoaded', function () {

  // ── 필터 버튼 그룹 토글
  document.querySelectorAll('.mgmt-filter-btn[data-filter]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var group = btn.dataset.group;
      document.querySelectorAll('.mgmt-filter-btn[data-group="' + group + '"]').forEach(function (b) {
        b.classList.remove('active');
      });
      btn.classList.add('active');

      var filter = btn.dataset.filter;
      document.querySelectorAll('tr[data-status]').forEach(function (row) {
        row.style.display = (filter === 'all' || row.dataset.status === filter) ? '' : 'none';
      });
    });
  });

  // ── 인라인 검색
  var searchEl = document.querySelector('.mgmt-search[data-search]');
  if (searchEl) {
    searchEl.addEventListener('input', function () {
      var q      = searchEl.value.trim().toLowerCase();
      var target = searchEl.dataset.search;
      document.querySelectorAll(target).forEach(function (row) {
        row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
      });
    });
  }

});
