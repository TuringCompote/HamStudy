// wavelength.js — frequency <-> wavelength, plus practical antenna lengths.
// λ(m) = 300 / f(MHz). Edit either field. Antenna lengths apply a velocity/
// shortening factor (default 0.95) for real wire.
"use strict";
(function () {
  const C_MHZ_M = 300; // speed of light ≈ 300 (MHz·m)

  Elmer.register("wavelength", function (el) {
    let vf = 0.95;

    const fInp = Elmer.h("input", { type: "number", step: "any", class: "tool-input mono", value: 14.2 });
    const lInp = Elmer.h("input", { type: "number", step: "any", class: "tool-input mono" });
    const vfInp = Elmer.h("input", { type: "number", step: "0.01", min: "0.5", max: "1", class: "tool-input mono", value: vf });

    const grid = Elmer.h("div", { class: "tool-grid" }, [
      Elmer.h("label", { class: "tool-field" }, [Elmer.h("span", { class: "tool-label" }, ["Frequency (MHz)"]), fInp]),
      Elmer.h("label", { class: "tool-field" }, [Elmer.h("span", { class: "tool-label" }, ["Wavelength λ (m)"]), lInp]),
      Elmer.h("label", { class: "tool-field" }, [Elmer.h("span", { class: "tool-label" }, ["Velocity factor"]), vfInp]),
    ]);

    const out = Elmer.h("div", { class: "tool-readout mono" });
    el.appendChild(grid);
    el.appendChild(out);

    fInp.addEventListener("input", fromF);
    lInp.addEventListener("input", fromL);
    vfInp.addEventListener("input", () => { vf = parseFloat(vfInp.value) || 0.95; fromF(); });

    function fromF() {
      const f = parseFloat(fInp.value);
      if (!isFinite(f) || f <= 0) { lInp.value = ""; out.textContent = "Frequency must be > 0."; return; }
      const lambda = C_MHZ_M / f;
      lInp.value = round(lambda);
      explain(f, lambda);
    }
    function fromL() {
      const lambda = parseFloat(lInp.value);
      if (!isFinite(lambda) || lambda <= 0) { fInp.value = ""; return; }
      const f = C_MHZ_M / lambda;
      fInp.value = round(f);
      explain(f, lambda);
    }
    function explain(f, lambda) {
      const dipole = (lambda / 2) * vf;     // ½λ dipole, shortened
      const vert = (lambda / 4) * vf;       // ¼λ vertical, shortened
      out.innerHTML =
        `λ = <b>${round(lambda)} m</b> &nbsp;·&nbsp; ` +
        `½λ dipole ≈ <b class="accent">${round(dipole)} m</b> ` +
        `(<span title="per half">${round(dipole / 2)} m each side</span>) &nbsp;·&nbsp; ` +
        `¼λ vertical ≈ <b class="accent">${round(vert)} m</b> ` +
        `<span class="muted">(vf ${vf})</span>`;
    }
    function round(x) {
      if (!isFinite(x)) return "";
      return Math.round(x * 1e3) / 1e3;
    }
    fromF();
  });
})();
