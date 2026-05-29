/* ── 사장님 대시보드 차트 + 사이드네비 ── */

document.addEventListener('DOMContentLoaded', function () {
  /* ── 프로그레스 바 애니메이션 (double rAF: 초기 paint 후 transition 발동) ── */
  requestAnimationFrame(function () {
    requestAnimationFrame(function () {
      document.querySelectorAll('[data-w]').forEach(function (el) {
        el.style.width = el.dataset.w + '%';
      });
    });
  });

  var _dbEl      = document.getElementById('db-chart-data');
  var _radarData  = _dbEl ? JSON.parse(_dbEl.dataset.radar)          : [];
  var _posPct     = _dbEl ? parseInt(_dbEl.dataset.pos,  10)         : 0;
  var _neuPct     = _dbEl ? parseInt(_dbEl.dataset.neu,  10)         : 0;
  var _negPct     = _dbEl ? parseInt(_dbEl.dataset.neg,  10)         : 0;
  var _trendLbls  = _dbEl ? JSON.parse(_dbEl.dataset.trendLabels)    : [];
  var _trendData  = _dbEl ? JSON.parse(_dbEl.dataset.trendData)      : [];
  var _bmTrendLbls = _dbEl ? JSON.parse(_dbEl.dataset.bmTrendLabels) : [];
  var _bmTrendData = _dbEl ? JSON.parse(_dbEl.dataset.bmTrendData)   : [];

  /* ── 레이더 차트 ── */
  var radarEl = document.getElementById('radarChart');
  if (radarEl && _radarData.length) {
    new Chart(radarEl.getContext('2d'), {
      type: 'radar',
      data: {
        labels: ['정부인증', '가격일치율', '연혁', '방문자인증', '찜수', 'AI점수'],
        datasets: [{
          label: '현재 점수',
          data: _radarData,
          backgroundColor: 'rgba(26,39,68,0.15)',
          borderColor: '#1A2744',
          borderWidth: 2,
          pointBackgroundColor: '#D4251A',
          pointRadius: 4,
        }, {
          label: '만점',
          data: [100, 100, 100, 100, 100, 100],
          backgroundColor: 'transparent',
          borderColor: 'rgba(232,213,160,0.6)',
          borderWidth: 1,
          borderDash: [4, 4],
          pointRadius: 0,
        }]
      },
      options: {
        responsive: true,
        scales: {
          r: {
            min: 0, max: 100,
            ticks: { display: false },
            grid: { color: 'rgba(26,39,68,0.1)' },
            pointLabels: { font: { size: 11, family: "'Noto Sans KR'" }, color: '#1A2744' }
          }
        },
        plugins: { legend: { display: false } }
      }
    });
  }

  /* ── 도넛 차트 ── */
  var donutEl = document.getElementById('donutChart');
  if (donutEl) {
    new Chart(donutEl.getContext('2d'), {
      type: 'doughnut',
      data: {
        datasets: [{
          data: [_posPct, _neuPct, _negPct],
          backgroundColor: ['#28a745', '#6c757d', '#D4251A'],
          borderWidth: 0,
          hoverOffset: 4,
        }]
      },
      options: {
        cutout: '68%',
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (c) {
                var labels = ['긍정', '중립', '부정'];
                return labels[c.dataIndex] + ': ' + c.raw + '%';
              }
            }
          }
        }
      }
    });
  }

  /* ── 라인 차트 (월별 영수증 인증 추이) ── */
  var lineEl = document.getElementById('lineChart');
  if (lineEl && _trendLbls.length) {
    new Chart(lineEl.getContext('2d'), {
      type: 'line',
      data: {
        labels: _trendLbls,
        datasets: [{
          label: '영수증 인증 건수',
          data: _trendData,
          borderColor: '#1A2744',
          backgroundColor: 'rgba(26,39,68,0.08)',
          fill: true, tension: 0.3,
          pointBackgroundColor: '#D4251A', pointRadius: 5,
        }]
      },
      options: {
        responsive: true,
        scales: {
          y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.06)' } },
          x: { grid: { display: false } }
        },
        plugins: { legend: { display: false } }
      }
    });
  }

  /* ── 라인 차트 (월별 저장수 추이) ── */
  var bmLineEl = document.getElementById('bmLineChart');
  if (bmLineEl && _bmTrendLbls.length) {
    new Chart(bmLineEl.getContext('2d'), {
      type: 'line',
      data: {
        labels: _bmTrendLbls,
        datasets: [{
          label: '저장수',
          data: _bmTrendData,
          borderColor: '#D4251A',
          backgroundColor: 'rgba(212,37,26,0.08)',
          fill: true, tension: 0.3,
          pointBackgroundColor: '#1A2744', pointRadius: 5,
        }]
      },
      options: {
        responsive: true,
        scales: {
          y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.06)' } },
          x: { grid: { display: false } }
        },
        plugins: { legend: { display: false } }
      }
    });
  } else if (bmLineEl) {
    var bmTitle = bmLineEl.closest('.bottom-card') && bmLineEl.closest('.bottom-card').querySelector('.bc-title');
    if (bmTitle) bmTitle.insertAdjacentHTML('afterend', '<p style="font-size:13px;color:var(--muted);margin-top:12px">아직 저장 데이터가 없습니다.</p>');
  }

  if (typeof renderHistory === 'function') renderHistory();
});

/* ── 사이드 네비게이션 ── */
(function () {
  'use strict';

  var items = document.querySelectorAll('.db-snav-item');

  items.forEach(function (item) {
    item.addEventListener('click', function () {
      var target = document.getElementById(item.dataset.target);
      if (!target) return;
      var rect = target.getBoundingClientRect();
      var top  = rect.top + window.scrollY - Math.round(window.innerHeight * 0.35);
      window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
    });
  });

  var sectionIds = ['sec-hero', 'sec-marketing', 'sec-insight', 'sec-badge', 'sec-score', 'sec-sales', 'sec-recent'];

  function setActive(id) {
    items.forEach(function (item) {
      item.classList.toggle('active', item.dataset.target === id);
    });
  }

  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) setActive(entry.target.id);
    });
  }, { rootMargin: '0px 0px -50% 0px', threshold: 0 });

  sectionIds.forEach(function (id) {
    var el = document.getElementById(id);
    if (el) observer.observe(el);
  });
})();
