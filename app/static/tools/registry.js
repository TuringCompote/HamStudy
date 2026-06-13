// registry.js — tiny mount framework for the interactive concept tools.
// Each tool file calls Elmer.register("<id>", fn); on load. On DOMContentLoaded
// we find every <div data-tool="<id>"> and hand it to its initializer.
// Tools are self-contained (SVG + vanilla JS) and theme from tokens.css.
"use strict";
window.Elmer = window.Elmer || { tools: {} };

Elmer.register = function (id, fn) {
  Elmer.tools[id] = fn;
};

Elmer.boot = function () {
  document.querySelectorAll("[data-tool]").forEach((el) => {
    const fn = Elmer.tools[el.dataset.tool];
    if (fn) {
      try {
        fn(el);
      } catch (e) {
        el.innerHTML = '<p class="muted">Tool failed to load.</p>';
        console.error("tool", el.dataset.tool, e);
      }
    }
  });
};

// shared helpers tools can use
Elmer.h = function (tag, attrs, children) {
  const ns = ["svg", "g", "line", "rect", "circle", "text", "path", "polyline"];
  const e = ns.includes(tag)
    ? document.createElementNS("http://www.w3.org/2000/svg", tag)
    : document.createElement(tag);
  for (const k in attrs || {}) {
    if (k === "class") e.setAttribute("class", attrs[k]);
    else if (k in e && !ns.includes(tag)) e[k] = attrs[k];
    else e.setAttribute(k, attrs[k]);
  }
  (children || []).forEach((c) =>
    e.appendChild(typeof c === "string" ? document.createTextNode(c) : c)
  );
  return e;
};

// format a number with sensible significant figures + optional unit
Elmer.fmt = function (x, unit) {
  if (!isFinite(x)) return "—";
  const a = Math.abs(x);
  let s;
  if (a !== 0 && (a < 1e-3 || a >= 1e6)) s = x.toExponential(3);
  else s = (Math.round(x * 1000) / 1000).toString();
  return unit ? s + " " + unit : s;
};

document.addEventListener("DOMContentLoaded", Elmer.boot);
