(function () {
  const post = (msg) => {
    try {
      parent.postMessage(msg, "*");
    } catch (e) {}
  };

  function parseCounterText(text) {
    const m = text.match(/\b(\d{1,3})\s*\/\s*(\d{1,3})\b/);
    if (!m) return null;
    const cur = Number(m[1]);
    const total = Number(m[2]);
    if (!Number.isFinite(cur) || !Number.isFinite(total)) return null;
    if (total < 1 || cur < 1 || cur > total) return null;
    return { current: cur - 1, total };
  }

  function findCounterState() {
    const nodes = document.querySelectorAll("body *");
    let best = null;
    for (const node of nodes) {
      const text = (node.textContent || "").trim();
      if (!text || text.length > 32) continue;
      const parsed = parseCounterText(text);
      if (!parsed) continue;
      if (best == null || parsed.total > best.total) best = parsed;
    }
    return best;
  }

  function titleForNode(el) {
    return (
      el.getAttribute("data-title") ||
      el.getAttribute("title") ||
      el.getAttribute("aria-label") ||
      ""
    );
  }

  function slidesFromSelector(selector) {
    const nodes = Array.from(document.querySelectorAll(selector));
    if (nodes.length < 2) return null;
    return nodes.map((el, i) => ({ index: i, el, title: titleForNode(el) }));
  }

  function findDeckState() {
    const selectorOrder = [
      "[data-slide]",
      "[data-slide-index]",
      '[aria-roledescription="slide"]',
      "body > section",
      "main > section",
      "main > article.slide",
      "body article.slide",
    ];
    for (const selector of selectorOrder) {
      const slides = slidesFromSelector(selector);
      if (slides && slides.length) {
        return { slides, current: 0 };
      }
    }
    const counter = findCounterState();
    const body = document.body;
    if (counter && counter.total > 1 && body) {
      const slides = Array.from({ length: counter.total }, (_x, i) => ({
        index: i,
        el: body,
        title: "",
      }));
      return { slides, current: Math.max(0, Math.min(counter.current, counter.total - 1)) };
    }
    if (!body) {
      return {
        slides: [{ index: 0, el: document.documentElement, title: "" }],
        current: 0,
      };
    }
    return { slides: [{ index: 0, el: body, title: "" }], current: 0 };
  }

  let deckState = findDeckState();
  let slides = deckState.slides;
  let titles = slides.map((s) => s.title || "");
  let lastManifestSig = "";

  function showOnly(active) {
    const uniqueEls = new Set(slides.map((s) => s.el));
    if (uniqueEls.size < 2) return;
    slides.forEach((s, i) => {
      s.el.style.display = i === active ? "" : "none";
    });
  }

  function postManifestIfChanged() {
    titles = slides.map((s) => s.title || "");
    const sig = `${slides.length}|${titles.join("\u241f")}`;
    if (sig === lastManifestSig) return;
    lastManifestSig = sig;
    post({
      type: "manifest",
      count: slides.length,
      titles,
    });
  }

  let commentMode = false;
  let current = Math.max(0, Math.min(deckState.current, slides.length - 1));

  function recomputeDeckState() {
    const next = findDeckState();
    slides = next.slides;
    if (slides.length <= 1) {
      current = 0;
    } else if (next.current >= 0 && next.current < slides.length) {
      // Keep in sync with decks that expose an in-slide counter (e.g. "2 / 6").
      current = next.current;
    } else {
      current = Math.max(0, Math.min(current, slides.length - 1));
    }
    showOnly(current);
    postManifestIfChanged();
  }

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

  let rescanTimer = null;
  function scheduleRescan() {
    if (rescanTimer != null) window.clearTimeout(rescanTimer);
    rescanTimer = window.setTimeout(() => {
      rescanTimer = null;
      recomputeDeckState();
    }, 120);
  }

  if (typeof MutationObserver !== "undefined") {
    const observer = new MutationObserver(() => scheduleRescan());
    const root = document.body || document.documentElement;
    if (root) {
      observer.observe(root, {
        subtree: true,
        childList: true,
        attributes: true,
        characterData: true,
      });
    }
  }

  window.addEventListener("load", () => scheduleRescan(), { once: true });

  // Some decks render slide chrome asynchronously after script load.
  let rescansLeft = 12;
  const interval = window.setInterval(() => {
    rescansLeft -= 1;
    recomputeDeckState();
    if (rescansLeft <= 0) {
      window.clearInterval(interval);
    }
  }, 500);

  recomputeDeckState();
})();
