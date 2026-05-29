(function () {
  'use strict';

  if (typeof Chart === 'undefined') return;
  if (!document.getElementById('menuChart')) return;

  const NAVY  = '#1a2744';
  const RED   = '#c0392b';
  const MUTED = '#7A6A4A';
  const CREAM = '#F5EDD0';

  /* 캔버스 전체 배경을 크림색으로 채우는 플러그인 */
  Chart.register({
    id: 'salesCanvasBg',
    beforeDraw(chart) {
      const ctx = chart.canvas.getContext('2d');
      ctx.save();
      ctx.fillStyle = CREAM;
      ctx.fillRect(0, 0, chart.canvas.width, chart.canvas.height);
      ctx.restore();
    }
  });

  const scaleBase = {
    x: { ticks: { color: MUTED, font: { size: 11 } }, grid: { display: false } },
    y: { ticks: { color: MUTED, font: { size: 11 } }, grid: { color: 'rgba(0,0,0,0.06)' } },
  };

  fetch('/sales/api/dashboard/')
    .then(res => res.json())
    .then(data => {
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
