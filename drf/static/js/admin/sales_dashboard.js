(function () {
  /* ─ 데이터 파싱 ─ */
  function parse(id) {
    var el = document.getElementById(id);
    return el ? JSON.parse(el.textContent) : [];
  }
  var daily       = parse('d-daily');
  var weekly      = parse('d-weekly');
  var monthly     = parse('d-monthly');
  var dow         = parse('d-dow');
  var menus       = parse('d-menus');
  var hourly      = parse('d-hourly');
  var mktEffect   = parse('d-mkt-effect');
  var coreMenus   = parse('d-core-menus');
  var lowMenus    = parse('d-low-menus');
  var consulting  = parse('d-consulting');
  var restaurants = parse('d-restaurants');

  /* ─ 색상 ─ */
  var NAVY  = '#1a2744';
  var RED   = '#c0392b';
  var MUTED = '#888';

  /* ─ 공통 스케일 ─ */
  var scaleOpts = {
    x: { ticks: { color: MUTED, font: { size: 10 } }, grid: { display: false } },
    y: { ticks: { color: MUTED, font: { size: 10 },
                  callback: function (v) { return (v / 10000).toLocaleString() + '만'; } },
         grid: { color: '#eee' } },
  };
  function fmtAmt(v) { return Number(v).toLocaleString('ko-KR') + '원'; }

  /* ─ 일별 차트 ─ */
  new Chart(document.getElementById('dailyChart'), {
    type: 'bar',
    data: {
      labels: daily.map(function (d) { return d.x.slice(5); }),
      datasets: [{ data: daily.map(function (d) { return d.y; }), backgroundColor: NAVY, borderRadius: 2 }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false },
        tooltip: { callbacks: { label: function (ctx) { return ' ' + fmtAmt(ctx.parsed.y); } } } },
      scales: scaleOpts,
    },
  });

  /* ─ 주별 차트 ─ */
  new Chart(document.getElementById('weeklyChart'), {
    type: 'line',
    data: {
      labels: weekly.map(function (w) { return w.x.slice(5); }),
      datasets: [{ data: weekly.map(function (w) { return w.y; }), borderColor: NAVY,
        backgroundColor: 'rgba(26,39,68,.08)', pointRadius: 3, tension: 0.3, fill: true }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false },
        tooltip: { callbacks: { label: function (ctx) { return ' ' + fmtAmt(ctx.parsed.y); } } } },
      scales: scaleOpts,
    },
  });

  /* ─ 월별 차트 ─ */
  new Chart(document.getElementById('monthlyChart'), {
    type: 'line',
    data: {
      labels: monthly.map(function (m) { return m.x; }),
      datasets: [{ data: monthly.map(function (m) { return m.y; }), borderColor: RED,
        backgroundColor: 'rgba(192,57,43,.08)', pointRadius: 3, tension: 0.3, fill: true }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false },
        tooltip: { callbacks: { label: function (ctx) { return ' ' + fmtAmt(ctx.parsed.y); } } } },
      scales: scaleOpts,
    },
  });

  /* ─ 시간대별 차트 ─ */
  (function () {
    var hours = [];
    for (var i = 0; i < 24; i++) { hours.push(i); }
    var hourMap = {};
    hourly.forEach(function (h) { hourMap[h.hour] = h; });
    var labels = hours.map(function (h) { return h + '시'; });
    var data   = hours.map(function (h) { return hourMap[h] ? hourMap[h].total : 0; });
    var colors = hours.map(function (h) { return (h >= 11 && h <= 22) ? NAVY : 'rgba(26,39,68,0.3)'; });

    new Chart(document.getElementById('hourlyChart'), {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{ data: data, backgroundColor: colors, borderRadius: 2 }],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false },
          tooltip: { callbacks: { label: function (ctx) { return ' ' + fmtAmt(ctx.parsed.y); } } } },
        scales: scaleOpts,
      },
    });
  })();

  /* ─ 요일별 차트 ─ */
  new Chart(document.getElementById('dowChart'), {
    type: 'bar',
    data: {
      labels: dow.map(function (d) { return d.label; }),
      datasets: [{ data: dow.map(function (d) { return d.avg; }), backgroundColor: NAVY, borderRadius: 2 }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false },
        tooltip: { callbacks: { label: function (ctx) { return ' ' + fmtAmt(ctx.parsed.y); } } } },
      scales: scaleOpts,
    },
  });

  /* ─ 메뉴별 가로 바 차트 ─ */
  new Chart(document.getElementById('menuChart'), {
    type: 'bar',
    data: {
      labels: menus.map(function (m) { return m.name; }),
      datasets: [{ data: menus.map(function (m) { return m.qty; }), backgroundColor: NAVY, borderRadius: 2 }],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      plugins: { legend: { display: false },
        tooltip: { callbacks: { label: function (ctx) { return ' ' + ctx.parsed.x.toLocaleString() + '개'; } } } },
      scales: {
        x: { ticks: { color: MUTED, font: { size: 10 } }, grid: { color: '#eee' } },
        y: { ticks: { color: MUTED, font: { size: 10 } }, grid: { display: false } },
      },
    },
  });

  /* ─ 마케팅 효과 테이블 렌더링 ─ */
  (function () {
    var tbody = document.getElementById('mktEffectBody');
    if (!mktEffect.length) {
      document.getElementById('mktNoData').style.display = 'block';
      tbody.closest('table').style.display = 'none';
      return;
    }
    mktEffect.forEach(function (row) {
      var changeStr = row.change !== null
        ? '<span class="' + (row.change >= 0 ? 'mkt-change-up' : 'mkt-change-down') + '">' +
          (row.change >= 0 ? '+' : '') + row.change + '%</span>'
        : '<span style="color:#888">-</span>';
      tbody.insertAdjacentHTML('beforeend',
        '<tr>' +
        '<td>' + row.platform + '</td>' +
        '<td>' + row.date + '</td>' +
        '<td>' + Number(row.before).toLocaleString() + '원</td>' +
        '<td>' + Number(row.after).toLocaleString() + '원</td>' +
        '<td>' + changeStr + '</td>' +
        '</tr>'
      );
    });
  })();

  /* ─ 메뉴 인사이트 렌더링 ─ */
  (function () {
    var coreWrap = document.getElementById('coreMenuWrap');
    var lowWrap  = document.getElementById('lowMenuWrap');

    if (!coreMenus.length) {
      coreWrap.innerHTML = '<span style="color:#888;font-size:13px;">데이터 없음</span>';
    } else {
      coreMenus.forEach(function (m) {
        coreWrap.insertAdjacentHTML('beforeend',
          '<span class="menu-chip" title="' + Number(m.qty).toLocaleString() + '개 / ' +
          Number(m.rev).toLocaleString() + '원 (' + m.pct + '%)">' +
          m.name + ' <strong>' + m.pct + '%</strong></span>'
        );
      });
    }

    if (!lowMenus.length) {
      lowWrap.innerHTML = '<span style="color:#888;font-size:13px;">데이터 없음</span>';
    } else {
      lowMenus.forEach(function (m) {
        lowWrap.insertAdjacentHTML('beforeend',
          '<span class="menu-chip menu-chip-low" title="' + Number(m.qty).toLocaleString() + '개 / ' +
          Number(m.rev).toLocaleString() + '원 (' + m.pct + '%)">' +
          m.name + ' <strong>' + m.pct + '%</strong></span>'
        );
      });
    }
  })();

  /* ─ 관리 매장 목록 렌더링 ─ */
  (function () {
    var tbody = document.getElementById('restaurantBody');
    if (!restaurants.length) {
      document.getElementById('restaurantNoData').style.display = 'block';
      document.getElementById('restaurantTable').style.display = 'none';
      return;
    }
    var statusColor = { '관리 중': '#27ae60', '휴면': '#e74c3c', '검토 중': '#f39c12' };
    restaurants.forEach(function (r) {
      tbody.insertAdjacentHTML('beforeend',
        '<tr>' +
        '<td style="font-weight:700">' + r.name + '</td>' +
        '<td>' + r.owner_name + '</td>' +
        '<td>' + (r.phone || '<span style="color:#bbb">-</span>') + '</td>' +
        '<td>' + (r.business_type || '<span style="color:#bbb">-</span>') + '</td>' +
        '<td><span style="color:' + (statusColor[r.status_display] || '#888') + ';font-weight:700">' + r.status_display + '</span></td>' +
        '<td>' + r.joined_at + '</td>' +
        '<td><a href="/admin/sales/managedrestaurant/' + r.id + '/change/" style="color:#1a2744;font-size:12px;">수정</a></td>' +
        '</tr>'
      );
    });
  })();

  /* ─ 상담 기록 테이블 렌더링 ─ */
  (function () {
    var tbody = document.getElementById('consultBody');
    if (!consulting.length) {
      document.getElementById('consultNoData').style.display = 'block';
      tbody.closest('table').style.display = 'none';
      return;
    }
    consulting.forEach(function (c) {
      var content = c.content.length > 60 ? c.content.slice(0, 60) + '…' : c.content;
      var nextAction = c.next_action
        ? (c.next_action.length > 50 ? c.next_action.slice(0, 50) + '…' : c.next_action)
        : '<span style="color:#bbb">-</span>';
      tbody.insertAdjacentHTML('beforeend',
        '<tr>' +
        '<td>' + c.date + '</td>' +
        '<td><span class="cat-badge">' + c.category_display + '</span></td>' +
        '<td>' + content + '</td>' +
        '<td>' + nextAction + '</td>' +
        '<td>' + (c.next_date || '<span style="color:#bbb">-</span>') + '</td>' +
        '<td>' + (c.created_by__username || '<span style="color:#bbb">-</span>') + '</td>' +
        '</tr>'
      );
    });
  })();

})();
