(function () {
  'use strict';

  /* 템플릿에서 meta 태그로 전달받은 값 */
  const clientKey  = document.getElementById('toss-client-key').content;
  const csrfToken  = document.getElementById('csrf-token').content;
  const customerKey = 'USER_' + Math.floor(Math.random() * 10000);

  let paymentWidget       = null;
  let paymentMethodWidget = null;

  /* ── 메뉴 데이터 ── */
  const MEALS = [
    { name: '순대국',          price: 7000  },
    { name: '살코기 순대국',   price: 7000  },
    { name: '순대만 순대국',   price: 7000  },
    { name: '부대찌개',        price: 7000  },
    { name: '술국',            price: 15000 },
    { name: '순대곱창전골 중', price: 20000 },
    { name: '순대곱창전골 대', price: 30000 },
    { name: '순대곱창볶음 중', price: 20000 },
    { name: '순대곱창볶음 대', price: 30000 },
  ];
  const LIQUORS = [
    { name: '소주', price: 3000 },
    { name: '맥주', price: 3000 },
  ];
  const DRINKS = [
    { name: '콜라',   price: 1000 },
    { name: '사이다', price: 1000 },
  ];

  /* ── 유틸 ── */
  function fmtPrice(n) {
    return Number(n).toLocaleString('ko-KR');
  }

  function shuffle(arr) {
    return [...arr].sort(() => 0.5 - Math.random());
  }

  /* ── 랜덤 주문 생성 ── */
  function buildRandomOrder() {
    const items     = [];
    const isEvening = Math.random() > 0.5;
    const mealCount = isEvening
      ? Math.floor(Math.random() * 2) + 1   // 저녁: 1~2종
      : Math.floor(Math.random() * 3) + 1;  // 점심: 1~3종

    shuffle(MEALS).slice(0, mealCount).forEach(m => {
      const qty = Math.floor(Math.random() * (isEvening ? 2 : 4)) + 1;
      items.push({ name: m.name, qty, price: m.price });
    });

    if (isEvening) {
      if (Math.random() > 0.2) {
        shuffle(LIQUORS).slice(0, Math.floor(Math.random() * 2) + 1).forEach(l => {
          items.push({ name: l.name, qty: Math.floor(Math.random() * 5) + 1, price: l.price });
        });
      }
      if (Math.random() > 0.6) {
        const d = DRINKS[Math.floor(Math.random() * DRINKS.length)];
        items.push({ name: d.name, qty: Math.floor(Math.random() * 3) + 1, price: d.price });
      }
    }

    return items;
  }

  /* ── Toss 위젯 초기화 ── */
  window.addEventListener('load', function () {
    if (typeof PaymentWidget === 'undefined') return;
    paymentWidget       = PaymentWidget(clientKey, customerKey);
    paymentMethodWidget = paymentWidget.renderPaymentMethods('#payment-method', { value: 0 });
    paymentWidget.renderAgreement('#agreement');
  });

  /* ── 결제 버튼 ── */
  document.getElementById('payment-button').addEventListener('click', async function () {
    if (!paymentWidget) {
      showAlert('결제 시스템 로딩 중입니다. 잠시만 기다려주세요.');
      return;
    }

    const items       = buildRandomOrder();
    const totalAmount = items.reduce((sum, i) => sum + i.price * i.qty, 0);
    const orderName   = '정직순대국 - ' + items.map(i => `${i.name} ${i.qty}개`).join(', ');
    const orderId     = 'ORDER_' + Math.random().toString(36).slice(2, 11).toUpperCase();

    try {
      await paymentMethodWidget.updateAmount(totalAmount);

      const res = await fetch('/sales/api/create-order/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({ orderId, amount: totalAmount, items }),
      });

      if (!res.ok) throw new Error('주문 생성 실패');

      await paymentWidget.requestPayment({
        orderId,
        amount: totalAmount,
        orderName,
        successUrl: window.location.origin + '/sales/success/',
        failUrl:    window.location.origin + '/sales/fail/',
      });
    } catch (err) {
      console.error(err);
      showAlert('오류: ' + err.message);
    }
  });
})();
