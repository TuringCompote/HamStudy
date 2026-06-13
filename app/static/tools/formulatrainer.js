// formulatrainer.js — flashcards for the (unlabelled) exam formula sheet.
// Two directions: "what does it find? -> formula" or "formula -> what it finds".
// Self-rated; missed cards requeue. Client-side only (a study aid, not bank data).
"use strict";
(function () {
  Elmer.register("formulatrainer", function (el) {
    let all;
    try {
      all = JSON.parse(el.dataset.formulas || "[]");
    } catch (e) {
      el.innerHTML = '<p class="muted">Could not load formulas.</p>';
      return;
    }
    let dir = "findToFormula"; // or "formulaToFind"
    let queue = [];
    let revealed = false;
    let got = 0, seen = 0;

    // deterministic-ish shuffle (no Math.random dependence on order across loads
    // isn't important here, but keep it varied per session)
    function shuffle(a) {
      const arr = a.slice();
      for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(((Date.now() >> (i % 16)) ^ (i * 2654435761)) % (i + 1));
        const k = Math.abs(j) % (i + 1);
        [arr[i], arr[k]] = [arr[k], arr[i]];
      }
      return arr;
    }

    // --- controls ---
    const tog = Elmer.h("div", { class: "tool-toggle" });
    const bA = Elmer.h("button", { class: "btn seg active", type: "button" }, ["Find → formula"]);
    const bB = Elmer.h("button", { class: "btn seg", type: "button" }, ["Formula → find"]);
    bA.addEventListener("click", () => { dir = "findToFormula"; restart(); });
    bB.addEventListener("click", () => { dir = "formulaToFind"; restart(); });
    tog.appendChild(bA); tog.appendChild(bB);

    const progress = Elmer.h("div", { class: "tool-note small muted" });
    const card = Elmer.h("div", { class: "ft-card" });
    const front = Elmer.h("div", { class: "ft-front" });
    const back = Elmer.h("div", { class: "ft-back hidden" });
    card.appendChild(front); card.appendChild(back);

    const actions = Elmer.h("div", { class: "card-actions" });
    const revealBtn = Elmer.h("button", { class: "btn btn-primary", type: "button" }, ["Reveal"]);
    const gotBtn = Elmer.h("button", { class: "btn", type: "button" }, ["Got it ✓"]);
    const missBtn = Elmer.h("button", { class: "btn", type: "button" }, ["Review again ↻"]);
    revealBtn.addEventListener("click", reveal);
    gotBtn.addEventListener("click", () => next(true));
    missBtn.addEventListener("click", () => next(false));
    actions.appendChild(revealBtn); actions.appendChild(gotBtn); actions.appendChild(missBtn);

    el.appendChild(tog);
    el.appendChild(progress);
    el.appendChild(card);
    el.appendChild(actions);
    restart();

    function restart() {
      bA.classList.toggle("active", dir === "findToFormula");
      bB.classList.toggle("active", dir === "formulaToFind");
      queue = shuffle(all);
      got = 0; seen = 0;
      render();
    }

    function render() {
      revealed = false;
      back.classList.add("hidden");
      revealBtn.classList.remove("hidden");
      gotBtn.classList.add("hidden");
      missBtn.classList.add("hidden");
      if (!queue.length) {
        front.innerHTML = `<div class="ft-done">Deck cleared — ${got}/${seen} on the first pass. 🎉</div>`;
        const again = Elmer.h("button", { class: "btn btn-primary", type: "button" }, ["Restart"]);
        again.addEventListener("click", restart);
        actions.innerHTML = ""; actions.appendChild(again);
        progress.textContent = "";
        return;
      }
      const f = queue[0];
      if (dir === "findToFormula") {
        front.innerHTML = `<div class="ft-prompt">${escapeHtml(f.finds)}</div>` +
          `<div class="ft-hint muted small">recall the formula</div>`;
      } else {
        front.innerHTML = `<div class="ft-formula mono">${escapeHtml(f.formula)}</div>` +
          `<div class="ft-hint muted small">what does this compute?</div>`;
      }
      progress.textContent = `${queue.length} left · ${got}/${seen} correct this round`;
    }

    function reveal() {
      revealed = true;
      const f = queue[0];
      back.innerHTML =
        `<div class="ft-formula mono">${escapeHtml(f.formula)}</div>` +
        `<div class="ft-finds">${escapeHtml(f.finds)}</div>` +
        `<div class="ft-vars muted small">${escapeHtml(f.vars)}</div>`;
      back.classList.remove("hidden");
      revealBtn.classList.add("hidden");
      gotBtn.classList.remove("hidden");
      missBtn.classList.remove("hidden");
    }

    function next(knewIt) {
      if (!revealed) return;
      seen++;
      const card0 = queue.shift();
      if (knewIt) got++;
      else queue.push(card0); // requeue missed card at the end
      render();
    }

    function escapeHtml(s) {
      const d = document.createElement("div");
      d.textContent = s;
      return d.innerHTML;
    }
  });
})();
