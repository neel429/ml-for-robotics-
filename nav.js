(() => {
  const body = document.body;
  const isLessonApp = body.classList.contains("lesson-app");
  let themeToggle = document.getElementById("themeToggle");
  const drawerToggle = document.getElementById("drawerToggle");
  const drawerScrim = document.getElementById("drawerScrim");
  const sidebar = document.getElementById("sidebar");
  const contentPanel = document.getElementById("contentPanel");
  const currentChapter = document.getElementById("currentChapter");
  const progressFill = document.getElementById("progressFill");
  const lessons = window.COURSE_LESSONS || [];
  const chapters = window.COURSE_CHAPTERS || [];
  const lessonIds = lessons.map((lesson) => lesson.id);
  const lessonById = new Map(lessons.map((lesson) => [lesson.id, lesson]));
  const legacyHashLessons = {
    "chapter-0": "ch0-welcome",
    build: "ch0-build",
    tools: "ch0-tools",
    "reading-tips": "ch0-reading-tips",
    python: "ch1-overview",
    "python-colab": "ch1-colab",
    variables: "ch1-variables",
    "data-structures": "ch1-data-structures",
    "control-flow": "ch1-control-flow",
    loops: "ch1-loops",
    functions: "ch1-functions",
    libraries: "ch1-libraries",
    checkpoint: "ch1-checkpoint",
    "what-is-ml": "ch2-overview",
    types: "ch2-types",
    "when-to-use": "ch2-when-to-use",
    supervised: "ch3-overview",
    "classification-regression": "ch3-classification-regression",
    algorithms: "ch3-algorithms",
    "ml-pipeline": "ch3-pipeline",
    "robot-failure-project": "ch3-project",
    unsupervised: "ch4-overview",
    clustering: "ch4-clustering",
    kmeans: "ch4-kmeans",
    "sensor-cluster-project": "ch4-project",
    "reinforcement-learning": "ch5-overview",
    "q-learning": "ch5-q-learning",
    "maze-project": "ch5-project",
    "computer-vision": "ch6-overview",
    opencv: "ch6-opencv",
    tensorflow: "ch6-tensorflow",
    cnn: "ch6-cnn",
    "traffic-sign-project": "ch6-project",
    "whats-next": "ch7-overview",
    "decision-guide": "ch7-decision-guide",
    roadmap: "ch7-roadmap",
    papers: "ch7-papers",
    projects: "project-archive"
  };

  function setTheme(theme) {
    const nextTheme = theme === "light" ? "light" : "dark";
    document.documentElement.classList.toggle("light-mode", nextTheme === "light");
    document.documentElement.dataset.theme = nextTheme;
    if (themeToggle) {
      themeToggle.textContent = nextTheme === "light" ? "Dark" : "Light";
      themeToggle.setAttribute(
        "aria-label",
        nextTheme === "light" ? "Switch to dark mode" : "Switch to light mode"
      );
    }
    try {
      localStorage.setItem("mlr-theme", nextTheme);
    } catch (error) {
      // Theme still works for the current page.
    }
  }

  function initTheme() {
    let saved = "dark";
    try {
      saved = localStorage.getItem("mlr-theme") || saved;
    } catch (error) {
      saved = "dark";
    }
    setTheme(saved);
    themeToggle?.addEventListener("click", () => {
      const current = document.documentElement.classList.contains("light-mode") ? "light" : "dark";
      setTheme(current === "light" ? "dark" : "light");
    });
  }

  function setSidebarOpen(open) {
    body.classList.toggle("sidebar-open", open);
    drawerToggle?.setAttribute("aria-expanded", String(open));
  }

  function completedKey(lessonId) {
    return `completed_${lessonId}`;
  }

  function isCompleted(lessonId) {
    try {
      return localStorage.getItem(completedKey(lessonId)) === "true";
    } catch (error) {
      return false;
    }
  }

  function setCompleted(lessonId, value) {
    try {
      localStorage.setItem(completedKey(lessonId), value ? "true" : "false");
    } catch (error) {
      // Ignore storage failure; UI still updates for the current page.
    }
  }

  function getInitialLesson() {
    const params = new URLSearchParams(window.location.search);
    const requested = params.get("lesson");
    if (requested === "home" || lessonById.has(requested)) return requested;

    const legacyHash = window.location.hash.replace("#", "");
    if (legacyHashLessons[legacyHash]) return legacyHashLessons[legacyHash];

    return "home";
  }

  function updateCollapsedGroups(activeLessonId) {
    document.querySelectorAll(".lesson-group").forEach((group) => {
      const key = group.dataset.chapter;
      const header = group.querySelector(".lesson-group-header");
      const bodyEl = group.querySelector(".lesson-group-body");
      const hasActive = Boolean(group.querySelector(`[data-lesson-link="${activeLessonId}"]`));
      let collapsed = false;
      try {
        const stored = localStorage.getItem(`collapsed_${key}`);
        collapsed = stored === null ? !hasActive : stored === "true";
      } catch (error) {
        collapsed = !hasActive;
      }
      group.classList.toggle("is-collapsed", collapsed);
      header?.setAttribute("aria-expanded", String(!collapsed));
      if (bodyEl) bodyEl.style.maxHeight = collapsed ? "0px" : `${bodyEl.scrollHeight}px`;
    });
  }

  function updateCompletionUi() {
    const completedCount = lessons.filter((lesson) => isCompleted(lesson.id)).length;
    const total = lessons.length || 1;
    const pct = Math.round((completedCount / total) * 100);
    if (progressFill) progressFill.style.width = `${pct}%`;
    document.querySelectorAll("[data-total-progress]").forEach((el) => {
      el.textContent = `${pct}%`;
    });

    document.querySelectorAll("[data-lesson-link]").forEach((link) => {
      const lessonId = link.dataset.lessonLink;
      const done = lessonId !== "home" && isCompleted(lessonId);
      link.classList.toggle("is-complete", done);
    });

    document.querySelectorAll(".mark-complete-btn").forEach((button) => {
      const lessonId = button.dataset.lesson;
      const done = isCompleted(lessonId);
      button.classList.toggle("is-complete", done);
      button.textContent = done ? "Completed" : "Mark as Complete";
    });

    chapters.forEach((chapter) => {
      const chapterCompleted = chapter.lessonIds.filter(isCompleted).length;
      const chapterTotal = chapter.lessonIds.length || 1;
      const card = document.querySelector(`[data-chapter-card="${chapter.key}"]`);
      if (!card) return;
      const bar = card.querySelector(".chapter-card-bar span");
      const text = card.querySelector(`[data-card-progress="${chapter.key}"]`);
      const start = card.querySelector(".chapter-start-btn");
      const nextLesson = chapter.lessonIds.find((lessonId) => !isCompleted(lessonId)) || chapter.lessonIds[0];
      if (bar) bar.style.width = `${(chapterCompleted / chapterTotal) * 100}%`;
      if (text) text.textContent = `${chapterCompleted} / ${chapterTotal} complete`;
      if (start) {
        start.textContent = chapterCompleted > 0 ? "Continue" : "Start";
        start.dataset.lessonLink = nextLesson;
        start.setAttribute("href", `?lesson=${nextLesson}`);
      }
    });
  }

  function showLesson(lessonId, options = {}) {
    const targetId = lessonId === "home" || lessonById.has(lessonId) ? lessonId : "home";
    const target = document.querySelector(`.lesson-content[data-lesson="${targetId}"]`);
    if (!target) return;

    document.querySelectorAll(".lesson-content").forEach((lesson) => {
      lesson.classList.toggle("is-active", lesson === target);
      lesson.hidden = lesson !== target;
    });
    if (typeof window.initRunnableCells === "function") {
      window.initRunnableCells(target);
    }

    document.querySelectorAll("[data-lesson-link]").forEach((link) => {
      link.classList.toggle("active", link.dataset.lessonLink === targetId);
    });

    const lesson = lessonById.get(targetId);
    const title = target.dataset.chapterTitle || lesson?.chapterTitle || "Course Dashboard";
    if (currentChapter) currentChapter.textContent = title;

    updateCollapsedGroups(targetId);

    if (!options.skipHistory) {
      const url = targetId === "home" ? "index.html?lesson=home" : `index.html?lesson=${targetId}`;
      history.pushState({ lesson: targetId }, "", url);
    }
    if (targetId !== "home") {
      try {
        localStorage.setItem("last_lesson", targetId);
      } catch (error) {
        // Ignore storage failure.
      }
    }

    setSidebarOpen(false);
    contentPanel?.scrollTo({ top: 0, behavior: options.instant ? "auto" : "smooth" });
    if (!options.instant) contentPanel?.focus({ preventScroll: true });
  }

  function wireLessonLinks() {
    document.addEventListener("click", (event) => {
      const link = event.target.closest("[data-lesson-link]");
      if (!link || !isLessonApp) return;
      const lessonId = link.dataset.lessonLink;
      if (!lessonId) return;
      event.preventDefault();
      showLesson(lessonId);
    });
  }

  function wireGroups() {
    document.querySelectorAll(".lesson-group-header").forEach((header) => {
      header.addEventListener("click", () => {
        const group = header.closest(".lesson-group");
        const key = group?.dataset.chapter;
        const collapsed = !group.classList.contains("is-collapsed");
        group.classList.toggle("is-collapsed", collapsed);
        header.setAttribute("aria-expanded", String(!collapsed));
        const bodyEl = group.querySelector(".lesson-group-body");
        if (bodyEl) bodyEl.style.maxHeight = collapsed ? "0px" : `${bodyEl.scrollHeight}px`;
        try {
          localStorage.setItem(`collapsed_${key}`, String(collapsed));
        } catch (error) {
          // Ignore storage failure.
        }
      });
    });
  }

  function wireCompletion() {
    document.addEventListener("click", (event) => {
      const button = event.target.closest(".mark-complete-btn");
      if (!button) return;
      setCompleted(button.dataset.lesson, true);
      updateCompletionUi();
    });
  }

  function wireProjectChecklists() {
    document.querySelectorAll("[data-checklist-key]").forEach((input) => {
      const key = `checklist_${input.dataset.checklistKey}`;
      try {
        input.checked = localStorage.getItem(key) === "true";
      } catch (error) {
        input.checked = false;
      }
      input.addEventListener("change", () => {
        try {
          localStorage.setItem(key, input.checked ? "true" : "false");
        } catch (error) {
          // Ignore storage failure; the checkbox still works for the current page.
        }
      });
    });
  }

  function wireLastLessonButton() {
    const button = document.getElementById("jumpLastBtn");
    if (!button) return;
    button.addEventListener("click", () => {
      let last = "ch0-welcome";
      try {
        last = localStorage.getItem("last_lesson") || last;
      } catch (error) {
        last = "ch0-welcome";
      }
      showLesson(lessonById.has(last) ? last : "ch0-welcome");
    });
  }

  function initFallbackPage() {
    if (!themeToggle && drawerToggle) {
      const button = document.createElement("button");
      button.className = "theme-toggle";
      button.type = "button";
      button.textContent = "Light";
      drawerToggle.insertAdjacentElement("beforebegin", button);
      themeToggle = button;
    }
    initTheme();
  }

  function initLessonApp() {
    initTheme();
    drawerToggle?.addEventListener("click", () => setSidebarOpen(!body.classList.contains("sidebar-open")));
    drawerScrim?.addEventListener("click", () => setSidebarOpen(false));
    wireLessonLinks();
    wireGroups();
    wireCompletion();
    wireProjectChecklists();
    wireLastLessonButton();
    updateCompletionUi();
    showLesson(getInitialLesson(), { skipHistory: true, instant: true });
    window.addEventListener("popstate", () => showLesson(getInitialLesson(), { skipHistory: true, instant: true }));
    window.addEventListener("resize", () => {
      const active = document.querySelector(".lesson-link.active")?.dataset.lessonLink || getInitialLesson();
      updateCollapsedGroups(active);
    });
  }

  if (isLessonApp) {
    initLessonApp();
  } else {
    initFallbackPage();
  }
})();
