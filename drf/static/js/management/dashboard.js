/**
 * management/dashboard.js
 * ========================
 * 운영 현황 대시보드 전용 — 신규 가입 추이 차트 (Chart.js)
 */
'use strict';

document.addEventListener('DOMContentLoaded', function () {
  var meta   = document.getElementById('mgmt-signup-data');
  var canvas = document.getElementById('mgmt-signup-chart');
  if (!meta || !canvas || typeof Chart === 'undefined') return;

  var labels = (meta.dataset.labels || '').split(',').filter(Boolean).map(function (s) {
    var parts = s.split('-');
    return parts[1] + '/' + parts[2];
  });
  var values = (meta.dataset.values || '').split(',').filter(Boolean).map(Number);

  new Chart(canvas, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{ label: '신규 가입', data: values,
        backgroundColor: 'rgba(30,42,74,.75)', borderColor: 'rgba(30,42,74,1)',
        borderWidth: 1, borderRadius: 2 }],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: function (c) { return c.parsed.y + '명'; } } },
      },
      scales: {
        y: { beginAtZero: true, ticks: { precision: 0, font: { size: 10 } }, grid: { color: 'rgba(0,0,0,.05)' } },
        x: { ticks: { font: { size: 10 } }, grid: { display: false } },
      },
    },
  });
});
