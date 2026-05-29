/* ── 마케팅 대시보드 JS ── */

// restaurant_id: 대시보드 index-meta 태그에서 읽음
const _meta = document.getElementById('index-meta');
const RESTAURANT_ID = _meta ? parseInt(_meta.dataset.restaurantId, 10) || null : null;

// SNS 연동 여부 — 관리 페이지 인라인 스크립트(window.SNS_CONNECTED)로 주입, 기본값 false
if (typeof window.SNS_CONNECTED === 'undefined') window.SNS_CONNECTED = false;
const SNS_CONNECTED = window.SNS_CONNECTED;

// DB 연동 게시물 목록 (페이지 로드 시 API로 채워짐)
let mktPosts = [];
let currentPost = null;
let selectedPlatform = 'instagram';

function getCsrf() {
  const c = document.cookie.split(';').map(s => s.trim()).find(s => s.startsWith('csrftoken='));
  return c ? c.split('=')[1] : '';
}

async function fetchPosts() {
  const url = RESTAURANT_ID
    ? `/marketing/api/posts/?restaurant_id=${RESTAURANT_ID}`
    : `/marketing/api/posts/`;
  try {
    const res = await fetch(url);
    if (!res.ok) return;
    mktPosts = await res.json();
    renderHistory();
    updateManageCounts();
  } catch (e) {
    console.error('게시물 목록 로드 실패', e);
  }
}

// 플랫폼 라벨 맵 — 템플릿에서 json_script로 전달
const _platformData = JSON.parse(document.getElementById('mkt-platform-data')?.textContent || '[]');
const PLATFORM_LABEL = Object.fromEntries(_platformData.map(p => [p.platform, p.display_name]));

// 존재하는 요소에만 이벤트 등록하는 헬퍼
function on(id, event, fn) {
  const el = document.getElementById(id);
  if (el) el.addEventListener(event, fn);
}

// ── 모달 열기/닫기 ─────────────────────────────────────
on('btn-mkt-open',  'click', () => openModal());   // 대시보드 생성 버튼
on('btn-mkt-open2', 'click', () => openModal());   // 관리 페이지 생성 버튼
on('btn-mkt-close', 'click', closeModal);
on('mktOverlay',    'click', (e) => { if (e.target === e.currentTarget) closeModal(); });

// ── 관리 페이지 필터 탭 ────────────────────────────────
document.querySelectorAll('.mmf-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.mmf-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderManageTable(btn.dataset.filter);
  });
});

// ── SNS 계정 연동 버튼 ────────────────────────────────
on('btn-sns-connect', 'click', () => {
  if (SNS_CONNECTED) return;
  toast('SNS 계정 연동 기능은 준비 중입니다.');
});

function openModal(postData = null) {
  const overlay = document.getElementById('mktOverlay');
  overlay.classList.add('open');
  document.body.style.overflow = 'hidden';

  if (postData) {
    // 수정 모드
    currentPost = postData;
    document.getElementById('mkt-edit-area').value = postData.final_content || postData.generated_content || '';
    document.getElementById('mkt-tags-row').value = (postData.hashtags || []).join(', ');
    setSelectedPlatform(postData.platform);
    showStep(3);
  } else {
    // 생성 모드
    currentPost = null;
    document.getElementById('mkt-input').value = '';
    setSelectedPlatform('instagram');
    showStep(1);
  }
}

function closeModal() {
  document.getElementById('mktOverlay').classList.remove('open');
  document.body.style.overflow = '';

  if (document._mktReturnToManage) {
    document._mktReturnToManage = false;
    show('mkt-manage');
    renderManageTable(document.querySelector('.mmf-btn.active')?.dataset.filter || 'all');
  }
}

// ── 단계 전환 ──────────────────────────────────────────
function showStep(n) {
  document.querySelectorAll('.mkt-step').forEach(el => el.classList.remove('active'));
  document.getElementById(`mkt-step-${n}`).classList.add('active');
}

// ── 플랫폼 선택 (모달) ─────────────────────────────────
document.querySelectorAll('.platform-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    setSelectedPlatform(btn.dataset.p);
  });
});

