// journal.js — one-week strip; days with an entry light up and are clickable.
// Scroll to earlier/later weeks; defaults to the current week.
"use strict";
const el = (id) => document.getElementById(id);
const WD = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

let weekOffset = 0;
let entryDates = new Set();

// local YYYY-MM-DD (avoid toISOString's UTC shift)
function iso(d) {
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}
function fmt(d) {
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

async function loadDates() {
  try {
    const r = await fetch("/api/journal/dates");
    entryDates = new Set((await r.json()).dates || []);
  } catch (e) {
    entryDates = new Set();
  }
}

async function loadEntry(di) {
  const out = el("jr-entry");
  out.innerHTML = "Loading…";
  out.classList.add("on");
  try {
    const r = await fetch("/api/journal/entry/" + di);
    if (!r.ok) { out.innerHTML = "<p class='muted'>No entry for that day.</p>"; return; }
    out.innerHTML = (await r.json()).html;
  } catch (e) {
    out.innerHTML = "<p class='muted'>Couldn't load that entry.</p>";
  }
}

function render() {
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const todayIso = iso(today);
  const start = new Date(today);
  start.setDate(today.getDate() - today.getDay() + weekOffset * 7); // Sunday start

  const days = el("jr-days");
  days.innerHTML = "";
  let first, last;
  for (let i = 0; i < 7; i++) {
    const d = new Date(start); d.setDate(start.getDate() + i);
    const di = iso(d);
    if (i === 0) first = d; if (i === 6) last = d;
    const lit = entryDates.has(di);
    const cell = document.createElement("button");
    cell.type = "button";
    cell.className = "jr-day" + (lit ? " lit" : "") + (di === todayIso ? " today" : "");
    cell.disabled = !lit;
    cell.innerHTML = `<span class="jr-wd">${WD[d.getDay()]}</span><span class="jr-dn mono">${d.getDate()}</span>`;
    if (lit) cell.onclick = () => loadEntry(di);
    days.appendChild(cell);
  }
  el("jr-range").textContent =
    `${fmt(first)} – ${fmt(last)}` + (weekOffset === 0 ? "  (this week)" : "");
}

// Only wire up if the journal strip is on this page (it's embedded on the dashboard).
if (el("jr-days")) {
  el("jr-prev").onclick = () => { weekOffset--; render(); };
  el("jr-next").onclick = () => { weekOffset++; render(); };

  const writeBtn = el("jr-write");
  if (writeBtn) {
    writeBtn.onclick = async function () {
      this.disabled = true; const label = this.textContent; this.textContent = "Writing…";
      try {
        await fetch("/api/journal", { method: "POST" });
        await loadDates();
        weekOffset = 0;
        render();
        loadEntry(iso(new Date()));
        this.textContent = "Saved";
      } catch (e) {
        this.textContent = "Failed";
      }
      setTimeout(() => { this.textContent = label; this.disabled = false; }, 1500);
    };
  }

  (async () => {
    await loadDates();
    render();
    const td = iso(new Date());
    if (entryDates.has(td)) loadEntry(td);   // auto-open today if present
  })();
}
