(function () {
  'use strict';

  var certImage = document.getElementById('certImage');
  if (certImage) {
    certImage.addEventListener('change', function () {
      var name = (this.files[0] && this.files[0].name) || '사진을 선택하거나 여기에 드래그하세요';
      var display = document.getElementById('fileNameDisplay');
      if (display) display.textContent = name;
    });
  }
})();
