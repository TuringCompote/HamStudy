// decibel.js — ratio <-> dB, both power (10·log) and voltage (20·log), with
// S-unit context (6 dB ≈ 1 S-unit). Edit either the ratio or the dB field.
"use strict";
(function () {
  Elmer.register("decibel", function (el) {
    let mode = "power"; // 'power' (10log) or 'voltage' (20log)
    const k = () => (mode === "power" ? 10 : 20);

    // mode toggle
    const toggle = Elmer.h("div", { class: "tool-toggle" });
    const btnP = Elmer.h("button", { class: "btn seg active", type: "button" }, ["Power (10·log)"]);
    const btnV = Elmer.h("button", { class: "btn seg", type: "button" }, ["Voltage (20·log)"]);
    toggle.appendChild(btnP); toggle.appendChild(btnV);

    const ratioInp = Elmer.h("input", { type: "number", step: "any", class: "tool-input mono", value: 2 });
    const dbInp = Elmer.h("input", { type: "number", step: "any", class: "tool-input mono" });

    const grid = Elmer.h("div", { class: "tool-grid" }, [
      Elmer.h("label", { class: "tool-field" }, [
        Elmer.h("span", { class: "tool-label" }, ["Ratio (out / in)"]), ratioInp]),
      Elmer.h("label", { class: "tool-field" }, [
        Elmer.h("span", { class: "tool-label" }, ["Decibels (dB)"]), dbInp]),
    ]);

    const note = Elmer.h("div", { class: "tool-note muted small" });

    el.appendChild(toggle);
    el.appendChild(grid);
    el.appendChild(note);

    ratioInp.addEventListener("input", fromRatio);
    dbInp.addEventListener("input", fromDb);
    btnP.addEventListener("click", () => setMode("power"));
    btnV.addEventListener("click", () => setMode("voltage"));

    function setMode(m) {
      mode = m;
      btnP.classList.toggle("active", m === "power");
      btnV.classList.toggle("active", m === "voltage");
      fromRatio();
    }

    function fromRatio() {
      const r = parseFloat(ratioInp.value);
      if (!isFinite(r) || r <= 0) { dbInp.value = ""; note.textContent = "Ratio must be > 0."; return; }
      const db = k() * Math.log10(r);
      dbInp.value = round(db);
      explain(r, db);
    }
    function fromDb() {
      const db = parseFloat(dbInp.value);
      if (!isFinite(db)) { ratioInp.value = ""; return; }
      const r = Math.pow(10, db / k());
      ratioInp.value = round(r);
      explain(r, db);
    }
    function explain(r, db) {
      const sUnits = db / 6;
      const common =
        Math.abs(db - 3) < 0.2 ? " (≈ ×2 power)" :
        Math.abs(db - 10) < 0.2 ? " (= ×10 power)" :
        Math.abs(db + 3) < 0.2 ? " (≈ half power)" : "";
      note.innerHTML =
        `${k()}·log₁₀(${round(r)}) = <b>${round(db)} dB</b>${common} &nbsp;·&nbsp; ` +
        `on the S-meter that's <b>${round(sUnits)}</b> S-unit(s) (6 dB each).`;
    }
    function round(x) {
      if (!isFinite(x)) return "";
      const a = Math.abs(x);
      if (a !== 0 && (a < 1e-3 || a >= 1e6)) return x.toExponential(3);
      return Math.round(x * 1e3) / 1e3;
    }
    fromRatio();
  });
})();
