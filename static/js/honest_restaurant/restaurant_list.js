(function () {
  'use strict';

  var searchInput  = document.getElementById('filter-search');
  var provinceSel  = document.getElementById('filter-province');
  var businessSel  = document.getElementById('filter-business-type');
  var searchBtn    = document.getElementById('btn-filter-search');
  var section      = document.getElementById('restaurant-section');

  if (!searchBtn) return;

  // ── 현재 필터 입력값으로 URLSearchParams 생성 ─────────────────
  function buildParams(pageOverride) {
    var params   = new URLSearchParams();
    var search   = searchInput ? searchInput.value.trim() : '';
    var province = provinceSel ? provinceSel.value        : '';
    var business = businessSel ? businessSel.value        : '';

    if (search)        params.set('search',        search);
    if (province)      params.set('province',      province);
    if (business)      params.set('business_type', business);
    if (pageOverride)  params.set('page',          pageOverride);

    return params;
  }

  // ── AJAX로 #restaurant-section만 교체 ────────────────────────
  function navigate(params) {
    var qs  = params.toString();
    var url = window.location.pathname + (qs ? '?' + qs : '');

    history.pushState(null, '', url);

    if (!section) {
      window.location.href = url;
      return;
    }

    section.classList.add('loading');

    fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (res) {
        if (!res.ok) throw new Error(res.status);
        return res.text();
      })
      .then(function (html) {
        var doc        = new DOMParser().parseFromString(html, 'text/html');
        var newSection = doc.getElementById('restaurant-section');
        if (newSection) {
          section.innerHTML = newSection.innerHTML;
          window.scrollTo({ top: 0, behavior: 'smooth' });
          // 지도 마커 갱신 요청
          document.dispatchEvent(new CustomEvent('restaurantSectionUpdated'));
        }
      })
      .catch(function () {
        // fetch 실패 시 일반 이동으로 폴백
        window.location.href = url;
      })
      .finally(function () {
        section.classList.remove('loading');
      });
  }

  // ── 검색/필터 실행 (page 초기화) ────────────────────────────
  function doSearch() {
    navigate(buildParams(null));
  }

  // ── 페이지네이션 클릭 — 이벤트 위임 (동적 DOM 대응) ──────────
  document.addEventListener('click', function (e) {
    var a = e.target.closest('#pagination a.page-btn');
    if (!a) return;
    e.preventDefault();

    var url  = new URL(a.href);
    var page = url.searchParams.get('page');
    navigate(buildParams(page));
  });

  // ── 필터 이벤트 바인딩 ───────────────────────────────────────
  searchBtn.addEventListener('click', doSearch);

  if (searchInput) {
    searchInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') doSearch();
    });
  }

  // ── 행 전체 클릭 → 상세 페이지 이동 (이벤트 위임) ──────────
  document.addEventListener('click', function (e) {
    // 페이지네이션·필터 클릭은 위에서 처리하므로 제외
    if (e.target.closest('#pagination') || e.target.closest('#filter-bar')) return;
    // <a> 태그 직접 클릭은 브라우저 기본 동작에 맡김
    if (e.target.closest('a')) return;

    var row = e.target.closest('tbody tr[data-href]');
    if (!row) return;
    window.location.href = row.dataset.href;
  });

  // ── 브라우저 뒤로/앞으로 → 전체 새로고침 ────────────────────
  window.addEventListener('popstate', function () {
    window.location.reload();
  });
})();


