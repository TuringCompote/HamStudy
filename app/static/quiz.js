// Quiz runner (vanilla JS). Talks to the JSON API; the server grades and records
// every answer to `attempts`. Drill = immediate feedback; exam = deferred results.
"use strict";

const el = (id) => document.getElementById(id);
const root = el("quiz");
const MODE = root.dataset.mode;
const SECTION = root.dataset.section ? Number(root.dataset.section) : null;
const OPTION_LETTERS = ["A", "B", "C", "D"];

let questions = [];
let idx = 0;
let answered = 0;
let correctCount = 0;
let results = [];          // {question, chosen, correct, correct_index}
let qStartedAt = 0;
let examStartedAt = 0;
let timerHandle = null;

async function api(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
  return res.json();
}

async function start() {
  try {
    const data = await api("/api/quiz", { mode: MODE, section: SECTION });
    questions = data.questions;
  } catch (e) {
    el("loading").textContent = "Could not load quiz: " + e.message;
    return;
  }
  el("loading").classList.add("hidden");
  el("card").classList.remove("hidden");
  examStartedAt = Date.now();
  if (MODE === "exam") startTimer();
  render();
}

function startTimer() {
  const t = el("timer");
  const tick = () => {
    const s = Math.floor((Date.now() - examStartedAt) / 1000);
    const m = String(Math.floor(s / 60)).padStart(2, "0");
    t.textContent = `${m}:${String(s % 60).padStart(2, "0")}`;
  };
  tick();
  timerHandle = setInterval(tick, 1000);
}

function render() {
  const q = questions[idx];
  el("progress").textContent = `Question ${idx + 1} of ${questions.length}`;
  el("stem").textContent = q.text;
  el("feedback").classList.add("hidden");
  el("next").classList.add("hidden");

  const ul = el("options");
  ul.innerHTML = "";
  q.options.forEach((opt, i) => {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.className = "option";
    btn.innerHTML = `<span class="letter">${OPTION_LETTERS[i]}</span> ${escapeHtml(opt)}`;
    btn.onclick = () => choose(i);
    li.appendChild(btn);
    ul.appendChild(li);
  });
  qStartedAt = Date.now();
}

async function choose(chosen) {
  const q = questions[idx];
  // lock the options
  document.querySelectorAll("#options .option").forEach((b) => (b.disabled = true));

  let res;
  try {
    res = await api("/api/attempt", {
      question_id: q.id,
      chosen_index: chosen,
      mode: MODE,
      response_ms: Date.now() - qStartedAt,
    });
  } catch (e) {
    el("feedback").textContent = "Error recording answer: " + e.message;
    el("feedback").classList.remove("hidden");
    document.querySelectorAll("#options .option").forEach((b) => (b.disabled = false));
    return;
  }

  answered++;
  if (res.correct) correctCount++;
  results.push({ q, chosen, correct: res.correct, correct_index: res.correct_index });

  if (MODE === "drill") {
    showFeedback(chosen, res);
  }
  el("next").classList.remove("hidden");
  el("next").textContent = idx + 1 < questions.length ? "Next" : "See results";
  el("next").focus();
}

function showFeedback(chosen, res) {
  const opts = document.querySelectorAll("#options .option");
  opts[res.correct_index].classList.add("correct");
  if (!res.correct) opts[chosen].classList.add("wrong");
  const fb = el("feedback");
  fb.textContent = res.correct
    ? "Correct."
    : `Not quite — the answer is ${OPTION_LETTERS[res.correct_index]}.`;
  fb.className = "feedback " + (res.correct ? "good" : "bad");
}

el("next").onclick = () => {
  idx++;
  if (idx < questions.length) render();
  else finish();
};

function finish() {
  if (timerHandle) clearInterval(timerHandle);
  el("card").classList.add("hidden");
  el("progress").textContent = "";
  const pct = answered ? Math.round((1000 * correctCount) / answered) / 10 : 0;
  const elapsed = Math.floor((Date.now() - examStartedAt) / 1000);

  // per-section breakdown
  const bySec = {};
  results.forEach((r) => {
    const s = r.q.section;
    bySec[s] = bySec[s] || { n: 0, c: 0 };
    bySec[s].n++;
    if (r.correct) bySec[s].c++;
  });

  const linesNote =
    MODE === "exam"
      ? `<div class="exam-lines">
           <span class="line pass">70% pass</span>
           <span class="line honours">80% Honours</span>
         </div>`
      : "";

  let rows = "";
  Object.keys(bySec)
    .sort((a, b) => a - b)
    .forEach((s) => {
      const b = bySec[s];
      const p = Math.round((1000 * b.c) / b.n) / 10;
      rows += `<tr><td>Section ${s}</td><td>${b.c}/${b.n}</td><td>${p}%</td></tr>`;
    });

  const verdict =
    MODE === "exam"
      ? pct >= 80
        ? `<p class="verdict ok">Honours-level — ${pct}% 🎉</p>`
        : pct >= 70
        ? `<p class="verdict warn">Pass (${pct}%), but below the 80% Honours bar.</p>`
        : `<p class="verdict bad">${pct}% — below the 70% pass line.</p>`
      : `<p class="verdict">${correctCount}/${answered} correct (${pct}%).</p>`;

  el("results").innerHTML = `
    <h2>Results</h2>
    <p class="score"><strong>${pct}%</strong> — ${correctCount}/${answered} correct
      ${MODE === "exam" ? `&middot; ${fmtTime(elapsed)}` : ""}</p>
    ${linesNote}
    ${verdict}
    <table class="section-table"><thead><tr><th>Section</th><th>Score</th><th>%</th></tr></thead>
      <tbody>${rows}</tbody></table>
    <div class="card-actions">
      <a class="btn btn-primary" href="/">Back to dashboard</a>
      <a class="btn" href="/quiz?mode=${MODE}${SECTION ? "&section=" + SECTION : ""}">Again</a>
    </div>`;
  el("results").classList.remove("hidden");
}

function fmtTime(s) {
  const m = String(Math.floor(s / 60)).padStart(2, "0");
  return `${m}:${String(s % 60).padStart(2, "0")}`;
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

start();
