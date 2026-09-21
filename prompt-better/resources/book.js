(function () {
  const RESPONSE = 0.4;
  const ZETA = 1.0;
  const reduceMotion = function () {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  };

  let raf = 0;
  let current = 0;
  let velocity = 0;
  let target = 0;
  let lastTime = 0;

  function maxY() {
    const scroller = document.scrollingElement || document.documentElement;
    return Math.max(0, scroller.scrollHeight - window.innerHeight);
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function rubberband(overshoot, dimension, constant) {
    const c = constant === undefined ? 0.55 : constant;
    return (overshoot * dimension * c) / (dimension + c * Math.abs(overshoot));
  }

  function stopSpring() {
    if (raf) window.cancelAnimationFrame(raf);
    raf = 0;
    lastTime = 0;
  }

  function grab() {
    if (!raf) return;
    stopSpring();
    current = window.scrollY;
    velocity = 0;
  }

  window.addEventListener("wheel", grab, { passive: true });
  window.addEventListener("pointerdown", grab, { passive: true });
  window.addEventListener("keydown", function (event) {
    if (
      event.key === "ArrowDown" ||
      event.key === "ArrowUp" ||
      event.key === "PageDown" ||
      event.key === "PageUp" ||
      event.key === "Home" ||
      event.key === "End" ||
      event.key === " "
    ) {
      grab();
    }
  });

  function step(now) {
    const dt = lastTime ? Math.min(0.032, (now - lastTime) / 1000) : 1 / 60;
    lastTime = now;
    const omega = (2 * Math.PI) / RESPONSE;
    const displacement = current - target;
    const acceleration =
      -2 * ZETA * omega * velocity - omega * omega * displacement;
    velocity += acceleration * dt;
    current += velocity * dt;

    const limit = maxY();
    if (current < 0) {
      current = rubberband(current, window.innerHeight);
      velocity *= 0.6;
      if (current > -0.5) {
        current = 0;
        velocity = 0;
      }
    } else if (current > limit) {
      current = limit + rubberband(current - limit, window.innerHeight);
      velocity *= 0.6;
      if (current < limit + 0.5) {
        current = limit;
        velocity = 0;
      }
    }

    window.scrollTo(0, current);

    if (Math.abs(current - target) < 0.5 && Math.abs(velocity) < 10) {
      window.scrollTo(0, target);
      stopSpring();
      return;
    }
    raf = window.requestAnimationFrame(step);
  }

  function markCurrent(id) {
    document.querySelectorAll(".spine a").forEach(function (link) {
      if (link.getAttribute("href") === "#" + id) {
        link.setAttribute("aria-current", "true");
      } else {
        link.removeAttribute("aria-current");
      }
    });
  }

  window.scrollToSection = function (id) {
    const node = document.getElementById(id);
    if (!node) return;
    markCurrent(id);
    current = window.scrollY;
    target = clamp(
      node.getBoundingClientRect().top + window.scrollY,
      0,
      maxY()
    );
    if (reduceMotion()) {
      stopSpring();
      window.scrollTo(0, target);
      return;
    }
    if (!raf) {
      lastTime = 0;
      raf = window.requestAnimationFrame(step);
    }
  };

  document.querySelectorAll(".spine a").forEach(function (link) {
    link.addEventListener("pointerdown", function () {
      if (reduceMotion()) return;
      link.style.transform = "scale(0.97)";
    });
    link.addEventListener("pointerup", function () {
      link.style.transform = "";
    });
    link.addEventListener("pointercancel", function () {
      link.style.transform = "";
    });
    link.addEventListener("click", function (event) {
      const href = link.getAttribute("href");
      if (!href || href.charAt(0) !== "#") return;
      event.preventDefault();
      window.scrollToSection(href.slice(1));
    });
  });

  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      function (entries) {
        if (raf) return;
        let best = null;
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          if (!best || entry.intersectionRatio > best.intersectionRatio) {
            best = entry;
          }
        });
        if (best && best.target.id) markCurrent(best.target.id);
      },
      { rootMargin: "-15% 0px -55% 0px", threshold: [0.1, 0.25, 0.5] }
    );
    document.querySelectorAll("article[id]").forEach(function (article) {
      observer.observe(article);
    });
  }
})();
