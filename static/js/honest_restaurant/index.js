document.addEventListener('DOMContentLoaded', function () {
  var meta     = document.getElementById('index-meta');
  var isAuth   = meta.dataset.authenticated === 'true';
  var loginUrl = meta.dataset.loginUrl;
  var listUrl  = '/restaurants/';

  // ── 검색 버튼 ────────────────────────────────────
  var searchBtn   = document.getElementById('btn-index-search');
  var searchInput = document.getElementById('index-search-input');

  function doIndexSearch() {
    if (!isAuth) {
      location.href = loginUrl + '?next=' + listUrl;
      return;
    }
    var q = searchInput ? searchInput.value.trim() : '';
    location.href = listUrl + (q ? '?search=' + encodeURIComponent(q) : '');
  }

  if (searchBtn) searchBtn.addEventListener('click', doIndexSearch);
  if (searchInput) {
    searchInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') doIndexSearch();
    });
  }

  // ── 섹션 전환 ────────────────────────────────────
  window.show = function (n) {
    if (!isAuth && (n === 'detail' || n === 'receipt')) {
      location.href = loginUrl + '?next=/';
      return;
    }
    ['home', 'detail', 'receipt', 'owner', 'mkt-manage'].forEach(function (s) {
      document.getElementById('s-' + s).style.display = s === n ? 'block' : 'none';
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  if (new URLSearchParams(location.search).get('owner') === '1') {
    show('owner');
  }
});
