// ── URL 설정 (template에서 data attribute로 주입) ────────────
var _appUrls        = document.getElementById('app-urls') || {};
var MAP_MARKERS_URL = (_appUrls.dataset || {}).mapMarkersUrl || '/restaurants/map-markers/';
var DISTRICT_URL    = (_appUrls.dataset || {}).districtUrl   || '/restaurants/districts/';
var RESTAURANT_BASE = (_appUrls.dataset || {}).restaurantBaseUrl || '/restaurants/';

// ── 카테고리 → 실제 업태 값 매핑 ────────────────────────────
var CATEGORY_MAP = {
  '한식'         : ['한식', '식육(숯불구이)', '냉면집', '복어취급', '탕류(보신용)', '이동조리', '출장조리'],
  '중식'         : ['중국식'],
  '일식/해산물'   : ['일식', '횟집'],
  '분식'         : ['분식', '김밥(도시락)'],
  '치킨/패스트푸드': ['통닭(치킨)', '호프/통닭', '패스트푸드', '패밀리레스트랑'],
  '양식'         : ['경양식', '외국음식전문점(인도,태국등)'],
  '카페/음료'    : ['까페', '커피숍', '전통찻집', '라이브카페', '키즈카페'],
  '주점'         : ['감성주점', '정종/대포집/소주방'],
  '뷔페'         : ['뷔페식'],
  '기타'         : ['기타', '기타 휴게음식점'],
};

// ── 공통 유틸: 현재 필터 select 값을 URLSearchParams로 변환 ──
function readFilterParams() {
  var si = document.getElementById('filter-search');
  var pr = document.getElementById('filter-province');
  var bt = document.getElementById('filter-business-type');
  var my = document.getElementById('filter-min-years');
  var params = new URLSearchParams();
  var di = document.getElementById('filter-district');
  if (si && si.value.trim()) params.set('search',    si.value.trim());
  if (pr && pr.value)        params.set('province',  pr.value);
  if (di && di.value)        params.set('district',  di.value);
  if (my && my.value)        params.set('min_years', my.value);
  // 정부인증 — 체크된 항목 모두 append
  document.querySelectorAll('.cert-cb:checked').forEach(function (cb) {
    params.append('cert', cb.value);
  });
  if (bt && bt.value) {
    var cat = bt.value;
    params.set('cat', cat);
    (CATEGORY_MAP[cat] || [cat]).forEach(function (t) {
      params.append('business_type', t);
    });
  }
  return params;
}

// ── 정부인증 체크박스 드롭다운 동작 ─────────────────────────
(function () {
  var wrap     = document.getElementById('filter-cert-wrap');
  var btn      = document.getElementById('filter-cert-btn');
  var dropdown = document.getElementById('filter-cert-dropdown');
  var label    = document.getElementById('filter-cert-label');
  if (!wrap || !btn || !dropdown) return;

  var CERT_LABELS = {
    excellent: '모범음식점',
    hygiene  : '위생등급',
    ansim    : '안심식당',
    goodprice: '착한가격업소',
  };

  function updateLabel() {
    var checked = Array.from(document.querySelectorAll('.cert-cb:checked'));
    if (checked.length === 0) {
      label.textContent = '정부인증';
    } else if (checked.length === 1) {
      label.textContent = CERT_LABELS[checked[0].value] || '정부인증 1개';
    } else {
      label.textContent = '정부인증 ' + checked.length + '개 선택';
    }
  }

  // 페이지 로드 시 URL 파라미터로 체크 상태 복원
  new URLSearchParams(window.location.search).getAll('cert').forEach(function (v) {
    var cb = document.querySelector('.cert-cb[value="' + v + '"]');
    if (cb) cb.checked = true;
  });
  updateLabel();

  // 토글
  btn.addEventListener('click', function (e) {
    e.stopPropagation();
    dropdown.classList.toggle('open');
  });

  // 체크 변경 시 라벨 갱신
  document.querySelectorAll('.cert-cb').forEach(function (cb) {
    cb.addEventListener('change', updateLabel);
  });

  // 외부 클릭 시 닫기
  document.addEventListener('click', function (e) {
    if (!wrap.contains(e.target)) dropdown.classList.remove('open');
  });
})();


