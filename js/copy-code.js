(function() {
  var style = document.createElement('style');
  style.textContent = [
    '.code-block-wrapper { position: relative; }',
    '.copy-btn {',
    '  position: absolute; top: 4px; right: 4px;',
    '  background: rgba(255,255,255,0.15); color: #ccc;',
    '  border: 1px solid rgba(255,255,255,0.2);',
    '  border-radius: 4px; padding: 2px 8px;',
    '  font-size: 12px; cursor: pointer;',
    '  opacity: 0; transition: opacity 0.2s;',
    '  z-index: 10;',
    '}',
    '.code-block-wrapper:hover .copy-btn { opacity: 1; }',
    '.copy-btn.copied { background: #27ae60; color: #fff; border-color: #27ae60; }',
    'html.dark-mode .copy-btn { background: rgba(0,0,0,0.3); color: #aaa; border-color: rgba(255,255,255,0.15); }',
    'html.dark-mode .copy-btn.copied { background: #27ae60; color: #fff; }',
  ].join('\n');
  document.head.appendChild(style);

  function addCopyButtons() {
    document.querySelectorAll('.code-block-wrapper').forEach(function(w) {
      var btn = w.querySelector('.copy-btn');
      if (btn) return;
      var pre = w.querySelector('pre');
      if (!pre) return;
      btn = document.createElement('button');
      btn.className = 'copy-btn';
      btn.textContent = 'Copy';
      btn.addEventListener('click', function() {
        var code = pre.querySelector('code');
        var text = code ? code.textContent : pre.textContent;
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(function() {
            btn.textContent = 'Copied!';
            btn.classList.add('copied');
            setTimeout(function() { btn.textContent = 'Copy'; btn.classList.remove('copied'); }, 2000);
          });
        } else {
          var ta = document.createElement('textarea');
          ta.value = text;
          ta.style.position = 'fixed'; ta.style.left = '-9999px';
          document.body.appendChild(ta);
          ta.select();
          document.execCommand('copy');
          document.body.removeChild(ta);
          btn.textContent = 'Copied!';
          btn.classList.add('copied');
          setTimeout(function() { btn.textContent = 'Copy'; btn.classList.remove('copied'); }, 2000);
        }
      });
      w.insertBefore(btn, pre);
    });
  }

  // Wrap all pre elements
  document.querySelectorAll('pre').forEach(function(pre) {
    if (!pre.parentElement.classList.contains('code-block-wrapper')) {
      var wrapper = document.createElement('div');
      wrapper.className = 'code-block-wrapper';
      pre.parentNode.insertBefore(wrapper, pre);
      wrapper.appendChild(pre);
    }
  });

  addCopyButtons();

  // Re-run when MkDocs navigation loads content dynamically
  var observer = new MutationObserver(function() {
    document.querySelectorAll('pre').forEach(function(pre) {
      if (!pre.parentElement.classList.contains('code-block-wrapper')) {
        var wrapper = document.createElement('div');
        wrapper.className = 'code-block-wrapper';
        pre.parentNode.insertBefore(wrapper, pre);
        wrapper.appendChild(pre);
      }
    });
    addCopyButtons();
  });
  observer.observe(document.body, { childList: true, subtree: true });
})();
