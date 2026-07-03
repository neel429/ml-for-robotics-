(function() {
  var STORAGE_KEY = 'mkdocs-dark-mode';
  var html = document.documentElement;
  var HLJS_LIGHT = 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/styles/github.min.css';
  var HLJS_DARK  = 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/styles/github-dark.min.css';

  function setHljsTheme(dark) {
    var link = document.querySelector('link[href*="highlight.js"]');
    if (link) link.href = dark ? HLJS_DARK : HLJS_LIGHT;
  }

  function setDark(enabled) {
    if (enabled) {
      html.classList.add('dark-mode');
    } else {
      html.classList.remove('dark-mode');
    }
    setHljsTheme(enabled);
    try {
      localStorage.setItem(STORAGE_KEY, enabled ? '1' : '0');
    } catch(e) {}
  }

  var stored = (function() {
    try { return localStorage.getItem(STORAGE_KEY); } catch(e) { return null; }
  })();

  if (stored === '1') {
    setDark(true);
  } else if (stored === null && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    setDark(true);
  }

  var btn = document.createElement('button');
  btn.className = 'dark-mode-toggle';
  btn.setAttribute('aria-label', 'Toggle dark mode');
  btn.innerHTML = html.classList.contains('dark-mode') ? '☀' : '☾';
  btn.addEventListener('click', function() {
    var isDark = !html.classList.contains('dark-mode');
    setDark(isDark);
    btn.innerHTML = isDark ? '☀' : '☾';
  });
  document.body.appendChild(btn);
})();
