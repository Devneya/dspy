(function () {
  "use strict";
  const editors = {};
  let _monacoReady = false;
  let _monacoPromise = null;
  let _pyodidePromise = null;
  let _pyodide = null;

  async function getPyodide() {
    if (_pyodide) return _pyodide;
    if (_pyodidePromise) return _pyodidePromise;

    _pyodidePromise = (async () => {
      const script = document.createElement("script");
      script.src = "https://cdn.jsdelivr.net/pyodide/v0.25.0/full/pyodide.js";
      await new Promise((resolve, reject) => {
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
      });
      _pyodide = await loadPyodide({
        indexURL: "https://cdn.jsdelivr.net/pyodide/v0.25.0/full/",
      });
      return _pyodide;
    })();

    return _pyodidePromise;
  }

  function loadMonaco() {
    if (_monacoPromise) return _monacoPromise;
    _monacoPromise = new Promise((resolve) => {
      if (_monacoReady) {
        resolve();
        return;
      }

      const MONACO_CDN =
        "https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs";

      require.config({
        paths: { vs: MONACO_CDN },
        baseUrl: MONACO_CDN,
      });

      require(["vs/editor/editor.main"], () => {
        _monacoReady = true;
        resolve();
      });
    });
    return _monacoPromise;
  }

  function waitForDimensions(container, maxAttempts) {
    maxAttempts = maxAttempts || 20;
    return new Promise((resolve) => {
      let attempts = 0;

      function check() {
        attempts++;

        if (!container.isConnected) {
          resolve();
          return;
        }

        if (container.clientWidth < 50) {
          const parent = container.parentElement;
          if (parent && parent.clientWidth > 50) {
            container.style.width = parent.clientWidth + "px";
          } else {
            container.style.width = "100%";
            container.style.minWidth = "300px";
          }
        }

        if (container.clientWidth >= 50 && container.clientHeight >= 50) {
          resolve();
          return;
        }

        if (attempts >= maxAttempts) {
          container.style.width = "100%";
          container.style.minWidth = "300px";
          container.style.height = "320px";
          setTimeout(() => resolve(), 50);
          return;
        }

        setTimeout(check, 150);
      }

      check();
    });
  }

  async function createEditor(blockId) {
    if (editors[blockId]) {
      try {
        editors[blockId].dispose();
      } catch (e) {}
      delete editors[blockId];
    }

    const container = document.getElementById(`monaco-editor-${blockId}`);
    if (!container || !container.isConnected) return;

    await waitForDimensions(container);

    if (!container.isConnected) return;

    await loadMonaco();

    const code =
      container.dataset.code ||
      document.getElementById(`code-editor-${blockId}`)?.value ||
      "";

    const isDark = document.documentElement.classList.contains("dark");

    const lineCount = code.split("\n").length;
    const lineHeight = 19;
    const initialHeight = Math.max(200, (lineCount + 1) * lineHeight);
    container.style.height = initialHeight + "px";

    const editor = monaco.editor.create(container, {
      value: code,
      language: "python",
      theme: isDark ? "vs-dark" : "vs",
      fontSize: 14,
      minimap: { enabled: false },
      automaticLayout: true,
      scrollBeyondLastLine: false,
      wordWrap: "on",
      lineNumbersMinChars: 3,
    });

    editors[blockId] = editor;

    editor.onDidContentSizeChange(() => {
      const contentHeight = editor.getContentHeight();
      container.style.height = Math.max(200, contentHeight) + "px";
      editor.layout();
    });

    editor.onDidChangeModelContent(() => {
      const ta = document.getElementById(`code-editor-${blockId}`);
      if (ta) ta.value = editor.getValue();
    });

    new MutationObserver(() => {
      const dark = document.documentElement.classList.contains("dark");
      monaco.editor.setTheme(dark ? "vs-dark" : "vs");
    }).observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });
  }

  function destroyAllEditors() {
    Object.keys(editors).forEach((id) => {
      try {
        editors[id].dispose();
      } catch (e) {}
    });
    for (const key in editors) {
      delete editors[key];
    }
  }

  function initAllEditors() {
    document.querySelectorAll('[id^="monaco-editor-"]').forEach((container) => {
      const blockId = container.id.replace("monaco-editor-", "");
      createEditor(blockId);
    });
  }

  function saveCode(blockId) {
    const editor = editors[blockId];
    const code = editor
      ? editor.getValue()
      : document.getElementById(`code-editor-${blockId}`)?.value || "";

    htmx.ajax("POST", "/save-reward-code", {
      swap: "none",
      values: { block_id: blockId, code },
    });

    const btn = document.querySelector(`[onclick*="saveCode('${blockId}')"]`);
    if (btn) {
      const orig = btn.innerHTML;
      btn.innerHTML = "✓";
      btn.disabled = true;
      setTimeout(() => {
        btn.innerHTML = orig;
        btn.disabled = false;
      }, 1500);
    }
  }

  async function testReward(blockId) {
    const editor = editors[blockId];
    const code = editor
      ? editor.getValue()
      : document.getElementById(`code-editor-${blockId}`)?.value || "";
    const data = (window._wrapperData || {})[blockId];
    const statusEl = document.getElementById(`test-status-${blockId}`);
    const btn = document.getElementById(`test-btn-${blockId}`);

    if (!data || !data.rows.length) {
      if (statusEl) statusEl.textContent = "No data";
      return;
    }
    if (!code.trim()) {
      if (statusEl) statusEl.textContent = "No code";
      return;
    }

    if (btn) btn.disabled = true;
    if (statusEl) statusEl.textContent = "Running...";

    try {
      const pyodide = await getPyodide();

      const pythonLines = [
        "import json",
        "",
        code,
        "",
        "class MockPrediction:",
        "    def __init__(self, **kwargs):",
        "        self.__dict__.update(kwargs)",
        "    def __str__(self):",
        "        for v in self.__dict__.values():",
        "            if v: return str(v)",
        '        return ""',
        "",
        "rows = " + JSON.stringify(data.rows),
        "input_cols = " + JSON.stringify(data.inputCols || []),
        "output_cols = " + JSON.stringify(data.outputCols || []),
        "",
        "results = []",
        "for row in rows:",
        "    inputs = {}",
        "    for col in input_cols:",
        '        inputs[col] = row.get(col, "")',
        "    pred_kwargs = {}",
        "    for col in output_cols:",
        '        pred_kwargs[col] = row.get(col, "")',
        "    prediction = MockPrediction(**pred_kwargs)",
        "    try:",
        "        score = reward_fn(inputs, prediction)",
        "        if isinstance(score, bool):",
        "            score = 1.0 if score else 0.0",
        "        score = float(score)",
        "        score = max(min(score, 1.0), 0.0)",
        '        results.append({"rowId": row["id"], "score": score, "error": None})',
        "    except Exception as e:",
        '        results.append({"rowId": row["id"], "score": None, "error": str(e)})',
        "json.dumps(results)",
      ];

      const pythonScript = pythonLines.join("\n");
      const resultStr = pyodide.runPython(pythonScript);
      const results = JSON.parse(resultStr);

      results.forEach((r) => {
        const el = document.getElementById(`score-${blockId}-${r.rowId}`);
        if (!el) return;
        if (r.error) {
          el.textContent = "ERR";
          el.title = r.error;
        } else {
          const num = r.score;
          el.textContent = num.toFixed(2);
        }
      });

      const errors = results.filter((r) => r.error).length;
      if (statusEl) {
        statusEl.textContent =
          errors > 0
            ? `${errors}/${results.length} errors`
            : `${results.filter((r) => r.score >= 0.4).length}/${results.length} passed`;
        statusEl.className =
          "text-xs " +
          (errors > 0 ? "text-destructive" : "text-muted-foreground") +
          " ml-2 p-0";
      }
    } catch (err) {
      console.error("Test error:", err);
      if (statusEl) statusEl.textContent = "Error: " + err.message;
      data.rows.forEach((row) => {
        const el = document.getElementById(`score-${blockId}-${row.id}`);
        if (el) {
          el.textContent = "ERR";
          el.className = "reward-score err";
        }
      });
    }

    if (btn) btn.disabled = false;
  }

  document.body.addEventListener("htmx:beforeSwap", (evt) => {
    if (evt.detail.target?.id === "main-container") {
      destroyAllEditors();
    }
  });

  document.body.addEventListener("htmx:afterSwap", (evt) => {
    if (evt.detail.target?.id === "main-container") {
      setTimeout(initAllEditors, 500);
    }
  });

  document.addEventListener("DOMContentLoaded", () => {
    setTimeout(initAllEditors, 500);
  });

  window.DSPyRewardEditor = { createEditor, saveCode, testReward };
})();