// ── 검색/필터 UI ─────────────────────────────────────────────
(function () {
  'use strict';

  var searchInput = document.getElementById('filter-search');
  var searchBtn   = document.getElementById('btn-filter-search');
  var section     = document.getElementById('restaurant-section');

  if (!searchBtn) return;

  function buildParams(pageOverride) {
    var params = readFilterParams();
    if (pageOverride) params.set('page', pageOverride);
    return params;
  }

  function navigate(params) {
    var qs  = params.toString();
    var url = window.location.pathname + (qs ? '?' + qs : '');
    history.pushState(null, '', url);

    if (!section) { window.location.href = url; return; }

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
          document.dispatchEvent(new CustomEvent('restaurantSectionUpdated'));
        }
      })
      .catch(function () { window.location.href = url; })
      .finally(function () { section.classList.remove('loading'); });
  }

  function doSearch() { navigate(buildParams(null)); }

  // 페이지네이션 클릭 (이벤트 위임)
  document.addEventListener('click', function (e) {
    var a = e.target.closest('#pagination a.page-btn');
    if (!a) return;
    e.preventDefault();
    navigate(buildParams(new URL(a.href).searchParams.get('page')));
  });

  searchBtn.addEventListener('click', doSearch);
  if (searchInput) {
    searchInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') doSearch();
    });
  }

  // 행 클릭 → 상세 페이지 (이벤트 위임)
  document.addEventListener('click', function (e) {
    if (e.target.closest('#pagination') || e.target.closest('#filter-bar')) return;
    if (e.target.closest('a')) return;
    var row = e.target.closest('tbody tr[data-href]');
    if (row) window.location.href = row.dataset.href;
  });

  window.addEventListener('popstate', function () { window.location.reload(); });
})();