// ── 카카오 지도 (페이지 로드 시 자동 표시) ───────────────────
(function () {
  if (typeof kakao === 'undefined' || typeof kakao.maps === 'undefined') return;

  var container = document.getElementById('kakao-map');
  if (!container) return;

  var kakaoMap = new kakao.maps.Map(container, {
    center: new kakao.maps.LatLng(37.5665, 126.9780),
    level : 8,
  });




  // ── 마커 이미지 ───────────────────────────────────────────
  function makeMarkerImage(color, w, h) {
    var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="' + w + '" height="' + h + '" viewBox="0 0 24 35">'
            + '<path d="M12 0C5.4 0 0 5.4 0 12c0 7.4 12 23 12 23S24 19.4 24 12C24 5.4 18.6 0 12 0z" fill="' + color + '"/>'
            + '<circle cx="12" cy="12" r="5" fill="white"/>'
            + '</svg>';
    return new kakao.maps.MarkerImage(
      'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg),
      new kakao.maps.Size(w, h),
      { offset: new kakao.maps.Point(w / 2, h) }
    );
  }

  var imgBlue = makeMarkerImage('#4A90E2', 24, 35);
  var imgPink = makeMarkerImage('#FF69B4', 34, 49);

  // ── 하트 마커 이미지 (북마크 가게용) ─────────────────────
  function makeHeartImage(w) {
    var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="' + w + '" height="' + w + '" viewBox="0 0 24 24">'
            + '<path d="M12 21.593C6.37 16.054 1 11.296 1 7.191 1 3.4 4.068 2 6.281 2c1.312 0 4.151.501 5.719 4.457C13.59 2.489 16.464 2 17.726 2 20.266 2 23 3.621 23 7.181c0 4.069-5.136 8.876-11 14.412z" fill="#FF1493"/>'
            + '<path d="M12 21.593C6.37 16.054 1 11.296 1 7.191 1 3.4 4.068 2 6.281 2c1.312 0 4.151.501 5.719 4.457C13.59 2.489 16.464 2 17.726 2 20.266 2 23 3.621 23 7.181c0 4.069-5.136 8.876-11 14.412z" fill="none" stroke="white" stroke-width="1"/>'
            + '</svg>';
    return new kakao.maps.MarkerImage(
      'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg),
      new kakao.maps.Size(w, w),
      { offset: new kakao.maps.Point(w / 2, w / 2) }
    );
  }

  var imgHeart      = makeHeartImage(28);
  var imgHeartHover = makeHeartImage(36);

  // 북마크 PK Set 읽기
  function readBookmarkedPks() {
    var el = document.getElementById('bookmarked-pks');
    try { return new Set(JSON.parse(el ? el.textContent : '[]')); } catch (e) { return new Set(); }
  }
  var bookmarkedPks = readBookmarkedPks();

  // ── 마커 목록 관리 ────────────────────────────────────────
  var markers  = [];
  var overlays = [];

  function clearMarkers() {
    markers.forEach(function (m) { m.setMap(null); });
    overlays.forEach(function (o) { o.setMap(null); });
    markers  = [];
    overlays = [];
  }

  function addMarkers(data) {
    clearMarkers();
    data.forEach(function (r) {
      var pos          = new kakao.maps.LatLng(r.lat, r.lng);
      var isBookmarked = bookmarkedPks.has(r.pk);
      var defaultImg   = isBookmarked ? imgHeart     : imgBlue;
      var hoverImg     = isBookmarked ? imgHeartHover : imgPink;
      var marker = new kakao.maps.Marker({ map: kakaoMap, position: pos, image: defaultImg });

      kakao.maps.event.addListener(marker, 'mouseover', function () { marker.setImage(hoverImg); });
      kakao.maps.event.addListener(marker, 'mouseout',  function () { marker.setImage(defaultImg); });
      kakao.maps.event.addListener(marker, 'click',     function () {
        window.location.href = '/restaurants/' + r.pk + '/';
      });

      var overlay = new kakao.maps.CustomOverlay({
        map     : kakaoMap,
        position: pos,
        content : '<div class="map-label" style="background:#fff;border:1px solid #ddd;border-radius:4px;padding:2px 7px;font-size:11px;white-space:nowrap;box-shadow:0 1px 3px rgba(0,0,0,.15);cursor:pointer">' + r.name + '</div>',
        yAnchor : isBookmarked ? 1.8 : 2.6,
      });

      markers.push(marker);
      overlays.push(overlay);
    });
  }

  function readGeoData() {
    var el = document.getElementById('restaurant-geo-data');
    try { return el ? JSON.parse(el.textContent) : []; } catch (e) { return []; }
  }

  // 초기 마커 표시
  addMarkers(readGeoData());

  // ── 검색/필터 AJAX 완료 시 마커 갱신 ────────────────────────
  document.addEventListener('restaurantSectionUpdated', function () {
    addMarkers(readGeoData());
  });

  // ── 지도 더블 클릭 → 해당 위치 중심·구 단위 줌인 → idle가 리스트 갱신 ──
  kakao.maps.event.addListener(kakaoMap, 'dblclick', function (mouseEvent) {
    kakaoMap.setCenter(mouseEvent.latLng);
    kakaoMap.setLevel(6); // 구 단위 레벨 6으로 줌인
  });

  // ── 지도 이동/줌 → 리스트 갱신 (600ms 디바운스) ──────────
  var boundsTimer = null;
  kakao.maps.event.addListener(kakaoMap, 'idle', function () {
    clearTimeout(boundsTimer);
    boundsTimer = setTimeout(function () {
      var bounds = kakaoMap.getBounds();
      var sw     = bounds.getSouthWest();
      var ne     = bounds.getNorthEast();

      var searchInput = document.getElementById('filter-search');
      var provinceSel = document.getElementById('filter-province');
      var businessSel = document.getElementById('filter-business-type');
      var params = new URLSearchParams();
      var search   = searchInput ? searchInput.value.trim() : '';
      var province = provinceSel ? provinceSel.value : '';
      var business = businessSel ? businessSel.value : '';
      if (search)   params.set('search',        search);
      if (province) params.set('province',      province);
      if (business) params.set('business_type', business);
      params.set('sw_lat', sw.getLat().toFixed(6));
      params.set('sw_lng', sw.getLng().toFixed(6));
      params.set('ne_lat', ne.getLat().toFixed(6));
      params.set('ne_lng', ne.getLng().toFixed(6));

      var section = document.getElementById('restaurant-section');
      var url     = window.location.pathname + '?' + params.toString();
      history.pushState(null, '', url);
      if (section) section.classList.add('loading');

      fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(function (res) { return res.text(); })
        .then(function (html) {
          var doc        = new DOMParser().parseFromString(html, 'text/html');
          var newSection = doc.getElementById('restaurant-section');
          if (newSection && section) {
            section.innerHTML = newSection.innerHTML;
            addMarkers(readGeoData());
          }
        })
        .finally(function () {
          if (section) section.classList.remove('loading');
        });
    }, 600);
  });
})();
