const body = document.body;
    const drawerToggle = document.getElementById("drawerToggle");
    const drawerScrim = document.getElementById("drawerScrim");
    const progressFill = document.getElementById("progressFill");
    const currentChapter = document.getElementById("currentChapter");
    const navLinks = Array.from(document.querySelectorAll(".nav-tree a[href]"));
    const legacyHashRoutes = {
      "chapter-0": "chapter-0.html",
      "build": "chapter-0.html",
      "tools": "chapter-0.html",
      "reading-tips": "chapter-0.html",
      "python": "chapter-1-python.html",
      "python-colab": "chapter-1-python.html",
      "variables": "chapter-1-python.html",
      "data-structures": "chapter-1-python.html",
      "control-flow": "chapter-1-python.html",
      "loops": "chapter-1-python.html",
      "functions": "chapter-1-python.html",
      "libraries": "chapter-1-python.html",
      "checkpoint": "chapter-1-python.html",
      "what-is-ml": "chapter-2-ml.html",
      "types": "chapter-2-ml.html",
      "when-to-use": "chapter-2-ml.html",
      "supervised": "chapter-3-supervised.html",
      "classification-regression": "chapter-3-supervised.html",
      "algorithms": "chapter-3-supervised.html",
      "ml-pipeline": "chapter-3-supervised.html",
      "robot-failure-project": "chapter-3-supervised.html",
      "unsupervised": "chapter-4-unsupervised.html",
      "clustering": "chapter-4-unsupervised.html",
      "kmeans": "chapter-4-unsupervised.html",
      "sensor-cluster-project": "chapter-4-unsupervised.html",
      "reinforcement-learning": "chapter-5-rl.html",
      "q-learning": "chapter-5-rl.html",
      "maze-project": "chapter-5-rl.html",
      "computer-vision": "chapter-6-vision.html",
      "opencv": "chapter-6-vision.html",
      "tensorflow": "chapter-6-vision.html",
      "cnn": "chapter-6-vision.html",
      "traffic-sign-project": "chapter-6-vision.html",
      "whats-next": "chapter-7-next.html",
      "decision-guide": "chapter-7-next.html",
      "roadmap": "chapter-7-next.html",
      "papers": "chapter-7-next.html",
      "projects": "student-projects.html"
    };

    const requestedHash = window.location.hash.slice(1);
    if (requestedHash && !document.getElementById(requestedHash) && legacyHashRoutes[requestedHash]) {
      window.location.replace(`${legacyHashRoutes[requestedHash]}#${requestedHash}`);
    }

    if (window.hljs) {
      window.hljs.highlightAll();
    }

    function setDrawer(open) {
      body.classList.toggle("drawer-open", open);
      drawerToggle.setAttribute("aria-expanded", String(open));
      drawerToggle.setAttribute("aria-label", open ? "Close navigation drawer" : "Open navigation drawer");
    }

    drawerToggle.addEventListener("click", () => setDrawer(!body.classList.contains("drawer-open")));
    drawerScrim.addEventListener("click", () => setDrawer(false));
    navLinks.forEach(link => link.addEventListener("click", () => setDrawer(false)));

    document.querySelectorAll("a[href^='#']").forEach(link => {
      link.addEventListener("click", () => setDrawer(false));
    });

    function updateProgress() {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      const pct = max > 0 ? (window.scrollY / max) * 100 : 0;
      progressFill.style.width = `${Math.min(100, Math.max(0, pct))}%`;
    }
    document.addEventListener("scroll", updateProgress, { passive: true });
    window.addEventListener("resize", updateProgress);
    updateProgress();

    document.querySelectorAll(".code-card").forEach((figure) => {
      const caption = figure.querySelector("figcaption");
      const code = figure.querySelector("code");
      if (!caption || !code || caption.querySelector(".copy-btn")) return;

      const button = document.createElement("button");
      button.className = "copy-btn";
      button.type = "button";
      button.textContent = "Copy";
      button.setAttribute("aria-label", "Copy code block");
      button.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(code.innerText);
          button.textContent = "Copied";
          setTimeout(() => { button.textContent = "Copy"; }, 1200);
        } catch (error) {
          button.textContent = "Select code";
          setTimeout(() => { button.textContent = "Copy"; }, 1600);
        }
      });
      caption.appendChild(button);
    });

    const observed = Array.from(document.querySelectorAll(".observe[id]"));
    const activeObserver = new IntersectionObserver((entries) => {
      const visible = entries
        .filter(entry => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (!visible) return;

      const id = visible.target.id;
      const title = visible.target.dataset.title || visible.target.querySelector("h2,h3,h1")?.textContent || "ML x Robotics";
      currentChapter.textContent = title;
      navLinks.forEach(link => {
        let isActive = false;
        try {
          const linkUrl = new URL(link.getAttribute("href"), window.location.href);
          const samePage = linkUrl.pathname === window.location.pathname;
          isActive = samePage && linkUrl.hash === `#${id}`;
        } catch (error) {
          isActive = link.getAttribute("href") === `#${id}`;
        }
        link.classList.toggle("active", isActive);
        if (isActive) {
          const details = link.closest("details");
          if (details) details.open = true;
        }
      });
    }, { rootMargin: "-18% 0px -70% 0px", threshold: [0.05, 0.2, 0.45] });
    observed.forEach(section => activeObserver.observe(section));

    document.querySelectorAll(".sortable").forEach(table => {
      const tbody = table.querySelector("tbody");
      table.querySelectorAll(".table-sort").forEach(button => {
        let ascending = true;
        button.addEventListener("click", () => {
          const index = Number(button.dataset.sort);
          const rows = Array.from(tbody.querySelectorAll("tr"));
          rows.sort((a, b) => {
            const left = a.children[index].textContent.trim();
            const right = b.children[index].textContent.trim();
            return ascending ? left.localeCompare(right) : right.localeCompare(left);
          });
          ascending = !ascending;
          rows.forEach(row => tbody.appendChild(row));
        });
      });
    });
