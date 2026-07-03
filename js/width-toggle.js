(function() {
  var STORAGE_KEY = 'mkdocs-narrow';
  var html = document.documentElement;

  function setNarrow(enabled) {
    if (enabled) {
      html.classList.add('narrow');
    } else {
      html.classList.remove('narrow');
    }
    try {
      localStorage.setItem(STORAGE_KEY, enabled ? '1' : '0');
    } catch(e) {}
  }

  var stored = (function() {
    try { return localStorage.getItem(STORAGE_KEY); } catch(e) { return null; }
  })();

  if (stored === '1') {
    setNarrow(true);
  }

  var btn = document.createElement('button');
  btn.className = 'width-toggle';
  btn.setAttribute('aria-label', 'Toggle content width');
  btn.innerHTML = html.classList.contains('narrow') ? '&#62;' : '&#60;';
  btn.addEventListener('click', function() {
    var isNarrow = !html.classList.contains('narrow');
    setNarrow(isNarrow);
    btn.innerHTML = isNarrow ? '&#62;' : '&#60;';
  });
  document.body.appendChild(btn);
})();
