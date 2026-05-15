(function () {
  'use strict';

  if (typeof Chart === 'undefined') return;
  if (!document.getElementById('menuChart')) return;

  const NAVY  = '#1a2744';
  const RED   = '#c0392b';
  const MUTED = '#888';

  const scaleBase = {
    x: { ticks: { color: MUTED, font: { size: 11 } }, grid: { display: false } },
    y: { ticks: { color: MUTED, font: { size: 11 } }, grid: { color: '#eee' } },
  };

  fetch('/sales/api/dashboard/')
    .then(res => res.json())
    .then(data => {
      // 이번 달 매출 뱃지
      const badge = document.getElementById('sales-monthly-badge');
      if (badge) {
        badge.textContent = '이번 달 ' + data.monthly_total.toLocaleString('ko-KR') + '원';
      }

      // ── 메뉴별 판매량 바 차트 (클릭 → 상세 페이지) ──
      const menuCtx = document.getElementById('menuChart');
      const menuChart = new Chart(menuCtx, {
        type: 'bar',
        data: {
          labels: data.menu_labels,
          datasets: [{
            data: data.menu_data,
            backgroundColor: data.menu_labels.map(l =>
              l === '주류/음료' ? RED : NAVY
            ),
            borderRadius: 2,
          }],
        },
        options: {
          responsive: true,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: { label: ctx => ' ' + ctx.parsed.y + '개' },
            },
          },
          scales: scaleBase,
          onHover: (event, elements) => {
            menuCtx.style.cursor = elements.length ? 'pointer' : 'default';
          },
        },
      });

      // 바 클릭 → 상세 페이지 이동
      menuCtx.addEventListener('click', (e) => {
        const points = menuChart.getElementsAtEventForMode(e, 'nearest', { intersect: true }, false);
        if (!points.length) return;
        const idx  = points[0].index;
        const key  = data.menu_keys[idx];  // 'drink' 또는 메뉴명
        window.location.href = '/sales/detail/';
      });

      // ── 최근 일별 매출 라인 차트 (클릭 → 상세 페이지) ──
      const shortLabels = data.daily_labels.map(d => {
        const parts = d.split('-');
        return `${parseInt(parts[1])}/${parseInt(parts[2])}`;
      });
      const dailyCtx = document.getElementById('dailyChart');
      const dailyChart = new Chart(dailyCtx, {
        type: 'line',
        data: {
          labels: shortLabels,
          datasets: [{
            data: data.daily_data,
            borderColor: RED,
            backgroundColor: 'rgba(192,57,43,0.08)',
            pointBackgroundColor: RED,
            pointRadius: 4,
            tension: 0.3,
            fill: true,
          }],
        },
        options: {
          responsive: true,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: ctx => ' ' + ctx.parsed.y.toLocaleString('ko-KR') + '원',
              },
            },
          },
          scales: scaleBase,
          onHover: (event, elements) => {
            dailyCtx.style.cursor = elements.length ? 'pointer' : 'default';
          },
        },
      });

      dailyCtx.addEventListener('click', (e) => {
        const points = dailyChart.getElementsAtEventForMode(e, 'nearest', { intersect: true }, false);
        if (!points.length) return;
        window.location.href = '/sales/detail/';
      });
    })
    .catch(err => console.error('[sales dashboard]', err));
})();