// ── 카카오 지도 ───────────────────────────────────────────────
(function () {
  if (typeof kakao === 'undefined' || typeof kakao.maps === 'undefined') return;

  var container = document.getElementById('kakao-map');
  if (!container) return;

  // ── 지도 초기화 ──────────────────────────────────────────
  var MAP_DEFAULT_CENTER = { lat: 37.5665, lng: 126.9780 };
  var MAP_DEFAULT_LEVEL  = 8;
  var CLUSTER_MIN_LEVEL  = 4;
  var CLUSTER_GRID_SIZE  = 120;
  var DBLCLICK_ZOOM_LEVEL = 6;
  var IDLE_DEBOUNCE_MS   = 600;
  var INIT_DELAY_MS      = 500;

  var kakaoMap = new kakao.maps.Map(container, {
    center: new kakao.maps.LatLng(MAP_DEFAULT_CENTER.lat, MAP_DEFAULT_CENTER.lng),
    level : MAP_DEFAULT_LEVEL,
  });

  // ── 마커 이미지 ──────────────────────────────────────────
  var MARKER_BLUE  = { color: '#4A90E2', w: 17, h: 25 };
  var MARKER_PINK  = { color: '#FF69B4', w: 24, h: 34 };
  var MARKER_HEART = { normal: 28, hover: 36 };

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

  var imgBlue      = makeMarkerImage(MARKER_BLUE.color,  MARKER_BLUE.w,  MARKER_BLUE.h);
  var imgPink      = makeMarkerImage(MARKER_PINK.color,  MARKER_PINK.w,  MARKER_PINK.h);
  var imgHeart     = makeHeartImage(MARKER_HEART.normal);
  var imgHeartHover= makeHeartImage(MARKER_HEART.hover);

  // ── 북마크 PK ────────────────────────────────────────────
  function readBookmarkedPks() {
    var el = document.getElementById('bookmarked-pks');
    try { return new Set(JSON.parse(el ? el.textContent : '[]')); } catch (e) { return new Set(); }
  }
  var bookmarkedPks = readBookmarkedPks();

  // ── 클러스터러 ───────────────────────────────────────────
  var clusterer = new kakao.maps.MarkerClusterer({
    map          : kakaoMap,
    averageCenter: true,
    minLevel     : CLUSTER_MIN_LEVEL,
    gridSize     : CLUSTER_GRID_SIZE,
  });

  // ── 마커 관리 ────────────────────────────────────────────
  var markers  = [];
  var overlays = [];

  function clearMarkers() {
    clusterer.clear();
    overlays.forEach(function (o) { o.setMap(null); });
    markers  = [];
    overlays = [];
  }

  function addMarkers(data) {
    clearMarkers();
    data.forEach(function (r) {
      var pos          = new kakao.maps.LatLng(r.lat, r.lng);
      var isBookmarked = bookmarkedPks.has(r.pk);
      var defaultImg   = isBookmarked ? imgHeart      : imgBlue;
      var hoverImg     = isBookmarked ? imgHeartHover : imgPink;
      var marker  = new kakao.maps.Marker({ position: pos, image: defaultImg });
      var overlay = new kakao.maps.CustomOverlay({
        map     : null,
        position: pos,
        content : '<div class="map-label">' + r.name + '</div>',
        yAnchor : isBookmarked ? 1.8 : 2.6,
      });

      kakao.maps.event.addListener(marker, 'mouseover', function () {
        marker.setImage(hoverImg);
        overlay.setMap(kakaoMap);
      });
      kakao.maps.event.addListener(marker, 'mouseout', function () {
        marker.setImage(defaultImg);
        overlay.setMap(null);
      });
      kakao.maps.event.addListener(marker, 'click', function () {
        window.location.href = RESTAURANT_BASE + r.pk + '/';
      });

      markers.push(marker);
      overlays.push(overlay);
    });
    clusterer.addMarkers(markers);
  }

  // ── 현재 bounds를 params에 추가 ──────────────────────────
  function addBoundsToParams(params) {
    var bounds = kakaoMap.getBounds();
    var sw     = bounds.getSouthWest();
    var ne     = bounds.getNorthEast();
    params.set('sw_lat', sw.getLat().toFixed(6));
    params.set('sw_lng', sw.getLng().toFixed(6));
    params.set('ne_lat', ne.getLat().toFixed(6));
    params.set('ne_lng', ne.getLng().toFixed(6));
    return params;
  }

  // 필터 + bounds 통합 파라미터
  function buildBoundsParams() {
    return addBoundsToParams(readFilterParams());
  }

  // ── 마커 API 호출 ────────────────────────────────────────
  function fetchAndRenderMarkers() {
    fetch(MAP_MARKERS_URL + '?' + buildBoundsParams().toString())
      .then(function (res) { return res.json(); })
      .then(function (data) { addMarkers(data.markers || []); })
      .catch(function () {});
  }

  // ── 리스트 섹션 fetch + DOM 교체 ─────────────────────────
  function fetchSection(url, dispatchEvent) {
    var section = document.getElementById('restaurant-section');
    if (section) section.classList.add('loading');
    fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (res) { return res.text(); })
      .then(function (html) {
        var doc        = new DOMParser().parseFromString(html, 'text/html');
        var newSection = doc.getElementById('restaurant-section');
        if (newSection && section) {
          section.innerHTML = newSection.innerHTML;
          if (dispatchEvent) {
            document.dispatchEvent(new CustomEvent('restaurantSectionUpdated'));
          }
        }
      })
      .finally(function () {
        if (section) section.classList.remove('loading');
      });
  }

  // ── 초기 로드: 현재 지도 범위로 리스트 갱신 ─────────────
  function fetchByBounds() {
    var params = buildBoundsParams();
    var url    = window.location.pathname + '?' + params.toString();
    history.replaceState(null, '', url);
    fetchSection(url, true);
  }

  setTimeout(fetchByBounds, INIT_DELAY_MS);

  // ── 시/도별 지도 중심·레벨 ──────────────────────────────
  var PROVINCE_CENTER = {
    '서울특별시'    : { lat: 37.5665, lng: 126.9780, level: 8  },
    '경기도'        : { lat: 37.4138, lng: 127.5183, level: 10 },
    '인천광역시'    : { lat: 37.4563, lng: 126.7052, level: 9  },
    '강원특별자치도': { lat: 37.8228, lng: 128.1555, level: 10 },
    '충청북도'      : { lat: 36.6358, lng: 127.4914, level: 10 },
    '충청남도'      : { lat: 36.6588, lng: 126.6728, level: 10 },
    '대전광역시'    : { lat: 36.3504, lng: 127.3845, level: 8  },
    '세종특별자치시': { lat: 36.4801, lng: 127.2890, level: 9  },
    '전북특별자치도': { lat: 35.7175, lng: 127.1530, level: 10 },
    '전라남도'      : { lat: 34.8679, lng: 126.9910, level: 10 },
    '광주광역시'    : { lat: 35.1595, lng: 126.8526, level: 8  },
    '경상북도'      : { lat: 36.4919, lng: 128.8889, level: 10 },
    '경상남도'      : { lat: 35.4606, lng: 128.2132, level: 10 },
    '대구광역시'    : { lat: 35.8714, lng: 128.6014, level: 8  },
    '울산광역시'    : { lat: 35.5384, lng: 129.3114, level: 8  },
    '부산광역시'    : { lat: 35.1796, lng: 129.0756, level: 8  },
    '제주특별자치도': { lat: 33.4996, lng: 126.5312, level: 9  },
  };

  // ── 검색 완료 이벤트: province 변경 시 지도 이동 ────────
  var lastProvince = '';
  var lastDistrict = '';

  function fitMapToGeoData() {
    var geoEl   = document.getElementById('restaurant-geo-data');
    var geoData = [];
    try { geoData = JSON.parse(geoEl ? geoEl.textContent : '[]'); } catch (e) {}
    var valid = geoData.filter(function (r) { return r.lat && r.lng; });

    if (valid.length === 0) {
      clearMarkers();
    } else if (valid.length === 1) {
      kakaoMap.setCenter(new kakao.maps.LatLng(valid[0].lat, valid[0].lng));
      kakaoMap.setLevel(5);
      fetchAndRenderMarkers();
    } else {
      var fitBounds = new kakao.maps.LatLngBounds();
      valid.forEach(function (r) {
        fitBounds.extend(new kakao.maps.LatLng(r.lat, r.lng));
      });
      kakaoMap.setBounds(fitBounds);
      fetchAndRenderMarkers();
    }
  }

  document.addEventListener('restaurantSectionUpdated', function () {
    var pr = document.getElementById('filter-province');
    var di = document.getElementById('filter-district');
    var pv = pr ? pr.value : '';
    var dv = di ? di.value : '';

    if (pv && pv !== lastProvince && PROVINCE_CENTER[pv]) {
      // 시/도 변경 → 시/도 중심으로 이동
      lastProvince = pv;
      lastDistrict = dv;
      var c = PROVINCE_CENTER[pv];
      kakaoMap.setCenter(new kakao.maps.LatLng(c.lat, c.lng));
      kakaoMap.setLevel(c.level);
      // idle 이벤트가 마커를 자동 갱신
    } else if (dv !== lastDistrict) {
      // 구/군 변경 → 결과 geo-data 기반으로 지도 이동
      lastProvince = pv;
      lastDistrict = dv;
      fitMapToGeoData();
    } else {
      lastProvince = pv;
      lastDistrict = dv;
      var si        = document.getElementById('filter-search');
      var searchVal = si ? si.value.trim() : '';

      if (searchVal) {
        fitMapToGeoData();
      } else {
        fetchAndRenderMarkers();
      }
    }
  });

  // ── 초기 검색어가 있으면 즉시 결과 위치로 지도 이동 ─────────
  (function initSearchPosition() {
    var si = document.getElementById('filter-search');
    if (!si || !si.value.trim()) return;
    var geoEl   = document.getElementById('restaurant-geo-data');
    var geoData = [];
    try { geoData = JSON.parse(geoEl ? geoEl.textContent : '[]'); } catch (e) {}
    var valid = geoData.filter(function (r) { return r.lat && r.lng; });
    if (valid.length === 0) return;
    if (valid.length === 1) {
      kakaoMap.setCenter(new kakao.maps.LatLng(valid[0].lat, valid[0].lng));
      kakaoMap.setLevel(5);
    } else {
      var fb = new kakao.maps.LatLngBounds();
      valid.forEach(function (r) { fb.extend(new kakao.maps.LatLng(r.lat, r.lng)); });
      kakaoMap.setBounds(fb);
    }
    fetchAndRenderMarkers();
  })();

  // ── 더블클릭 줌인 ────────────────────────────────────────
  kakao.maps.event.addListener(kakaoMap, 'dblclick', function (mouseEvent) {
    kakaoMap.setCenter(mouseEvent.latLng);
    kakaoMap.setLevel(DBLCLICK_ZOOM_LEVEL);
  });

  // ── 지도 이동/줌 → 리스트 + 마커 갱신 (디바운스) ───────
  var boundsTimer = null;
  kakao.maps.event.addListener(kakaoMap, 'idle', function () {
    clearTimeout(boundsTimer);
    boundsTimer = setTimeout(function () {
      var params = buildBoundsParams();
      var url    = window.location.pathname + '?' + params.toString();
      history.pushState(null, '', url);
      fetchSection(url, false);
      fetchAndRenderMarkers();
    }, IDLE_DEBOUNCE_MS);
  });
})();

// ── 시/도 변경 시 구/군 목록 동적 로드 ──────────────────────
(function () {
  var provinceEl = document.getElementById('filter-province');
  var districtEl = document.getElementById('filter-district');
  if (!provinceEl || !districtEl) return;

  function loadDistricts(province, selectedDistrict) {
    districtEl.innerHTML = '<option value="">구/군</option>';
    if (!province) {
      districtEl.disabled = true;
      return;
    }
    fetch(DISTRICT_URL + '?province=' + encodeURIComponent(province))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        data.districts.forEach(function (d) {
          var opt = document.createElement('option');
          opt.value = d;
          opt.textContent = d;
          if (d === selectedDistrict) opt.selected = true;
          districtEl.appendChild(opt);
        });
        districtEl.disabled = false;
      });
  }

  provinceEl.addEventListener('change', function () {
    loadDistricts(provinceEl.value, '');
  });

  // 페이지 로드 시 시/도가 이미 선택된 경우 구 목록 복원
  if (provinceEl.value) {
    var currentDistrict = new URLSearchParams(location.search).get('district') || '';
    loadDistricts(provinceEl.value, currentDistrict);
  }
})();
