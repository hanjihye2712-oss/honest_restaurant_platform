document.addEventListener('DOMContentLoaded', function () {
  var countEl = document.querySelector('.bookmark-count strong');

  document.addEventListener('click', function (e) {
    var btn = e.target.closest('.bmc-heart');
    if (!btn) return;
    e.preventDefault();
    e.stopPropagation();

    var restaurantId = btn.dataset.restaurantId;
    var card = btn.closest('.bookmark-card');
    btn.disabled = true;

    BookmarkAPI.toggle(restaurantId)
      .then(function (result) {
        if (!result.bookmarked) {
          card.style.transition = 'opacity 0.25s, transform 0.25s';
          card.style.opacity = '0';
          card.style.transform = 'translateX(16px)';
          setTimeout(function () {
            card.remove();
            if (countEl) {
              var n = parseInt(countEl.textContent, 10) - 1;
              countEl.textContent = n;
            }
          }, 260);
        } else {
          btn.disabled = false;
        }
      })
      .catch(function () {
        btn.disabled = false;
      });
  });
});
