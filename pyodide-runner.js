(() => {
  let pyodide = null;
  const chapterNamespaces = {};
  const resetSessions = new Set();
  const colabUrl = "https://colab.research.google.com/";
  const colabOnlyPatterns = [
    /import\s+tensorflow/i,
    /from\s+tensorflow/i,
    /import\s+keras/i,
    /from\s+keras/i,
    /\bkeras\b/i,
    /\btf\./i,
    /ImageDataGenerator/i,
    /import\s+torch/i,
    /from\s+torch/i,
    /!kaggle/i,
    /!pip\s+.*kaggle/i,
    /!pip/i,
    /!mkdir/i,
    /!cp/i,
    /!chmod/i,
    /!unzip/i,
    /kaggle\.api/i,
    /\bcv2\b/i,
    /import\s+gymnasium/i,
    /import\s+gym/i,
    /\bgym\./i,
    /FrozenLake/i,
    /from\s+google\.colab/i,
    /files\.upload/i
  ];
  const chapterSixProjectPatterns = [
    /\bmodel\.(compile|fit|evaluate|predict|add)/i,
    /\bhistory\.history/i,
    /\bgtsrb\b/i,
    /Train\.csv/i,
    /\bX_train\b|\bX_test\b|\by_train\b|\by_test\b/,
    /\bclass_names\b/i,
    /\bsample_path\b/i
  ];
  const chapterFiveColabPatterns = [
    /\benv\./i,
    /\bq_table\b/i,
    /\blog_df\b/i,
    /\bpolicy\b/i,
    /\bepsilon\b/i,
    /\breward\b/i,
    /\bterminated\b/i,
    /\btruncated\b/i
  ];

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function truncateOutput(text, maxLines = 200) {
    const lines = text.split("\n");
    if (lines.length <= maxLines) return text;
    return `${lines.slice(0, maxLines).join("\n")}\n[truncated]`;
  }

  function cleanCode(rawCode) {
    const text = String(rawCode || "").replace(/\r\n/g, "\n").replace(/^\n+|\s+$/g, "");
    const lines = text.split("\n");
    if (lines.length < 2) return text;

    const indentOf = (line) => line.match(/^ */)?.[0].length || 0;
    const firstIndent = indentOf(lines[0]);
    const restIndents = lines.slice(1).filter((line) => line.trim()).map(indentOf);

    if (firstIndent === 0 && restIndents.length) {
      const restBase = Math.min(...restIndents);
      if (restBase >= 6 || (restBase > 0 && !lines[0].trim().endsWith(":"))) {
        return [lines[0], ...lines.slice(1).map((line) => line.slice(Math.min(restBase, indentOf(line))))].join("\n");
      }
    }

    const allIndents = lines.filter((line) => line.trim()).map(indentOf);
    const base = allIndents.length ? Math.min(...allIndents) : 0;
    return base ? lines.map((line) => line.slice(Math.min(base, indentOf(line)))).join("\n") : text;
  }

  function cleanPythonError(message) {
    const lines = String(message || "").split("\n");
    const start = lines.findIndex((line) =>
      line.includes('File "<exec>"') ||
      line.includes("Traceback") ||
      line.includes("Error:")
    );
    return start >= 0 ? lines.slice(start).join("\n") : lines.join("\n");
  }

  function isPython(codeEl) {
    return codeEl?.className?.includes("language-python");
  }

  function normalizeChapter(value, fallback = "course") {
    const raw = String(value || "").trim().toLowerCase();
    const match = raw.match(/(?:^|[^a-z0-9])ch(?:apter)?-?(\d+)|^ch?(\d+)$/i);
    if (match) return match[1] || match[2];
    if (/^\d+$/.test(raw)) return raw;
    return fallback;
  }

  function chapterFromElement(el) {
    const direct = el.dataset?.chapter || el.closest("[data-chapter]")?.dataset?.chapter;
    const normalized = normalizeChapter(direct, "");
    if (normalized) return normalized;
    const classNode = el.closest("[class*='ch']");
    const classMatch = classNode?.className?.match(/(?:^|\s)ch(\d+)(?:\s|$)/i);
    return classMatch ? classMatch[1] : "course";
  }

  function lessonFromElement(el) {
    return (
      el.dataset?.lesson ||
      el.closest(".lesson-content")?.dataset?.lesson ||
      el.closest("section[id]")?.id ||
      `chapter-${chapterFromElement(el)}`
    );
  }

  function sessionKeyFor(el) {
    return String(el.dataset?.session || lessonFromElement(el) || chapterFromElement(el));
  }

  function isColabOnly(code, chapter) {
    if (colabOnlyPatterns.some((pattern) => pattern.test(code))) return true;
    if (chapter === "5" && chapterFiveColabPatterns.some((pattern) => pattern.test(code))) return true;
    if (chapter === "6" && chapterSixProjectPatterns.some((pattern) => pattern.test(code))) return true;
    return false;
  }

  function filenameFromCaption(caption, index) {
    const raw = caption?.textContent?.trim() || `example_${index + 1}.py`;
    if (/cell\s*\d+/i.test(raw)) return raw;
    if (raw.toLowerCase().includes("python")) return raw;
    return raw.endsWith(".py")
      ? raw
      : `${raw.replace(/[^\w.-]+/g, "_").replace(/^_+|_+$/g, "").toLowerCase() || "example"}.py`;
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

  function createNamespace(py) {
    return typeof py.toPy === "function" ? py.toPy({}) : py.runPython("dict()");
  }

  async function runCode(code, sessionKey, outputEl) {
    const py = await getPyodide();
    const key = String(sessionKey);

    try {
      await py.loadPackagesFromImports(code);
    } catch (error) {
      // Static import detection can miss or reject optional packages; execution will report real errors.
    }

    let stdout = "";
    let stderr = "";
    py.setStdout({ batched: (text) => { stdout += `${text}\n`; } });
    py.setStderr({ batched: (text) => { stderr += `${text}\n`; } });

    const fullCode = `
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
${code}
`;

    try {
      if (!chapterNamespaces[key]) {
        chapterNamespaces[key] = createNamespace(py);
      }

      await py.runPythonAsync(fullCode, {
        globals: chapterNamespaces[key]
      });

      let imgB64 = "";
      try {
        imgB64 = py.runPython(`
import io, base64, matplotlib.pyplot as plt
_buf = io.BytesIO()
if plt.get_fignums():
    plt.savefig(_buf, format='png', bbox_inches='tight', facecolor='#0d1117', dpi=120)
    _buf.seek(0)
    _result = base64.b64encode(_buf.read()).decode('utf-8')
    plt.close('all')
else:
    _result = ''
_result
`, { globals: chapterNamespaces[key] });
      } catch (error) {
        imgB64 = "";
      }

      renderOutput(outputEl, stdout.trim(), stderr.trim(), imgB64, null);
    } catch (error) {
      delete chapterNamespaces[key];
      renderOutput(outputEl, stdout.trim(), stderr.trim(), "", error);
    } finally {
      py.setStdout({ batched: (text) => console.log(text) });
      py.setStderr({ batched: (text) => console.warn(text) });
    }
  }

  function renderOutput(outputEl, stdout, stderr, imgB64, error) {
    outputEl.innerHTML = "";

    if (stdout) {
      const pre = document.createElement("pre");
      pre.className = "output-text";
      pre.textContent = truncateOutput(stdout);
      outputEl.appendChild(pre);
    }

    if (imgB64) {
      const img = document.createElement("img");
      img.className = "output-img";
      img.alt = "Matplotlib output";
      img.src = `data:image/png;base64,${imgB64}`;
      outputEl.appendChild(img);
    }

    if (stderr && !error) {
      const div = document.createElement("div");
      div.className = "output-error";
      div.textContent = stderr;
      outputEl.appendChild(div);
    }

    if (error) {
      const div = document.createElement("div");
      div.className = "output-error";
      div.textContent = cleanPythonError(error.message || String(error));
      outputEl.appendChild(div);
    }

    if (!outputEl.children.length && !error) {
      const empty = document.createElement("pre");
      empty.className = "output-text";
      empty.textContent = "[code ran successfully with no printed output]";
      outputEl.appendChild(empty);
    }

    outputEl.classList.toggle("has-content", outputEl.children.length > 0);
  }

  function wireCopyButton(block) {
    const copy = block.querySelector(".copy-btn");
    if (!copy || copy.dataset.initialized === "true") return;
    copy.dataset.initialized = "true";
    copy.addEventListener("click", async () => {
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
    if (!textarea || textarea.dataset.tabKeyInitialized === "true") return;
    textarea.dataset.tabKeyInitialized = "true";
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
    if (!button || !editor || !output || button.dataset.initialized === "true") return;
    button.dataset.initialized = "true";

    async function execute() {
      if (button.disabled) return;
      button.disabled = true;
      output.innerHTML = "";
      output.classList.remove("has-content");
      if (!window._pyodideEverLoaded) showToast("Loading Python runtime... one-time download");
      button.textContent = window._pyodideEverLoaded ? "Running..." : "Loading Python...";
      try {
        await runCode(editor.value, button.dataset.session || button.dataset.chapter, output);
        window._pyodideEverLoaded = true;
      } catch (error) {
        renderOutput(output, "", "", "", error);
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

  function addResetBar(block, session, chapter) {
    if (!session) return;
    const existing = Array.from(document.querySelectorAll(".reset-chapter-btn"))
      .some((button) => button.dataset.session === session);
    if (existing) {
      resetSessions.add(session);
      return;
    }
    resetSessions.add(session);
    const reset = document.createElement("div");
    reset.className = "chapter-reset-bar";
    reset.innerHTML = `<span class="chapter-reset-info">All runnable cells in this lesson share one Python session.</span><button class="reset-chapter-btn" type="button" data-session="${escapeHtml(session)}" data-chapter="${escapeHtml(chapter)}">↺ Reset Chapter Session</button>`;
    block.insertAdjacentElement("beforebegin", reset);
    wireResetButtons(reset);
  }

  function wireResetButtons(container = document) {
    findAll(container, ".reset-chapter-btn").forEach((button) => {
      if (button.dataset.initialized === "true") return;
      button.dataset.initialized = "true";
      button.addEventListener("click", () => {
        const key = String(button.dataset.session || button.dataset.chapter || "");
        delete chapterNamespaces[key];
        button.textContent = "Reset!";
        setTimeout(() => {
          button.textContent = "↺ Reset Chapter Session";
        }, 2000);
      });
    });
  }

  function findAll(root, selector) {
    const matches = [];
    if (root?.matches?.(selector)) matches.push(root);
    root?.querySelectorAll?.(selector).forEach((el) => matches.push(el));
    return matches;
  }

  function renderCodeBlock(block, details) {
    const { code, codeClass, filename, python, runnable, colabOnly, chapter, session } = details;
    block.classList.toggle("is-runnable", runnable);
    block.classList.toggle("is-colab-only", colabOnly);
    block.dataset.runnable = String(runnable);
    block.dataset.chapter = chapter;
    block.dataset.session = session;
    block.dataset.filename = filename;
    block.dataset.lang = python ? "python" : "text";
    block.innerHTML = `
      <div class="code-header">
        <span class="code-filename">${escapeHtml(filename)}</span>
        <div class="code-actions">
          <span class="code-lang">${python ? "Python" : "Text"}</span>
          <button class="copy-btn" type="button" title="Copy code">Copy</button>
          ${runnable ? `<button class="run-btn" type="button" data-chapter="${escapeHtml(chapter)}" data-session="${escapeHtml(session)}">Run</button>` : ""}
          ${colabOnly ? `<a class="colab-inline-btn" href="${colabUrl}" target="_blank" rel="noreferrer"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"></a><span class="colab-reason" title="This cell needs Google Colab or unsupported browser packages.">Run in Colab</span>` : ""}
        </div>
      </div>
      ${
        runnable
          ? `<div class="editor-shell"><pre class="line-gutter" aria-hidden="true">${lineNumbersFor(code)}</pre><textarea class="code-editor" spellcheck="false">${escapeHtml(code)}</textarea></div><div class="output-area"></div>`
          : `<div class="static-code-shell"><pre class="line-gutter" aria-hidden="true">${lineNumbersFor(code)}</pre><pre><code class="${escapeHtml(codeClass || (python ? "language-python" : "language-text"))}">${escapeHtml(code)}</code></pre></div>`
      }
    `;
    block.dataset.initialized = "true";
    wireCopyButton(block);
    if (runnable) {
      addResetBar(block, session, chapter);
      const editor = block.querySelector(".code-editor");
      editor?.addEventListener("input", () => updateLineNumbers(block));
      wireTabKey(editor);
      wireRunButton(block);
    } else if (window.hljs) {
      block.querySelectorAll("pre code").forEach((codeNode) => window.hljs.highlightElement(codeNode));
    }
  }

  function blockDetailsFromElement(el, index = 0) {
    const codeEl = el.querySelector("code");
    const codeClass = codeEl?.className || "";
    const code = cleanCode(el.dataset.code || codeEl?.textContent || "");
    const python = isPython(codeEl) || el.dataset.lang === "python";
    const chapter = normalizeChapter(el.dataset.chapter, chapterFromElement(el));
    const session = sessionKeyFor(el);
    const caption = el.querySelector("figcaption");
    const filename = el.dataset.filename || filenameFromCaption(caption, index);
    const colabOnly = python && isColabOnly(code, chapter);
    const declaredRunnable = el.dataset.runnable;
    const runnable = python && !colabOnly && (declaredRunnable === undefined || declaredRunnable === "true");
    return { code, codeClass, filename, python, runnable, colabOnly, chapter, session };
  }

  function transformFigure(figure, index) {
    if (figure.dataset.initialized === "true") return;
    const details = blockDetailsFromElement(figure, index);
    if (!details.code) return;
    const block = document.createElement("div");
    block.className = "code-block";
    figure.replaceWith(block);
    renderCodeBlock(block, details);
  }

  function makeRunnable(codeBlockEl) {
    if (!codeBlockEl || codeBlockEl.dataset.initialized === "true") return;
    const details = blockDetailsFromElement(codeBlockEl);
    if (!details.runnable) {
      renderCodeBlock(codeBlockEl, details);
      return;
    }
    renderCodeBlock(codeBlockEl, details);
  }

  function makeStaticCodeBlock(codeBlockEl) {
    if (!codeBlockEl || codeBlockEl.dataset.initialized === "true") return;
    renderCodeBlock(codeBlockEl, blockDetailsFromElement(codeBlockEl));
  }

  function initRunnableCells(containerEl = document) {
    const root = containerEl || document;
    findAll(root, "figure.code-card").forEach(transformFigure);
    findAll(root, '.code-block[data-runnable="true"]').forEach(makeRunnable);
    findAll(root, '.code-block[data-runnable="false"]').forEach(makeStaticCodeBlock);
    wireResetButtons(root);
  }

  window.makeRunnable = makeRunnable;
  window.initRunnableCells = initRunnableCells;
  window.addEventListener("mlr:lesson-loaded", (event) => {
    initRunnableCells(event.detail?.container || document);
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => initRunnableCells(document));
  } else {
    initRunnableCells(document);
  }
})();
