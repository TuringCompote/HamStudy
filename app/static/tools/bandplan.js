// bandplan.js — Canadian amateur band explorer. Toggle your qualification and see
// which bands you may use. The exam-critical rule: Basic gives everything ABOVE
// 30 MHz; HF below 30 MHz needs Basic with Honours (≥80%) — or Advanced / Basic+5yr.
// Frequency edges per RBR-4 / the Canadian table; verify edge cases against RBR-4.
"use strict";
(function () {
  // hf:true => below 30 MHz (needs Honours). status: P=primary, S=secondary (amateur).
  const BANDS = [
    { name: "2200 m", lo: 0.1357, hi: 0.1378, hf: true, status: "S", note: "LF, CW/data" },
    { name: "630 m", lo: 0.472, hi: 0.479, hf: true, status: "S", note: "MF, low power" },
    { name: "160 m", lo: 1.8, hi: 2.0, hf: true, status: "P" },
    { name: "80 m", lo: 3.5, hi: 4.0, hf: true, status: "P" },
    { name: "60 m", lo: 5.3, hi: 5.4, hf: true, status: "S", note: "5 channels only" },
    { name: "40 m", lo: 7.0, hi: 7.3, hf: true, status: "P" },
    { name: "30 m", lo: 10.1, hi: 10.15, hf: true, status: "S", note: "CW/data only" },
    { name: "20 m", lo: 14.0, hi: 14.35, hf: true, status: "P" },
    { name: "17 m", lo: 18.068, hi: 18.168, hf: true, status: "P" },
    { name: "15 m", lo: 21.0, hi: 21.45, hf: true, status: "P" },
    { name: "12 m", lo: 24.89, hi: 24.99, hf: true, status: "P" },
    { name: "10 m", lo: 28.0, hi: 29.7, hf: true, status: "P" },
    { name: "6 m", lo: 50, hi: 54, hf: false, status: "P" },
    { name: "2 m", lo: 144, hi: 148, hf: false, status: "P" },
    { name: "1.25 m", lo: 222, hi: 225, hf: false, status: "P" },
    { name: "70 cm", lo: 430, hi: 450, hf: false, status: "S" },
    { name: "33 cm", lo: 902, hi: 928, hf: false, status: "S" },
    { name: "23 cm", lo: 1240, hi: 1300, hf: false, status: "S" },
  ];

  Elmer.register("bandplan", function (el) {
    let honours = false; // false = Basic only, true = Basic with Honours (or Advanced)

    const tog = Elmer.h("div", { class: "tool-toggle" });
    const bB = Elmer.h("button", { class: "btn seg active", type: "button" }, ["Basic"]);
    const bH = Elmer.h("button", { class: "btn seg", type: "button" }, ["Basic with Honours"]);
    bB.addEventListener("click", () => { honours = false; render(); });
    bH.addEventListener("click", () => { honours = true; render(); });
    tog.appendChild(bB); tog.appendChild(bH);

    const summary = Elmer.h("div", { class: "tool-readout" });
    const list = Elmer.h("div", { class: "bp-list" });
    const legend = Elmer.h("div", { class: "tool-note small muted" }, [
      "Lit = you may operate · dim = needs a higher qualification · ",
      "P = primary, S = secondary allocation. Edges per RBR-4 — verify specifics there.",
    ]);

    el.appendChild(tog); el.appendChild(summary); el.appendChild(list); el.appendChild(legend);
    render();

    function fmtFreq(mhz) {
      if (mhz < 1) return Math.round(mhz * 1000) + " kHz";
      return (Math.round(mhz * 1000) / 1000) + " MHz";
    }

    function render() {
      bB.classList.toggle("active", !honours);
      bH.classList.toggle("active", honours);
      const allowed = BANDS.filter((b) => !b.hf || honours).length;
      summary.innerHTML = honours
        ? `<b class="accent">Basic with Honours</b> unlocks <b>all ${BANDS.length} bands</b> — ` +
          `including HF below 30 MHz, at full power.`
        : `<b>Basic</b> covers the <b>${allowed} bands above 30 MHz</b>. ` +
          `HF below 30 MHz is locked until <b class="accent">Honours (≥80%)</b>.`;

      list.innerHTML = "";
      BANDS.forEach((b) => {
        const ok = !b.hf || honours;
        const row = Elmer.h("div", { class: "bp-row" + (ok ? " on" : " off") });
        row.appendChild(Elmer.h("span", { class: "bp-name mono" }, [b.name]));
        row.appendChild(Elmer.h("span", { class: "bp-range mono" }, [`${fmtFreq(b.lo)} – ${fmtFreq(b.hi)}`]));
        row.appendChild(Elmer.h("span", { class: "bp-status" }, [b.status + (b.note ? " · " + b.note : "")]));
        row.appendChild(Elmer.h("span", { class: "bp-lock" }, [ok ? "✓" : (b.hf ? "Honours" : "—")]));
        list.appendChild(row);
      });
    }
  });
})();
