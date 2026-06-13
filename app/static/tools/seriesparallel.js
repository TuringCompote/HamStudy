// seriesparallel.js — combine resistors OR capacitors in series or parallel.
// Add/remove values; the equivalent and a simple schematic update live.
//   R series: ΣR     R parallel: 1/Σ(1/R)
//   C series: 1/Σ(1/C)  C parallel: ΣC   (capacitors are the mirror image)
"use strict";
(function () {
  Elmer.register("seriesparallel", function (el) {
    let kind = "R";          // 'R' or 'C'
    let arr = "series";      // 'series' or 'parallel'
    let vals = [100, 100];

    const unit = () => (kind === "R" ? "Ω" : "pF");

    // toggles
    const kindTog = seg(["R", "C"], (v) => { kind = v; render(); });
    const arrTog = seg(["series", "parallel"], (v) => { arr = v; render(); });
    const togRow = Elmer.h("div", { class: "tool-toggle" }, [
      labelWrap("Component", kindTog.root), labelWrap("Arrangement", arrTog.root),
    ]);

    const list = Elmer.h("div", { class: "sp-list" });
    const addBtn = Elmer.h("button", { class: "btn", type: "button" }, ["+ add"]);
    addBtn.addEventListener("click", () => { vals.push(kind === "R" ? 100 : 100); render(); });

    const readout = Elmer.h("div", { class: "tool-readout mono" });
    const svg = Elmer.h("svg", { class: "tool-svg", viewBox: "0 0 320 140", width: "100%", height: "auto" });

    el.appendChild(togRow);
    el.appendChild(list);
    el.appendChild(addBtn);
    el.appendChild(svg);
    el.appendChild(readout);
    render();

    function render() {
      kindTog.set(kind); arrTog.set(arr);
      // rebuild value inputs
      list.innerHTML = "";
      vals.forEach((v, i) => {
        const inp = Elmer.h("input", { type: "number", step: "any", class: "tool-input mono", value: v });
        inp.addEventListener("input", () => { vals[i] = parseFloat(inp.value); compute(); });
        const rm = Elmer.h("button", { class: "btn sp-rm", type: "button", title: "remove" }, ["×"]);
        rm.addEventListener("click", () => { if (vals.length > 1) { vals.splice(i, 1); render(); } });
        list.appendChild(Elmer.h("div", { class: "sp-row" }, [
          Elmer.h("span", { class: "tool-label" }, [`${kind}${i + 1} (${unit()})`]), inp, rm,
        ]));
      });
      compute();
      draw();
    }

    function equivalent() {
      const v = vals.filter((x) => isFinite(x) && x > 0);
      if (!v.length) return NaN;
      const addDirect = (kind === "R" && arr === "series") || (kind === "C" && arr === "parallel");
      if (addDirect) return v.reduce((a, b) => a + b, 0);
      return 1 / v.reduce((a, b) => a + 1 / b, 0);          // reciprocal combine
    }

    function compute() {
      const eq = equivalent();
      const rule = (kind === "R")
        ? (arr === "series" ? "series resistances add" : "parallel: 1/Σ(1/R), below the smallest")
        : (arr === "parallel" ? "parallel capacitances add" : "series: 1/Σ(1/C), below the smallest");
      readout.innerHTML = `Equivalent ${kind} = <b class="accent">${Elmer.fmt(eq, unit())}</b> ` +
        `<span class="muted">— ${rule}</span>`;
    }

    function draw() {
      svg.innerHTML = "";
      const n = vals.length;
      const box = (x, y, w, h) => Elmer.h("rect", { x, y, width: w, height: h, rx: 3, class: "node" });
      const wire = (x1, y1, x2, y2) => Elmer.h("line", { x1, y1, x2, y2, class: "wire" });
      if (arr === "series") {
        const y = 70; let x = 20;
        const gap = (280) / n;
        svg.appendChild(wire(10, y, 20, y));
        vals.forEach((_, i) => {
          svg.appendChild(box(x, y - 12, gap - 16, 24));
          svg.appendChild(Elmer.h("text", { x: x + (gap - 16) / 2, y: y + 4, class: "svg-val", "text-anchor": "middle" }, [kind + (i + 1)]));
          svg.appendChild(wire(x + gap - 16, y, x + gap, y));
          x += gap;
        });
      } else {
        const x1 = 40, x2 = 280; let y = 30;
        const step = Math.min(34, 100 / n);
        svg.appendChild(wire(20, 70, x1, 70));
        svg.appendChild(wire(x2, 70, 300, 70));
        vals.forEach((_, i) => {
          svg.appendChild(wire(x1, 70, x1, y)); svg.appendChild(wire(x1, y, x1 + 30, y));
          svg.appendChild(box(x1 + 30, y - 10, 160, 20));
          svg.appendChild(Elmer.h("text", { x: x1 + 110, y: y + 4, class: "svg-val", "text-anchor": "middle" }, [kind + (i + 1)]));
          svg.appendChild(wire(x1 + 190, y, x2, y)); svg.appendChild(wire(x2, y, x2, 70));
          y += step + 14;
        });
      }
    }

    // a small segmented toggle helper
    function seg(opts, onPick) {
      const root = Elmer.h("div", { class: "tool-toggle" });
      const btns = {};
      opts.forEach((o) => {
        const b = Elmer.h("button", { class: "btn seg", type: "button" }, [o]);
        b.addEventListener("click", () => onPick(o));
        btns[o] = b; root.appendChild(b);
      });
      return { root, set: (v) => opts.forEach((o) => btns[o].classList.toggle("active", o === v)) };
    }
    function labelWrap(label, node) {
      return Elmer.h("div", { class: "tool-field" }, [Elmer.h("span", { class: "tool-label" }, [label]), node]);
    }
  });
})();
