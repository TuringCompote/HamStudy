// propagation.js — ionospheric propagation, made visual. Toggle day/night and
// sweep frequency: watch a sky-wave ray refract back below the MUF or punch
// through above it, and see the D layer absorb low HF by day. Numbers are
// teaching approximations (real MUF depends on the sun, path, and season).
"use strict";
(function () {
  Elmer.register("propagation", function (el) {
    let day = true;
    let f = 14; // MHz

    // approximate teaching values
    const muf = () => (day ? 28 : 9);          // higher by day (more ionization)
    const dAbsorbBelow = () => (day ? 7 : 0);  // D layer absorbs low HF by day only

    const tog = Elmer.h("div", { class: "tool-toggle" });
    const bDay = Elmer.h("button", { class: "btn seg active", type: "button" }, ["Day"]);
    const bNight = Elmer.h("button", { class: "btn seg", type: "button" }, ["Night"]);
    bDay.addEventListener("click", () => { day = true; render(); });
    bNight.addEventListener("click", () => { day = false; render(); });
    tog.appendChild(bDay); tog.appendChild(bNight);

    const fWrap = Elmer.h("label", { class: "tool-field" }, [
      Elmer.h("span", { class: "tool-label" }, ["Frequency (MHz)"]),
    ]);
    const fRange = Elmer.h("input", { type: "range", min: "1", max: "30", step: "0.5", value: f, class: "tool-range" });
    const fNum = Elmer.h("input", { type: "number", min: "1", max: "30", step: "0.5", value: f, class: "tool-input mono" });
    fRange.addEventListener("input", () => { f = +fRange.value; fNum.value = f; render(); });
    fNum.addEventListener("input", () => { f = +fNum.value; fRange.value = f; render(); });
    fWrap.appendChild(fNum); fWrap.appendChild(fRange);

    const svg = buildScene();
    const readout = Elmer.h("div", { class: "tool-readout" });

    el.appendChild(tog); el.appendChild(fWrap); el.appendChild(svg.root); el.appendChild(readout);
    render();

    function render() {
      bDay.classList.toggle("active", day);
      bNight.classList.toggle("active", !day);
      const M = muf(), absorb = dAbsorbBelow();
      let mode, msg;
      if (absorb && f < absorb) {
        mode = "absorbed";
        msg = `At ${f} MHz by day the <b>D layer absorbs</b> the signal — only short ground-wave range. ` +
              `(These low bands open at night when D fades.)`;
      } else if (f <= M) {
        mode = "skip";
        msg = `${f} MHz is below the MUF (~${M} MHz ${day ? "by day" : "at night"}) — the signal ` +
              `<b class="accent">refracts off the F layer</b> and returns far away (sky-wave DX).`;
      } else {
        mode = "penetrate";
        msg = `${f} MHz is above the MUF (~${M} MHz) — the signal <b>punches through</b> the ` +
              `ionosphere into space. Drop frequency or wait for higher ionization.`;
      }
      readout.innerHTML = msg;
      svg.update(day, mode);
    }
  });

  function buildScene() {
    const W = 320, H = 200;
    const svg = Elmer.h("svg", {
      class: "tool-svg", viewBox: `0 0 ${W} ${H}`, width: "100%", height: "auto",
      role: "img", "aria-label": "Ionospheric propagation scene",
    });
    const sky = Elmer.h("rect", { x: 0, y: 0, width: W, height: H, rx: 6 });
    sky.setAttribute("class", "prop-sky");
    svg.appendChild(sky);

    // ionosphere layers (arcs as dashed lines)
    const layer = (y, label, cls) => {
      const ln = Elmer.h("line", { x1: 10, y1: y, x2: W - 10, y2: y });
      ln.setAttribute("class", "prop-layer " + cls);
      svg.appendChild(ln);
      svg.appendChild(Elmer.h("text", { x: W - 12, y: y - 3, class: "svg-val", "text-anchor": "end" }, [label]));
      return ln;
    };
    const fLayer = layer(40, "F", "f");
    const eLayer = layer(70, "E", "e");
    const dLayer = layer(95, "D", "d");

    // ground
    svg.appendChild(Elmer.h("rect", { x: 0, y: H - 24, width: W, height: 24, class: "prop-ground" }));
    // TX antenna
    svg.appendChild(Elmer.h("line", { x1: 40, y1: H - 24, x2: 40, y2: H - 48, class: "wire" }));
    svg.appendChild(Elmer.h("text", { x: 40, y: H - 52, class: "svg-val", "text-anchor": "middle" }, ["TX"]));

    const ray = Elmer.h("polyline", { class: "prop-ray" });
    svg.appendChild(ray);
    const arrow = Elmer.h("text", { class: "svg-val accent" }, [""]);
    svg.appendChild(arrow);

    function update(day, mode) {
      sky.setAttribute("class", "prop-sky " + (day ? "is-day" : "is-night"));
      // D layer only meaningful by day
      dLayer.style.opacity = day ? "0.9" : "0.15";
      const x0 = 40, y0 = H - 48, fY = 40;
      if (mode === "skip") {
        // up to F layer, back down to the right (one hop)
        ray.setAttribute("points", `${x0},${y0} 150,${fY} 280,${H - 24}`);
        arrow.textContent = "↩ returns to Earth";
        arrow.setAttribute("x", 250); arrow.setAttribute("y", H - 30);
      } else if (mode === "penetrate") {
        ray.setAttribute("points", `${x0},${y0} 170,${fY} 250,8`);
        arrow.textContent = "↗ into space";
        arrow.setAttribute("x", 235); arrow.setAttribute("y", 16);
      } else { // absorbed — short ground hop, stopped at D
        ray.setAttribute("points", `${x0},${y0} 120,95`);
        arrow.textContent = "✕ absorbed (D)";
        arrow.setAttribute("x", 130); arrow.setAttribute("y", 92);
      }
    }
    return { root: svg, update };
  }
})();
