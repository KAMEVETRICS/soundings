const form = document.getElementById("claw-form");
const statusEl = document.getElementById("claw-status");
const answerEl = document.getElementById("claw-answer");

if (form) {
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
