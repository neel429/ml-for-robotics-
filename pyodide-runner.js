(() => {
  let pyodide = null;
  const chapterNamespaces = {};
  const resetChapters = new Set();
  const colabUrl = "https://colab.research.google.com/";
  const colabOnlyPatterns = [
    /import\s+tensorflow/i,
    /from\s+tensorflow/i,
    /import\s+keras/i,
    /from\s+keras/i,
    /import\s+torch/i,
    /!kaggle/i,
    /!pip\s+.*kaggle/i,
    /!pip/i,
    /!mkdir/i,
    /!cp/i,
    /!chmod/i,
    /!unzip/i,
    /kaggle\.api/i,
    /import\s+cv2/i,
    /cv2\.imshow/i,
    /import\s+gymnasium/i,
    /import\s+gym/i,
    /from\s+google\.colab/i,
    /files\.upload/i
  ];

  function escapeHtml(value) {
    return value
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function truncateOutput(text, maxLines = 200) {
    const lines = text.split("\n");
    if (lines.length <= maxLines) return text;
    return `${lines.slice(0, maxLines).join("\n")}\n\n[... output truncated - showing ${maxLines} of ${lines.length} lines]`;
  }

  function cleanPythonError(message) {
    const lines = message.split("\n");
    const start = lines.findIndex((line) => line.includes('File "<exec>"') || line.includes("Traceback"));
    return start >= 0 ? lines.slice(start).join("\n") : message;
  }

  function isColabOnly(code) {
    return colabOnlyPatterns.some((pattern) => pattern.test(code));
  }

  function isPython(codeEl) {
    return codeEl.className.includes("language-python");
  }

  function filenameFromCaption(caption, index) {
    const raw = caption?.textContent?.trim() || `example_${index + 1}.py`;
    if (/cell\s*\d+/i.test(raw)) return raw;
    if (raw.toLowerCase().includes("python")) return raw;
    return raw.endsWith(".py") ? raw : `${raw.replace(/[^\w.-]+/g, "_").replace(/^_+|_+$/g, "").toLowerCase() || "example"}.py`;
  }

  function lineNumbersFor(code) {
    const count = Math.max(1, code.split("\n").length);
    return Array.from({ length: count }, (_, index) => index + 1).join("\n");
  }

  function updateLineNumbers(block) {
    const editor = block.querySelector(".code-editor");
    const gutter = block.querySelector(".line-gutter");
    if (!editor || !gutter) return;
    gutter.textContent = lineNumbersFor(editor.value);
  }

  function showToast(message) {
    dismissToast();
    const toast = document.createElement("div");
    toast.className = "pyodide-toast";
    toast.textContent = message;
    toast.id = "pyodide-toast";
    document.body.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add("visible"));
  }

  function dismissToast() {
    const toast = document.getElementById("pyodide-toast");
    if (!toast) return;
    toast.classList.remove("visible");
    setTimeout(() => toast.remove(), 400);
  }

  async function getPyodide() {
    if (pyodide) return pyodide;
    if (typeof loadPyodide !== "function") {
      throw new Error("Pyodide could not be loaded. Check your internet connection and refresh the page.");
    }
    pyodide = await loadPyodide();
    await pyodide.loadPackage(["numpy", "pandas", "matplotlib", "scikit-learn", "scipy"]);
    return pyodide;
  }

  async function runCode(code, chapterNum, outputEl) {
    const py = await getPyodide();
    if (!chapterNamespaces[chapterNum]) {
      chapterNamespaces[chapterNum] = py.runPython("dict()");
    }
    const ns = chapterNamespaces[chapterNum];

    py.runPython(`
import sys, io
sys.stdout = io.StringIO()
sys.stderr = io.StringIO()
`);

    const preamble = `
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
`;

    try {
      await py.runPythonAsync(`${preamble}\n${code}`, { globals: ns });
      const stdout = py.runPython("sys.stdout.getvalue()");
      const stderr = py.runPython("sys.stderr.getvalue()");
      const imgB64 = py.runPython(`
import io, base64
_buf = io.BytesIO()
if plt.get_fignums():
    plt.savefig(_buf, format='png', bbox_inches='tight', facecolor='#0d1117', dpi=120)
    _buf.seek(0)
    _img = base64.b64encode(_buf.read()).decode('utf-8')
    plt.close('all')
else:
    _img = ''
_img
`);

      outputEl.innerHTML = "";
      if (stdout) {
        const pre = document.createElement("pre");
        pre.textContent = truncateOutput(stdout);
        outputEl.appendChild(pre);
      }
      if (stderr) {
        const errDiv = document.createElement("div");
        errDiv.className = "output-error";
        errDiv.textContent = stderr;
        outputEl.appendChild(errDiv);
      }
      if (imgB64) {
        const img = document.createElement("img");
        img.className = "output-img";
        img.alt = "Matplotlib output";
        img.src = `data:image/png;base64,${imgB64}`;
        outputEl.appendChild(img);
      }
      if (!stdout && !stderr && !imgB64) {
        const empty = document.createElement("pre");
        empty.textContent = "[code ran successfully with no printed output]";
        outputEl.appendChild(empty);
      }
      outputEl.classList.add("has-content");
    } catch (error) {
      outputEl.innerHTML = `<div class="output-error">${escapeHtml(cleanPythonError(error.message))}</div>`;
      outputEl.classList.add("has-content");
    }
  }

  function wireCopyButton(block) {
    const copy = block.querySelector(".copy-btn");
    copy?.addEventListener("click", async () => {
      const editor = block.querySelector(".code-editor");
      const code = editor ? editor.value : block.querySelector("code")?.textContent || "";
      try {
        await navigator.clipboard.writeText(code);
        copy.classList.add("copied");
        copy.textContent = "Copied!";
      } catch (error) {
        copy.textContent = "Select code";
      }
      setTimeout(() => {
        copy.classList.remove("copied");
        copy.textContent = "Copy";
      }, 1500);
    });
  }

  function wireTabKey(textarea) {
    textarea.addEventListener("keydown", (event) => {
      if (event.key !== "Tab") return;
      event.preventDefault();
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      textarea.value = `${textarea.value.slice(0, start)}    ${textarea.value.slice(end)}`;
      textarea.selectionStart = textarea.selectionEnd = start + 4;
      updateLineNumbers(textarea.closest(".code-block"));
    });
  }

  function wireRunButton(block) {
    const button = block.querySelector(".run-btn");
    const editor = block.querySelector(".code-editor");
    const output = block.querySelector(".output-area");
    if (!button || !editor || !output) return;

    async function execute() {
      if (button.disabled) return;
      button.disabled = true;
      output.innerHTML = "";
      output.classList.remove("has-content");
      if (!window._pyodideEverLoaded) showToast("Loading Python runtime... one-time download");
      button.textContent = window._pyodideEverLoaded ? "Running..." : "Loading Python...";
      try {
        await runCode(editor.value, button.dataset.chapter, output);
        window._pyodideEverLoaded = true;
      } catch (error) {
        output.innerHTML = `<div class="output-error">${escapeHtml(cleanPythonError(error.message))}</div>`;
        output.classList.add("has-content");
      } finally {
        dismissToast();
        button.textContent = "Run";
        button.disabled = false;
      }
    }

    button.addEventListener("click", execute);
    editor.addEventListener("keydown", (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
        event.preventDefault();
        execute();
      }
    });
  }

  function addResetBar(block, chapter) {
    if (!chapter || resetChapters.has(chapter)) return;
    resetChapters.add(chapter);
    const reset = document.createElement("div");
    reset.className = "chapter-reset-bar";
    reset.innerHTML = `<span class="chapter-reset-info">All runnable cells in this chapter share one Python session.</span><button class="reset-chapter-btn" type="button" data-chapter="${chapter}">Reset Chapter Session</button>`;
    block.insertAdjacentElement("beforebegin", reset);
  }

  function wireResetButtons() {
    document.querySelectorAll(".reset-chapter-btn").forEach((button) => {
      button.addEventListener("click", () => {
        delete chapterNamespaces[button.dataset.chapter];
        button.textContent = "Reset!";
        setTimeout(() => {
          button.textContent = "Reset Chapter Session";
        }, 2000);
      });
    });
  }

  function transformCodeBlock(figure, index) {
    const codeEl = figure.querySelector("code");
    if (!codeEl) return;
    const code = codeEl.textContent.replace(/^\n+|\s+$/g, "");
    const caption = figure.querySelector("figcaption");
    const filename = filenameFromCaption(caption, index);
    const python = isPython(codeEl);
    const colabOnly = python && isColabOnly(code);
    const runnable = python && !colabOnly;
    const chapter = figure.closest(".lesson-content")?.dataset.chapter || "course";

    const block = document.createElement("div");
    block.className = `code-block${runnable ? " is-runnable" : ""}${colabOnly ? " is-colab-only" : ""}`;
    block.dataset.lang = python ? "python" : "text";
    block.dataset.chapter = chapter;
    block.innerHTML = `
      <div class="code-header">
        <span class="code-filename">${escapeHtml(filename)}</span>
        <div class="code-actions">
          <span class="code-lang">${python ? "Python" : "Text"}</span>
          <button class="copy-btn" type="button" title="Copy code">Copy</button>
          ${runnable ? `<button class="run-btn" type="button" data-chapter="${chapter}">Run</button>` : ""}
          ${colabOnly ? `<a class="colab-inline-btn" href="${colabUrl}" target="_blank" rel="noreferrer"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"></a><span class="colab-reason" title="This cell needs Google Colab or unsupported browser packages.">Run in Colab</span>` : ""}
        </div>
      </div>
      ${
        runnable
          ? `<div class="editor-shell"><pre class="line-gutter" aria-hidden="true">${lineNumbersFor(code)}</pre><textarea class="code-editor" spellcheck="false">${escapeHtml(code)}</textarea></div><div class="output-area"></div>`
          : `<div class="static-code-shell"><pre class="line-gutter" aria-hidden="true">${lineNumbersFor(code)}</pre><pre><code class="${escapeHtml(codeEl.className)}">${escapeHtml(code)}</code></pre></div>`
      }
    `;

    figure.replaceWith(block);
    wireCopyButton(block);
    if (runnable) {
      addResetBar(block, chapter);
      const editor = block.querySelector(".code-editor");
      editor.addEventListener("input", () => updateLineNumbers(block));
      wireTabKey(editor);
      wireRunButton(block);
    }
    if (!runnable && window.hljs) {
      block.querySelectorAll("pre code").forEach((codeNode) => window.hljs.highlightElement(codeNode));
    }
  }

  function initCodeBlocks() {
    document.querySelectorAll("figure.code-card").forEach(transformCodeBlock);
    wireResetButtons();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initCodeBlocks);
  } else {
    initCodeBlocks();
  }
})();