function setSelectedPlatform(platform) {
  selectedPlatform = platform;
  document.querySelectorAll('.platform-btn').forEach(b => {
    b.classList.toggle('selected', b.dataset.p === platform);
  });
}

// ── 대시보드 인라인 플랫폼 선택 ────────────────────────
let inlineSelectedPlatform = null;

document.querySelectorAll('.mkt-inline-plat-btn').forEach(btn => {
  if (!inlineSelectedPlatform && btn.classList.contains('selected')) {
    inlineSelectedPlatform = btn.dataset.p;
  }
  btn.addEventListener('click', () => {
    document.querySelectorAll('.mkt-inline-plat-btn').forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');
    inlineSelectedPlatform = btn.dataset.p;
  });
});

// ── 대시보드 인라인 AI 글 생성 ─────────────────────────
on('btn-mkt-inline-generate', 'click', async () => {
  const input = document.getElementById('mkt-inline-input')?.value.trim();
  if (!input) { toast('키워드나 문장을 입력해 주세요.'); return; }
  if (!RESTAURANT_ID) { toast('식당 정보를 불러올 수 없습니다.'); return; }

  const overlay = document.getElementById('mktOverlay');
  overlay.classList.add('open');
  document.body.style.overflow = 'hidden';
  showStep(2);

  try {
    const res = await fetch('/marketing/api/posts/generate/', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
      body: JSON.stringify({
        restaurant_id: RESTAURANT_ID,
        input_prompt:  input,
        platform:      inlineSelectedPlatform || selectedPlatform,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const msg = err.detail || 'AI 글 생성에 실패했습니다.';
      toast(msg.length > 50 ? msg.slice(0, 50) + '…' : msg);
      overlay.classList.remove('open');
      document.body.style.overflow = '';
      return;
    }

    const post = await res.json();
    currentPost = post;

    document.getElementById('mkt-edit-area').value          = post.final_content;
    document.getElementById('mkt-tags-row').value           = post.hashtags.join(', ');
    showStep(3);

    document.getElementById('mkt-inline-input').value = '';
    await fetchPosts();

  } catch (e) {
    console.error(e);
    toast('네트워크 오류가 발생했습니다.');
    overlay.classList.remove('open');
    document.body.style.overflow = '';
  }
});

// ── AI 글 생성 (모달) ──────────────────────────────────
document.getElementById('btn-mkt-generate').addEventListener('click', async () => {
  const input = document.getElementById('mkt-input').value.trim();
  if (!input) { toast('키워드나 문장을 입력해 주세요.'); return; }
  if (!RESTAURANT_ID) { toast('식당 정보를 불러올 수 없습니다.'); return; }

  showStep(2);  // 생성 중 화면

  try {
    const res = await fetch('/marketing/api/posts/generate/', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
      body: JSON.stringify({
        restaurant_id: RESTAURANT_ID,
        input_prompt:  input,
        platform:      selectedPlatform,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const msg = err.detail || 'AI 글 생성에 실패했습니다.';
      toast(msg.length > 50 ? msg.slice(0, 50) + '…' : msg);
      showStep(1);
      return;
    }

    const post = await res.json();
    currentPost = post;

    document.getElementById('mkt-edit-area').value         = post.final_content;
    document.getElementById('mkt-tags-row').value          = post.hashtags.join(', ');
    showStep(3);

  } catch (e) {
    console.error(e);
    toast('네트워크 오류가 발생했습니다.');
    showStep(1);
  }
});

// ── 글 복사하기 ────────────────────────────────────────
on('btn-mkt-copy', 'click', () => {
  const body = document.getElementById('mkt-edit-area').value;
  const tags = document.getElementById('mkt-tags-row').value;
  const text = tags ? `${body}\n\n${tags}` : body;
  if (!text.trim()) { toast('복사할 내용이 없습니다.'); return; }
  navigator.clipboard.writeText(text)
    .then(() => toast('클립보드에 복사되었습니다!'))
    .catch(() => {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.cssText = 'position:fixed;opacity:0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      toast('클립보드에 복사되었습니다!');
    });
});

async function apiPublish(postId, scheduledAt) {
  // 내용 수정분을 먼저 PATCH로 저장
  await fetch(`/marketing/api/posts/${postId}/`, {
    method:  'PATCH',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
    body: JSON.stringify({ final_content: document.getElementById('mkt-edit-area').value }),
  });

  const body = scheduledAt ? { scheduled_at: scheduledAt } : {};
  const res = await fetch(`/marketing/api/posts/${postId}/publish/`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    toast(err.detail || '발행에 실패했습니다.');
    return false;
  }
  return true;
}

// ── 이력 카드: 수정 ────────────────────────────────────
function mktEdit(postId) {
  const post = mktPosts.find(p => p.id === postId);
  if (post) openModal(post);
}

// ── 삭제 버튼 ──────────────────────────────────────────
async function mktDelete(postId) {
  await fetch(`/marketing/api/posts/${postId}/`, {
    method: 'DELETE', headers: { 'X-CSRFToken': getCsrf() },
  });
  await fetchPosts();
  toast('삭제되었습니다.');
}

// ── 게시물 저장 및 렌더링 ─────────────────────────────
function getEditedPost() {
  return {
    ...currentPost,
    final_content: document.getElementById('mkt-edit-area').value,
  };
}

// ── 관리 페이지 카운트 뱃지 갱신 ─────────────────────
function updateManageCounts() {
  const counts = { all: mktPosts.length, draft: 0, scheduled: 0, published: 0, failed: 0 };
  mktPosts.forEach(p => { if (counts[p.status] !== undefined) counts[p.status]++; });
  Object.keys(counts).forEach(k => {
    const el = document.getElementById(`cnt-${k}`);
    if (el) el.textContent = counts[k];
  });
}

// ── 관리 테이블 렌더 (페이지네이션 포함) ──────────────
const PAGE_SIZE = 10;
let currentPage = 1;
let currentFilter = 'all';

function renderManageTable(filter, page = 1) {
  currentFilter = filter;
  currentPage   = page;
  updateManageCounts();

  const tbody    = document.getElementById('mkt-manage-body');
  const filtered = filter === 'all' ? mktPosts : mktPosts.filter(p => p.status === filter);

  if (!filtered.length) {
    const cols = SNS_CONNECTED ? 5 : 3;
    tbody.innerHTML = `<tr><td colspan="${cols}" class="mmw-empty">${filter === 'all' ? '아직 작성된 글이 없습니다.' : '해당 상태의 글이 없습니다.'}</td></tr>`;
    renderPagination(0, 1);
    return;
  }

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const safePage   = Math.min(Math.max(page, 1), totalPages);
  const start      = (safePage - 1) * PAGE_SIZE;
  const pageItems  = filtered.slice(start, start + PAGE_SIZE);

  const STATUS_LABEL = { draft: '임시저장', scheduled: '예약', published: '발행완료', failed: '실패' };

  tbody.innerHTML = pageItems.map(p => {
    const dateStr = p.published_at
      ? formatDatetimeFull(new Date(p.published_at))
      : p.scheduled_at
        ? formatDatetimeFull(new Date(p.scheduled_at))
        : formatDatetimeFull(new Date(p.created_at));

    const publishBtn = SNS_CONNECTED && p.status !== 'published'
      ? `<button class="btn-pub" onclick="mktPublishFromManage(${p.id})">즉시발행</button>`
      : '';

    const platCols = SNS_CONNECTED
      ? `<td><span class="mmw-plat-badge ${p.platform}">${PLATFORM_LABEL[p.platform]}</span></td>
         <td><span class="mmw-status ${p.status}">${STATUS_LABEL[p.status] || p.status}</span></td>`
      : '';

    return `
      <tr>
        ${platCols}
        <td><div class="mmw-date">${dateStr}</div></td>
        <td><div class="mmw-content-preview">${escHtml(p.final_content || '')}</div></td>
        <td>
          <div class="mmw-actions">
            <button onclick="mktEditFromManage(${p.id})">수정</button>
            ${publishBtn}
            <button class="btn-del" onclick="mktDeleteFromManage(${p.id})">삭제</button>
          </div>
        </td>
      </tr>`;
  }).join('');

  renderPagination(totalPages, safePage);
}

function renderPagination(totalPages, activePage) {
  const wrap = document.getElementById('mmw-pagination');
  if (!wrap) return;
  if (totalPages <= 1) { wrap.innerHTML = ''; return; }

  const prev = `<button class="mmw-page-btn" onclick="renderManageTable('${currentFilter}',${activePage - 1})" ${activePage === 1 ? 'disabled' : ''}>‹</button>`;
  const next = `<button class="mmw-page-btn" onclick="renderManageTable('${currentFilter}',${activePage + 1})" ${activePage === totalPages ? 'disabled' : ''}>›</button>`;

  const nums = Array.from({ length: totalPages }, (_, i) => i + 1).map(n =>
    `<button class="mmw-page-btn${n === activePage ? ' active' : ''}" onclick="renderManageTable('${currentFilter}',${n})">${n}</button>`
  ).join('');

  wrap.innerHTML = prev + nums + next;
}

// ── 관리 페이지에서 수정 ──────────────────────────────
function mktEditFromManage(postId) {
  const post = mktPosts.find(p => p.id === postId);
  if (post) {
    openModal(post);
    document._mktReturnToManage = true;
  }
}

// ── 관리 페이지에서 즉시발행 ─────────────────────────
async function mktPublishFromManage(postId) {
  const ok = await apiPublish(postId, null);
  if (ok) {
    toast('발행 완료!');
    await fetchPosts();
    renderManageTable(document.querySelector('.mmf-btn.active')?.dataset.filter || 'all');
  }
}

// ── 관리 페이지에서 삭제 ──────────────────────────────
async function mktDeleteFromManage(postId) {
  await fetch(`/marketing/api/posts/${postId}/`, {
    method: 'DELETE', headers: { 'X-CSRFToken': getCsrf() },
  });
  toast('삭제되었습니다.');
  await fetchPosts();
  renderManageTable(document.querySelector('.mmf-btn.active')?.dataset.filter || 'all');
}

function renderHistory() {
  const container = document.getElementById('mkt-history');
  if (!container) return;

  if (!mktPosts.length) {
    container.innerHTML = '<p style="font-size:12px;color:var(--muted);padding:12px 0;">+ 생성 버튼을 눌러 첫 번째 마케팅 글을 만들어보세요.</p>';
    return;
  }

  // 대시보드에는 플랫폼 + 상태/일시만 한 줄로 표시 — 클릭하면 모달 재오픈
  container.innerHTML = `<ul class="mkt-summary-list">` +
    mktPosts.map(p => {
      const timeInfo = p.published_at
        ? `발행 · ${formatDatetime(new Date(p.published_at))}`
        : p.scheduled_at
          ? `예약 · ${formatDatetime(new Date(p.scheduled_at))}`
          : '임시저장';
      return `
        <li class="mkt-summary-item" onclick="mktEdit(${p.id})">
          <span class="mkt-badge ${p.platform}">${PLATFORM_LABEL[p.platform] || p.platform}</span>
          <span class="mkt-summary-time ${p.status}">${timeInfo}</span>
          <span class="mkt-summary-arrow">›</span>
        </li>`;
    }).join('') +
  `</ul>`;
}

// ── 유틸 ──────────────────────────────────────────────

function getCsrf() {
  return document.cookie.split(';').map(c => c.trim()).find(c => c.startsWith('csrftoken='))?.split('=')[1] || '';
}

function toast(msg) {
  const el = document.getElementById('mktToast');
  el.textContent = msg;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 2400);
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>');
}

function toLocalDatetimeString(d) {
  const pad = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function formatDatetime(d) {
  const pad = n => String(n).padStart(2, '0');
  return `${d.getMonth()+1}/${d.getDate()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function formatDatetimeFull(d) {
  const pad = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}.${pad(d.getMonth()+1)}.${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/* ── 초기화 ── */
document.addEventListener('DOMContentLoaded', function () {
  // 대시보드 또는 관리 페이지 로드 시 DB에서 게시물 목록 가져오기
  fetchPosts().then(() => {
    if (document.getElementById('mkt-manage-body')) {
      renderManageTable('all');
    }
  });
});
