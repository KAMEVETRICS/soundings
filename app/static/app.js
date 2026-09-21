function bootClaw() {
  const form = document.getElementById("claw-form");
  const statusEl = document.getElementById("claw-status");
  const answerEl = document.getElementById("claw-answer");
  if (!form || form.dataset.bound) return;
  form.dataset.bound = "1";
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const question = (document.getElementById("q") || {}).value || "";
    if (statusEl) statusEl.textContent = "Loading…";
    if (answerEl) answerEl.hidden = true;
    try {
      const response = await fetch("/api/claw", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const data = await response.json();
      if (!data.ok) {
        if (statusEl) statusEl.textContent = data.error || "Claw failed.";
        return;
      }
      if (statusEl) statusEl.textContent = data.symbol || "";
      if (answerEl) {
        answerEl.hidden = false;
        answerEl.textContent = data.answer || "";
      }
    } catch (error) {
      if (statusEl) statusEl.textContent = String(error);
    }
  });
}

function markNav(url) {
  const path = new URL(url, location.origin).pathname;
  document.querySelectorAll(".sidebar nav a").forEach((link) => {
    const href = link.getAttribute("href") || "";
    const on =
      href === "/"
        ? path === "/"
        : href === "/screener"
          ? path === "/screener" || path.startsWith("/token/")
          : path === href;
    link.classList.toggle("on", on);
  });
}

async function swapTo(url, push) {
  const main = document.getElementById("main");
  if (!main) {
    location.href = url;
    return;
  }
  main.classList.add("is-loading");
  try {
    const response = await fetch(url, {
      headers: { Accept: "text/html", "X-Soundings-Nav": "1" },
    });
    const html = await response.text();
    const doc = new DOMParser().parseFromString(html, "text/html");
    const next = doc.getElementById("main");
    if (!next) {
      location.href = url;
      return;
    }
    main.replaceWith(next);
    document.title = doc.title;
    markNav(url);
    if (push) history.pushState({ url }, "", url);
    bootClaw();
  } catch (error) {
    location.href = url;
  }
}

function shouldHijack(anchor, event) {
  if (!anchor || anchor.target || anchor.hasAttribute("download")) return false;
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return false;
  let url;
  try {
    url = new URL(anchor.href, location.origin);
  } catch (error) {
    return false;
  }
  if (url.origin !== location.origin) return false;
  if (url.pathname.startsWith("/api") || url.pathname.startsWith("/static") || url.pathname.startsWith("/docs")) {
    return false;
  }
  return true;
}

document.addEventListener("click", (event) => {
  const anchor = event.target.closest("a");
  if (!shouldHijack(anchor, event)) return;
  event.preventDefault();
  const url = new URL(anchor.href, location.origin);
  swapTo(url.pathname + url.search, true);
});

document.addEventListener("submit", (event) => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement)) return;
  if (form.id === "claw-form") return;
  if ((form.getAttribute("method") || "get").toLowerCase() !== "get") return;
  event.preventDefault();
  const url = new URL(form.getAttribute("action") || location.pathname, location.origin);
  const data = new FormData(form);
  data.forEach((value, key) => {
    url.searchParams.set(key, String(value));
  });
  swapTo(url.pathname + url.search, true);
});

window.addEventListener("popstate", () => {
  swapTo(location.pathname + location.search, false);
});

bootClaw();
