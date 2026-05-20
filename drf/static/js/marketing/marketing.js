/* ── 마케팅 대시보드 JS ── */

// localStorage로 페이지 간 데이터 유지 (API 연동 전 테스트용)
const STORAGE_KEY = 'mkt_posts';

function loadPosts() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || []; }
  catch { return []; }
}
function persistPosts() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(mktPosts));
}

const mktPosts = loadPosts();
let currentPost = null;
let selectedPlatform = 'instagram';

const PLATFORM_LABEL = {
  instagram:   'Instagram',
  facebook:    'Facebook',
  naver_blog:  '네이버 블로그',
  kakao_story: '카카오스토리',
};

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

function openModal(postData = null) {
  const overlay = document.getElementById('mktOverlay');
  overlay.classList.add('open');
  document.body.style.overflow = 'hidden';

  if (postData) {
    // 수정 모드
    currentPost = postData;
    document.getElementById('mkt-edit-area').value = postData.content;
    document.getElementById('mkt-tags-row').textContent = postData.hashtags.join(' ');
    document.getElementById('mkt-result-plat').textContent = PLATFORM_LABEL[postData.platform];
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
  document.getElementById('mkt-schedule-box').classList.remove('open');

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

// ── 플랫폼 선택 ────────────────────────────────────────
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

// ── AI 글 생성 ─────────────────────────────────────────
document.getElementById('btn-mkt-generate').addEventListener('click', async () => {
  const input = document.getElementById('mkt-input').value.trim();
  if (!input) {
    toast('키워드나 문장을 입력해 주세요.');
    return;
  }

  showStep(2);

  // TODO: 실제 API 호출로 교체
  // const res = await fetch('/api/marketing/posts/generate/', {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
  //   body: JSON.stringify({ restaurant_id: 1, input_prompt: input, platform: selectedPlatform }),
  // });
  // const data = await res.json();

  // 테스트용 Mock AI 응답 (1.5초 지연)
  await delay(1500);
  const mockData = generateMockContent(input, selectedPlatform);

  currentPost = {
    id: Date.now(),
    platform: selectedPlatform,
    input_prompt: input,
    content: mockData.content,
    hashtags: mockData.hashtags,
    status: 'draft',
    created_at: new Date().toISOString(),
  };

  document.getElementById('mkt-edit-area').value = currentPost.content;
  document.getElementById('mkt-tags-row').textContent = currentPost.hashtags.join(' ');
  document.getElementById('mkt-result-plat').textContent = PLATFORM_LABEL[selectedPlatform];
  document.getElementById('mkt-schedule-box').classList.remove('open');
  showStep(3);
});

// ── 다시 작성 ──────────────────────────────────────────
document.getElementById('btn-mkt-back').addEventListener('click', () => {
  showStep(1);
});

// ── 예약 발행 토글 ────────────────────────────────────
document.getElementById('btn-schedule').addEventListener('click', () => {
  const box = document.getElementById('mkt-schedule-box');
  box.classList.toggle('open');
  if (box.classList.contains('open')) {
    // 기본값: 오늘 오후 6시
    const d = new Date();
    d.setHours(18, 0, 0, 0);
    document.getElementById('mkt-datetime').value = toLocalDatetimeString(d);
  }
});

// ── 예약 확정 ──────────────────────────────────────────
document.getElementById('btn-schedule-confirm').addEventListener('click', () => {
  const dt = document.getElementById('mkt-datetime').value;
  if (!dt) { toast('날짜와 시간을 선택해 주세요.'); return; }

  const scheduled = new Date(dt);
  savePost({ ...getEditedPost(), status: 'scheduled', scheduled_at: scheduled });
  toast(`${formatDatetime(scheduled)} 예약 완료`);
  closeModal();
});

// ── 즉시 발행 ──────────────────────────────────────────
document.getElementById('btn-publish-now').addEventListener('click', () => {
  savePost({ ...getEditedPost(), status: 'published', published_at: new Date() });
  toast('발행 완료!');
  closeModal();
});

// ── 이력 카드: 수정 ────────────────────────────────────
function mktEdit(postId) {
  const post = mktPosts.find(p => p.id === postId);
  if (post) openModal(post);
}

// ── 삭제 버튼 ──────────────────────────────────────────
function mktDelete(postId) {
  const idx = mktPosts.findIndex(p => p.id === postId);
  if (idx !== -1) {
    mktPosts.splice(idx, 1);
    persistPosts();
    renderHistory();
    toast('삭제되었습니다.');
  }
}

// ── 게시물 저장 및 렌더링 ─────────────────────────────
function getEditedPost() {
  return {
    ...currentPost,
    content: document.getElementById('mkt-edit-area').value,
  };
}

function savePost(post) {
  const idx = mktPosts.findIndex(p => p.id === post.id);
  if (idx !== -1) {
    mktPosts[idx] = post;
  } else {
    mktPosts.unshift(post);
  }
  persistPosts();
  renderHistory();
  updateManageCounts();
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

// ── 관리 테이블 렌더 ──────────────────────────────────
function renderManageTable(filter) {
  updateManageCounts();
  const tbody = document.getElementById('mkt-manage-body');
  const filtered = filter === 'all' ? mktPosts : mktPosts.filter(p => p.status === filter);

  if (!filtered.length) {
    tbody.innerHTML = `<tr><td colspan="5" class="mmw-empty">${filter === 'all' ? '아직 작성된 글이 없습니다.' : '해당 상태의 글이 없습니다.'}</td></tr>`;
    return;
  }

  const STATUS_LABEL = { draft: '임시저장', scheduled: '예약', published: '발행완료', failed: '실패' };

  tbody.innerHTML = filtered.map(p => {
    const dateStr = p.published_at
      ? `발행 ${formatDatetime(new Date(p.published_at))}`
      : p.scheduled_at
        ? `예약 ${formatDatetime(new Date(p.scheduled_at))}`
        : `작성 ${formatDatetime(new Date(p.created_at))}`;

    const publishBtn = p.status !== 'published'
      ? `<button class="btn-pub" onclick="mktPublishFromManage(${p.id})">즉시발행</button>`
      : '';

    return `
      <tr>
        <td><span class="mmw-plat-badge ${p.platform}">${PLATFORM_LABEL[p.platform]}</span></td>
        <td><span class="mmw-status ${p.status}">${STATUS_LABEL[p.status] || p.status}</span></td>
        <td><div class="mmw-content-preview">${escHtml(p.content)}</div></td>
        <td><div class="mmw-date">${dateStr}</div></td>
        <td>
          <div class="mmw-actions">
            <button onclick="mktEditFromManage(${p.id})">수정</button>
            ${publishBtn}
            <button class="btn-del" onclick="mktDeleteFromManage(${p.id})">삭제</button>
          </div>
        </td>
      </tr>`;
  }).join('');
}

// ── 관리 페이지에서 수정 ──────────────────────────────
function mktEditFromManage(postId) {
  const post = mktPosts.find(p => p.id === postId);
  if (post) {
    openModal(post);
    // 모달 닫힌 후 관리 페이지로 복귀
    document._mktReturnToManage = true;
  }
}

// ── 관리 페이지에서 즉시발행 ─────────────────────────
function mktPublishFromManage(postId) {
  const post = mktPosts.find(p => p.id === postId);
  if (!post) return;
  savePost({ ...post, status: 'published', published_at: new Date() });
  toast('발행 완료!');
  renderManageTable(document.querySelector('.mmf-btn.active')?.dataset.filter || 'all');
}

// ── 관리 페이지에서 삭제 ──────────────────────────────
function mktDeleteFromManage(postId) {
  const idx = mktPosts.findIndex(p => p.id === postId);
  if (idx !== -1) {
    mktPosts.splice(idx, 1);
    persistPosts();
    renderHistory();
    toast('삭제되었습니다.');
    renderManageTable(document.querySelector('.mmf-btn.active')?.dataset.filter || 'all');
  }
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
          <span class="mkt-badge ${p.platform}">${PLATFORM_LABEL[p.platform]}</span>
          <span class="mkt-summary-time ${p.status}">${timeInfo}</span>
          <span class="mkt-summary-arrow">›</span>
        </li>`;
    }).join('') +
  `</ul>`;
}

// ── Mock AI 콘텐츠 생성 ───────────────────────────────
function generateMockContent(input, platform) {
  const templates = {
    instagram: [
      `오늘도 새벽 5시.\n${input}\n\n손님 한 분 한 분을 위해 오늘도 정성을 다하겠습니다. 많은 사랑 부탁드립니다 🙏`,
      `${input}\n\n20년 동안 변하지 않은 것, 정직한 가격과 진심.\n오늘도 익선동 골목에서 기다리고 있겠습니다.`,
    ],
    facebook: [
      `안녕하세요, 종로 골목 김밥집입니다.\n\n${input}\n\n오늘도 신선한 재료로 정성껏 준비했습니다. 맛있게 드시고 행복한 하루 보내세요!`,
    ],
    naver_blog: [
      `[오늘의 메뉴 소식]\n\n${input}\n\n저희 가게는 매일 아침 신선한 재료를 직접 손질합니다. 20년 전통의 맛을 오늘도 이어갑니다.\n\n많은 방문 부탁드립니다. 감사합니다.`,
    ],
    kakao_story: [
      `${input} ☕\n오늘도 맛있는 하루 되세요!`,
    ],
  };
  const arr = templates[platform] || templates.instagram;
  const content = arr[Math.floor(Math.random() * arr.length)];
  const hashtags = ['#정직식당', '#익선동맛집', '#LV3검증', '#골목장인'];
  return { content, hashtags };
}

// ── 유틸 ──────────────────────────────────────────────
function delay(ms) { return new Promise(r => setTimeout(r, ms)); }

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
