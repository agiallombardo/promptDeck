(function () {
  const post = (msg) => {
    try {
      parent.postMessage(msg, "*");
    } catch (e) {}
  };

  function findSlides() {
    const byData = document.querySelectorAll("[data-slide]");
    if (byData.length) {
      return Array.from(byData).map((el, i) => ({
        index: i,
        el,
        title: el.getAttribute("data-title") || el.getAttribute("title") || "",
      }));
    }
    const body = document.body;
    if (!body) return [{ index: 0, el: document.documentElement, title: "" }];
    const sections = Array.from(body.children).filter((n) => n.tagName === "SECTION");
    if (sections.length) {
      return sections.map((el, i) => ({ index: i, el, title: "" }));
    }
    return [{ index: 0, el: body, title: "" }];
  }

  const slides = findSlides();
  const titles = slides.map((s) => s.title || "");

  function showOnly(active) {
    slides.forEach((s, i) => {
      s.el.style.display = i === active ? "" : "none";
    });
  }

  let commentMode = false;
  let current = 0;

  window.addEventListener("message", (ev) => {
    const d = ev.data;
    if (!d || typeof d !== "object") return;
    if (d.type === "goto" && typeof d.slide === "number") {
      current = Math.max(0, Math.min(d.slide, slides.length - 1));
      showOnly(current);
    }
    if (d.type === "setCommentMode") {
      commentMode = !!d.enabled;
      document.body.style.cursor = commentMode ? "crosshair" : "";
    }
  });

  document.addEventListener(
    "click",
    (ev) => {
      if (!commentMode) return;
      const rect = slides[current].el.getBoundingClientRect();
      const x = rect.width ? (ev.clientX - rect.left) / rect.width : 0;
      const y = rect.height ? (ev.clientY - rect.top) / rect.height : 0;
      post({
        type: "slide-click",
        slide: current,
        x: Math.max(0, Math.min(1, x)),
        y: Math.max(0, Math.min(1, y)),
      });
    },
    true,
  );

  post({
    type: "manifest",
    count: slides.length,
    titles,
  });

  showOnly(0);
})();
