(function () {
  'use strict';

  const menuData    = JSON.parse(document.getElementById('monthly-menu-data').textContent);
  const revByYear   = JSON.parse(document.getElementById('rev-by-year-data').textContent);
  const chartRaw    = JSON.parse(document.getElementById('chart-data').textContent);
  const meta        = JSON.parse(document.getElementById('page-meta').textContent);

  const months      = Object.keys(menuData).sort();
  let menuIdx       = Math.max(months.indexOf(meta.currentMonthKey), 0);

  const NAVY = '#1a2744';
  const MUTED = '#888';

  /* ── 포맷 ────────────────────────────────── */
  function fmtMonth(key) {
    const [y, m] = key.split('-');
    return `${y}년 ${parseInt(m)}월`;
  }
  function fmtNum(n) { return Number(n).toLocaleString('ko-KR'); }

  /* ── 월별 매출 그래프 ──────────────────────── */
  if (typeof Chart !== 'undefined' && chartRaw.labels.length) {
    new Chart(document.getElementById('monthlyRevChart'), {
      type: 'line',
      data: {
        labels: chartRaw.labels.map(k => {
          const [y, m] = k.split('-'); return `${y}.${m}`;
        }),
        datasets: [{
          data: chartRaw.data,
          borderColor: NAVY,
          backgroundColor: 'rgba(26,39,68,0.06)',
          pointBackgroundColor: NAVY,
          pointRadius: 3,
          tension: 0.3,
          fill: true,
        }],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: { label: ctx => ' ' + fmtNum(ctx.parsed.y) + '원' },
          },
        },
        scales: {
          x: { ticks: { color: MUTED, font: { size: 10 } }, grid: { display: false } },
          y: { ticks: { color: MUTED, font: { size: 10 },
                        callback: v => (v / 10000).toLocaleString() + '만' },
               grid: { color: '#eee' } },
        },
      },
    });
  }

  /* ── 메뉴별 현황 렌더링 ────────────────────── */
  function renderMenu(idx) {
    const key   = months[idx] || meta.currentMonthKey;
    const items = menuData[key] || [];
    const list  = document.getElementById('menu-table');

    const totalRev = items.reduce((sum, i) => sum + i.rev, 0);
    const rows = items.map(item => `
      <li class="dl-row">
        <span class="dl-name">${item.name}</span>
        <span class="dl-qty">${fmtNum(item.qty)}개</span>
        <span class="dl-rev">${fmtNum(item.rev)}원</span>
      </li>`).join('') || '<li class="dl-empty">데이터가 없습니다.</li>';

    const totalRow = items.length ? `
      <li class="dl-row dl-total">
        <span class="dl-name">월 매출 합계</span>
        <span class="dl-qty"></span>
        <span class="dl-rev">${fmtNum(totalRev)}원</span>
      </li>` : '';

    list.innerHTML = `
      <li class="dl-header">
        <span class="dl-name">메뉴</span>
        <span class="dl-qty">수량</span>
        <span class="dl-rev">매출</span>
      </li>${rows}${totalRow}`;

    document.getElementById('menu-month-label').textContent = fmtMonth(key);
    document.getElementById('btn-menu-prev').disabled = idx <= 0;
    document.getElementById('btn-menu-next').disabled = idx >= months.length - 1;
  }

  document.getElementById('btn-menu-prev').addEventListener('click', () => {
    if (menuIdx > 0) renderMenu(--menuIdx);
  });
  document.getElementById('btn-menu-next').addEventListener('click', () => {
    if (menuIdx < months.length - 1) renderMenu(++menuIdx);
  });

  renderMenu(menuIdx);

  /* ── 연도별 월 매출 리스트 ─────────────────── */
  const years   = Object.keys(revByYear).filter(y => revByYear[y].length).sort();
  let   yearIdx = years.length - 1;   // 가장 최근 연도부터

  function renderRevYear(idx) {
    const year  = years[idx];
    const items = revByYear[year] || [];
    document.getElementById('rev-year-label').textContent = `${year}년`;

    const total = items.reduce((sum, m) => sum + m.rev, 0);
    const rows  = items.map(m => `
      <li class="dl-row">
        <span class="dl-name">${fmtMonth(m.month)}</span>
        <span class="dl-rev">${fmtNum(m.rev)}원</span>
      </li>`).join('') || '<li class="dl-empty">데이터가 없습니다.</li>';

    const totalRow = items.length ? `
      <li class="dl-row dl-total">
        <span class="dl-name">월 매출 합계</span>
        <span class="dl-rev">${fmtNum(total)}원</span>
      </li>` : '';

    document.getElementById('rev-year-list').innerHTML = `
      <li class="dl-header">
        <span class="dl-name">월</span>
        <span class="dl-rev">매출</span>
      </li>${rows}${totalRow}`;

    document.getElementById('btn-rev-prev').disabled = idx <= 0;
    document.getElementById('btn-rev-next').disabled = idx >= years.length - 1;
  }

  document.getElementById('btn-rev-prev').addEventListener('click', () => {
    if (yearIdx > 0) renderRevYear(--yearIdx);
  });
  document.getElementById('btn-rev-next').addEventListener('click', () => {
    if (yearIdx < years.length - 1) renderRevYear(++yearIdx);
  });

  renderRevYear(yearIdx);
})();
