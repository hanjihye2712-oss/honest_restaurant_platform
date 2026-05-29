/**
 * 메뉴 관리 모달 — 다중 행 추가 / 수정 / 삭제 / 순서 변경
 * 의존: header.js (getCsrf), axios (CDN)
 */
(function () {
  'use strict';

  var overlay      = document.getElementById('mm-overlay');
  var panel        = document.getElementById('mm-panel');
  var closeBtn     = document.getElementById('mm-close');
  var list         = document.getElementById('mm-list');
  var emptyMsg     = document.getElementById('mm-empty');
  var form         = document.getElementById('mm-form');
  var rowsContainer= document.getElementById('mm-rows');
  var addRowBtn    = document.getElementById('mm-btn-add-row');
  var submitBtn    = document.getElementById('mm-btn-submit');

  if (!panel) return;

  var restaurantPk = panel.dataset.pk;
  var createUrl    = '/restaurants/' + restaurantPk + '/menu-items/';
  var reorderUrl   = '/restaurants/' + restaurantPk + '/menu-items/reorder/';

  var dataEl = document.getElementById('menu-data');
  var items  = dataEl ? JSON.parse(dataEl.textContent) : [];

  var editingPk  = null;
  var INIT_ROWS  = 3;
  var dragSrcIdx = null;

  // ── 모달 열기/닫기 ────────────────────────────────────────────

  function openModal() {
    editingPk = null;
    renderList();
    initRows();
    overlay.classList.add('open');
    panel.classList.add('open');
    panel.setAttribute('aria-hidden', 'false');
    setTimeout(function () { focusFirstEmpty(); }, 50);
  }

  function closeModal() {
    overlay.classList.remove('open');
    panel.classList.remove('open');
    panel.setAttribute('aria-hidden', 'true');
    editingPk = null;
  }

  // ── 입력 행 관리 ──────────────────────────────────────────────

  function initRows() {
    rowsContainer.innerHTML = '';
    for (var i = 0; i < INIT_ROWS; i++) addRow();
  }

  function addRow(name, price) {
    var div = document.createElement('div');
    div.className = 'mm-row-input';
    div.innerHTML =
      '<input class="mm-input mm-ri-name" type="text" placeholder="메뉴명 (예: 김밥)"' +
      ' maxlength="100" autocomplete="off"' + (name ? ' value="' + escAttr(name) + '"' : '') + '>' +
      '<input class="mm-input mm-ri-price" type="number" placeholder="가격(원)" min="0" step="100"' +
      (price !== undefined && price !== null ? ' value="' + price + '"' : '') + '>' +
      '<button type="button" class="mm-row-del" tabindex="-1">✕</button>';

    // 마지막 행의 가격 칸에서 Tab → 새 행 추가
    div.querySelector('.mm-ri-price').addEventListener('keydown', function (e) {
      if (e.key !== 'Tab' || e.shiftKey) return;
      var rows = rowsContainer.querySelectorAll('.mm-row-input');
      if (div === rows[rows.length - 1]) {
        e.preventDefault();
        addRow();
        focusLastRowName();
      }
    });

    rowsContainer.appendChild(div);
    return div;
  }

  function focusFirstEmpty() {
    var first = rowsContainer.querySelector('.mm-ri-name');
    if (first) first.focus();
  }

  function focusLastRowName() {
    var rows = rowsContainer.querySelectorAll('.mm-row-input');
    var last = rows[rows.length - 1];
    if (last) last.querySelector('.mm-ri-name').focus();
  }

  // ── 행 삭제 버튼 (이벤트 위임) ───────────────────────────────

  rowsContainer.addEventListener('click', function (e) {
    var btn = e.target.closest('.mm-row-del');
    if (!btn) return;
    var row = btn.closest('.mm-row-input');
    var rows = rowsContainer.querySelectorAll('.mm-row-input');
    if (rows.length <= 1) {
      // 마지막 행은 내용만 지우기
      row.querySelector('.mm-ri-name').value = '';
      row.querySelector('.mm-ri-price').value = '';
      row.querySelector('.mm-ri-name').focus();
    } else {
      var prevRow = row.previousElementSibling;
      row.remove();
      if (prevRow) prevRow.querySelector('.mm-ri-price').focus();
    }
  });

  // ── "행 추가" 버튼 ────────────────────────────────────────────

  addRowBtn.addEventListener('click', function () {
    addRow();
    focusLastRowName();
  });

  // ── 폼 제출 (여러 행 순차 저장) ─────────────────────────────

  form.addEventListener('submit', function (e) {
    e.preventDefault();

    var entries = [];
    rowsContainer.querySelectorAll('.mm-row-input').forEach(function (row) {
      var name  = row.querySelector('.mm-ri-name').value.trim();
      var price = parseInt(row.querySelector('.mm-ri-price').value, 10);
      if (name && !isNaN(price) && price >= 0) {
        entries.push({ name: name, price: price });
      }
    });

    if (entries.length === 0) {
      focusFirstEmpty();
      return;
    }

    submitBtn.disabled = true;
    addRowBtn.disabled = true;

    var errors = [];

    // SQLite 동시쓰기 방지를 위해 순차 처리
    function processNext(idx) {
      if (idx >= entries.length) {
        submitBtn.disabled = false;
        addRowBtn.disabled = false;
        if (errors.length > 0) {
          showAlert('일부 항목 추가 실패:\n' + errors.join('\n'));
        }
        initRows();
        renderList();
        focusFirstEmpty();
        return;
      }

      var entry = entries[idx];
      postForm(createUrl, entry)
        .then(function (data) {
          var existing = items.findIndex(function (i) { return i.pk === data.id; });
          if (existing >= 0) {
            items[existing].name  = data.name;
            items[existing].price = data.price;
          } else {
            items.push({ pk: data.id, name: data.name, price: data.price });
          }
        })
        .catch(function (err) {
          var msg = '"' + entry.name + '": ';
          if (err.response && err.response.data && err.response.data.errors) {
            var errs = err.response.data.errors;
            msg += Object.values(errs).map(function (e) {
              return Array.isArray(e) ? e.join(' ') : e;
            }).join(', ');
          } else {
            msg += '오류가 발생했습니다.';
          }
          errors.push(msg);
        })
        .finally(function () { processNext(idx + 1); });
    }

    processNext(0);
  });

  // ── 등록된 메뉴 목록 렌더링 ──────────────────────────────────

  function renderList() {
    list.innerHTML = '';
    if (items.length === 0) {
      emptyMsg.textContent = '아직 등록된 메뉴가 없습니다.';
      emptyMsg.style.display = 'block';
    } else {
      emptyMsg.style.display = 'none';
      items.forEach(function (item, idx) {
        var li = document.createElement('li');
        li.className = 'mm-item';
        li.dataset.pk = item.pk;

        if (String(item.pk) === String(editingPk)) {
          li.classList.add('mm-item-editing');
          li.innerHTML =
            '<input class="mm-input mm-edit-name" type="text"' +
            ' value="' + escAttr(item.name) + '" maxlength="100" autocomplete="off">' +
            '<input class="mm-input mm-edit-price" type="number"' +
            ' value="' + item.price + '" min="0" step="100">' +
            '<button type="button" class="mm-item-save" data-pk="' + item.pk + '">저장</button>' +
            '<button type="button" class="mm-item-cancel" data-pk="' + item.pk + '">취소</button>';
        } else {
          var isFirst = idx === 0;
          var isLast  = idx === items.length - 1;
          li.setAttribute('draggable', 'true');
          li.innerHTML =
            '<span class="mm-arrows">' +
              '<button type="button" class="mm-item-up" data-pk="' + item.pk + '"' + (isFirst ? ' disabled' : '') + '>▲</button>' +
              '<button type="button" class="mm-item-dn" data-pk="' + item.pk + '"' + (isLast  ? ' disabled' : '') + '>▼</button>' +
            '</span>' +
            '<span class="mm-item-name">' + escHtml(item.name) + '</span>' +
            '<span class="mm-item-price">' + item.price.toLocaleString() + '원</span>' +
            '<button type="button" class="mm-item-edit" data-pk="' + item.pk + '">수정</button>' +
            '<button type="button" class="mm-item-del"  data-pk="' + item.pk + '">삭제</button>';
          bindDragHandlers(li, idx);
        }
        list.appendChild(li);
      });

      if (editingPk) {
        var editName = list.querySelector('.mm-edit-name');
        if (editName) { editName.focus(); editName.select(); }
      }
    }
    syncPoster();
  }

  // ── 드래그 핸들러 바인딩 ─────────────────────────────────────

  function bindDragHandlers(li, itemIdx) {
    li.addEventListener('dragstart', function (e) {
      dragSrcIdx = itemIdx;
      e.dataTransfer.effectAllowed = 'move';
      setTimeout(function () { li.classList.add('mm-dragging'); }, 0);
    });

    li.addEventListener('dragend', function () {
      li.classList.remove('mm-dragging');
      clearDropIndicators();
      dragSrcIdx = null;
    });

    li.addEventListener('dragover', function (e) {
      if (dragSrcIdx === null || dragSrcIdx === itemIdx) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      clearDropIndicators();
      var rect = li.getBoundingClientRect();
      if (e.clientY < rect.top + rect.height / 2) {
        li.classList.add('mm-drop-top');
      } else {
        li.classList.add('mm-drop-bottom');
      }
    });

    li.addEventListener('dragleave', function (e) {
      if (!li.contains(e.relatedTarget)) {
        li.classList.remove('mm-drop-top', 'mm-drop-bottom');
      }
    });

    li.addEventListener('drop', function (e) {
      e.preventDefault();
      if (dragSrcIdx === null || dragSrcIdx === itemIdx) {
        clearDropIndicators();
        return;
      }
      var rect = li.getBoundingClientRect();
      var dropBefore = e.clientY < rect.top + rect.height / 2;
      clearDropIndicators();

      var moved = items.splice(dragSrcIdx, 1)[0];
      var insertAt;
      if (dropBefore) {
        insertAt = (dragSrcIdx < itemIdx) ? itemIdx - 1 : itemIdx;
      } else {
        insertAt = (dragSrcIdx < itemIdx) ? itemIdx : itemIdx + 1;
      }
      items.splice(insertAt, 0, moved);

      dragSrcIdx = null;
      renderList();
      sendReorder();
    });
  }

  function clearDropIndicators() {
    list.querySelectorAll('.mm-drop-top, .mm-drop-bottom').forEach(function (el) {
      el.classList.remove('mm-drop-top', 'mm-drop-bottom');
    });
  }

  // ── 등록된 메뉴 목록 버튼 이벤트 위임 ───────────────────────

  list.addEventListener('click', function (e) {
    var btn = e.target.closest('button[data-pk]');
    if (!btn) return;
    var itemPk = btn.dataset.pk;
    var idx;

    if (btn.classList.contains('mm-item-edit')) {
      editingPk = itemPk;
      renderList();
    } else if (btn.classList.contains('mm-item-cancel')) {
      editingPk = null;
      renderList();
    } else if (btn.classList.contains('mm-item-save')) {
      handleSave(btn, itemPk);
    } else if (btn.classList.contains('mm-item-del')) {
      handleDelete(btn, itemPk);
    } else if (btn.classList.contains('mm-item-up')) {
      idx = items.findIndex(function (i) { return String(i.pk) === itemPk; });
      if (idx > 0) {
        var tmp = items[idx]; items[idx] = items[idx - 1]; items[idx - 1] = tmp;
        renderList();
        sendReorder();
      }
    } else if (btn.classList.contains('mm-item-dn')) {
      idx = items.findIndex(function (i) { return String(i.pk) === itemPk; });
      if (idx >= 0 && idx < items.length - 1) {
        var swp = items[idx]; items[idx] = items[idx + 1]; items[idx + 1] = swp;
        renderList();
        sendReorder();
      }
    }
  });

  // ── 수정 저장 ────────────────────────────────────────────────

  function handleSave(saveBtn, itemPk) {
    var li      = list.querySelector('li[data-pk="' + itemPk + '"]');
    var nameEl  = li && li.querySelector('.mm-edit-name');
    var priceEl = li && li.querySelector('.mm-edit-price');
    if (!nameEl || !priceEl) return;

    var name  = nameEl.value.trim();
    var price = parseInt(priceEl.value, 10);
    if (!name) { nameEl.focus(); return; }
    if (isNaN(price) || price < 0) { priceEl.focus(); return; }

    saveBtn.disabled = true;
    var updateUrl = '/restaurants/' + restaurantPk + '/menu-items/' + itemPk + '/update/';

    postForm(updateUrl, { name: name, price: price })
      .then(function (data) {
        var idx = items.findIndex(function (i) { return String(i.pk) === String(itemPk); });
        if (idx >= 0) { items[idx].name = data.name; items[idx].price = data.price; }
        editingPk = null;
        renderList();
      })
      .catch(showFormError)
      .finally(function () { saveBtn.disabled = false; });
  }

  // ── 삭제 ─────────────────────────────────────────────────────

  function handleDelete(delBtn, itemPk) {
    showConfirm('이 메뉴를 삭제하시겠습니까?', function () {
      delBtn.disabled = true;
      axios.post('/restaurants/' + restaurantPk + '/menu-items/' + itemPk + '/delete/', null, ajaxHeaders())
        .then(function () {
          items = items.filter(function (i) { return String(i.pk) !== String(itemPk); });
          renderList();
        })
        .catch(function () { showAlert('삭제 중 오류가 발생했습니다.'); delBtn.disabled = false; });
    });
  }

  // ── 순서 저장 ────────────────────────────────────────────────

  function sendReorder() {
    var pks = items.map(function (i) { return i.pk; });
    axios.post(reorderUrl, JSON.stringify({ pks: pks }), {
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrf(),
        'X-Requested-With': 'XMLHttpRequest',
      }
    }).catch(function () { /* 순서 저장 실패는 무시 */ });
  }

  // ── 상세 페이지 메뉴 카드 동기화 ────────────────────────────

  function syncPoster() {
    var rows = document.getElementById('menu-poster-rows');
    if (!rows) return;
    rows.innerHTML = '';
    if (items.length === 0) {
      rows.innerHTML = '<div class="mp-row"><span style="color:var(--muted);font-size:12px;">아직 등록된 메뉴가 없습니다.</span></div>';
      return;
    }
    items.forEach(function (item) {
      var div = document.createElement('div');
      div.className = 'mp-row';
      div.innerHTML = '<span>' + escHtml(item.name) + '</span>' +
                      '<span class="mp-price">' + item.price.toLocaleString() + '원</span>';
      rows.appendChild(div);
    });
    document.dispatchEvent(new CustomEvent('menu-poster-updated'));
  }

  // ── 이벤트 바인딩 ────────────────────────────────────────────

  document.querySelectorAll('[data-target="menu-modal"]').forEach(function (btn) {
    btn.addEventListener('click', openModal);
  });

  overlay.addEventListener('click', closeModal);
  closeBtn.addEventListener('click', closeModal);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && panel.classList.contains('open')) closeModal();
  });

  // ── 유틸 ─────────────────────────────────────────────────────

  function postForm(url, fields) {
    var body = new URLSearchParams();
    Object.keys(fields).forEach(function (k) { body.append(k, fields[k]); });
    return axios.post(url, body.toString(), ajaxHeaders()).then(function (r) { return r.data; });
  }

  function ajaxHeaders() {
    return {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRFToken': getCsrf(),
        'X-Requested-With': 'XMLHttpRequest',
      }
    };
  }

  function showFormError(err) {
    var msg = '오류가 발생했습니다.';
    if (err.response && err.response.data && err.response.data.errors) {
      var errs = err.response.data.errors;
      msg = Object.values(errs).map(function (e) { return Array.isArray(e) ? e.join(' ') : e; }).join('\n');
    }
    showAlert(msg);
  }

  function escHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function escAttr(s) { return escHtml(s); }

})();
