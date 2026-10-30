/* unzzz wake-up challenge — runs on the phone that opens a shortlink. */
(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const token = decodeURIComponent(location.pathname.split("/").filter(Boolean).pop() || "");
  const S = {
    data: null, offset: 0, timer: null, submitting: false,
    selection: { choice: null, color: null, cells: new Set() },
  };

  const esc = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));

  function setHeader(eyebrow, headline, sub) {
    $("#eyebrow").textContent = eyebrow;
    $("#headline").textContent = headline;
    $("#sub").textContent = sub;
  }

  function tz() { return S.data?.timezone || undefined; }

  function fmtHM(ts) {
    if (!ts) return "--:--";
    return new Intl.DateTimeFormat(window.UNZZZ_I18N?.locale, {
      timeZone: tz(), hour: "2-digit", minute: "2-digit", hourCycle: "h23",
    }).format(new Date(ts * 1000));
  }

  function fmtClock(ts) {
    return new Intl.DateTimeFormat(window.UNZZZ_I18N?.locale, {
      timeZone: tz(), hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
    }).format(new Date(ts * 1000));
  }

  function tick() {
    $("#clock").textContent = fmtClock(Date.now() / 1000 + S.offset);
  }

  function greeting() {
    const hour = Number(new Intl.DateTimeFormat(window.UNZZZ_I18N?.locale, {
      timeZone: tz(), hour: "2-digit", hourCycle: "h23",
    }).format(new Date(Date.now() + S.offset * 1000)));
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  }

  function stateWord(state) {
    return ({
      completed: "answered by everyone",
      stopped: "stopped by an admin",
      expired: "timed out",
      interrupted: "interrupted by a server restart",
      missed: "missed",
      snoozed: "snoozed",
      skipped: "skipped",
    }[state] || state);
  }

  function progressText(data) {
    const base = data.completion_mode === "count"
      ? `${data.answered_count}/${data.target_count} needed · ${data.total} selected`
      : `${data.answered_count} of ${data.total} answered`;
    return data.required > 1
      ? `${base} · ${data.solved}/${data.required} for you`
      : base;
  }

  function progressPercent(data) {
    if (data.completion_mode === "count") {
      return data.target_count ? Math.min(100, Math.round((data.answered_count / data.target_count) * 100)) : 0;
    }
    return data.total ? Math.round((data.answered_count / data.total) * 100) : 0;
  }

  function participantsHtml(data, withProgress = true) {
    const pct = progressPercent(data);
    const rows = data.participants.map((p) => `
      <li class="participant${p.answered ? " done" : ""}${p.you ? " you" : ""}">
        <span class="p-check">✓</span>
        <span class="p-name">${esc(p.name)}${p.you ? " (you)" : ""}</span>
        <span class="p-status">${p.answered
          ? "answered " + fmtHM(p.answered_at)
          : (p.required > 1 ? `${p.solved || 0}/${p.required} passed` : "waiting")}</span>
      </li>`).join("");
    return `
      ${withProgress ? `
        <div class="challenge-progress">
          <div class="row between">
            <span class="muted small">${esc(progressText(data))}</span>
            <span class="muted small">${pct}%</span>
          </div>
          <div class="progress"><span class="progress-fill" data-progress="${pct}"></span></div>
        </div>` : ""}
      <ul class="participant-list">${rows}</ul>`;
  }

  function applyProgressWidths() {
    document.querySelectorAll("[data-progress]").forEach((el) => {
      el.style.width = `${Number(el.dataset.progress) || 0}%`;
    });
  }

  function resetSelection() {
    S.selection = { choice: null, color: null, cells: new Set() };
  }

  function patternGridHtml(size, target, interactive) {
    const on = new Set(target || []);
    const cells = [];
    for (let i = 0; i < size * size; i++) {
      if (interactive) {
        cells.push(`<button class="paint-cell" type="button" data-cell="${i}" aria-label="Cell ${i + 1}"></button>`);
      } else {
        cells.push(`<span class="paint-cell${on.has(i) ? " on" : ""}"></span>`);
      }
    }
    return cells.join("");
  }

  function answerAreaHtml(data) {
    const type = data.challenge_type || (data.answer_type === "text" ? "text" : "math");
    const payload = data.payload || {};
    const attempts = data.attempts || 0;
    const feedback = `<p class="feedback" id="feedback">${attempts ? `${attempts} wrong ${attempts === 1 ? "try" : "tries"} — here is a fresh one.` : ""}</p>`;
    if (type === "choice" && Array.isArray(payload.options) && payload.options.length) {
      return `<div class="question-box" id="answer-area">
        <div class="choice-grid">${payload.options.map((opt) =>
          `<button class="choice-option" type="button" data-choice="${esc(opt)}" aria-pressed="false">${esc(opt)}</button>`
        ).join("")}</div>
        <form id="answer-form" autocomplete="off"><button class="btn primary wide" type="submit" id="answer-btn">Answer</button></form>
        ${feedback}
      </div>`;
    }
    if (type === "color" && payload.target && Array.isArray(payload.options)) {
      return `<div class="question-box" id="answer-area">
        <div class="color-target-wrap">
          <span class="swatch color-${esc(payload.target.key)}"></span>
          <div><div class="color-target-label">Target colour</div><div class="color-target-name">Match the swatch</div></div>
        </div>
        <div class="color-grid">${payload.options.map((c) =>
          `<button class="color-option" type="button" data-color="${esc(c.key)}" aria-pressed="false"><span class="swatch color-${esc(c.key)}"></span><span>${esc(c.name)}</span></button>`
        ).join("")}</div>
        <form id="answer-form" autocomplete="off"><button class="btn primary wide" type="submit" id="answer-btn">Answer</button></form>
        ${feedback}
      </div>`;
    }
    if (type === "pattern" && payload.target) {
      const size = Number(payload.size) || 3;
      return `<div class="question-box" id="answer-area">
        <div class="paint-row">
          <div class="paint-section"><span class="paint-label">Target</span><div class="paint-grid target" style="grid-template-columns:repeat(${size},1fr)">${patternGridHtml(size, payload.target, false)}</div></div>
          <div class="paint-section"><span class="paint-label">Your pattern</span><div class="paint-grid" id="paint-grid" style="grid-template-columns:repeat(${size},1fr)">${patternGridHtml(size, [], true)}</div></div>
        </div>
        <form id="answer-form" autocomplete="off"><button class="btn primary wide" type="submit" id="answer-btn">Answer</button></form>
        ${feedback}
      </div>`;
    }
    if (type === "hold") {
      const seconds = Number(payload.seconds) || 5;
      return `<div class="question-box" id="answer-area">
        <div class="hold-wrap">
          <div class="hold-ring" id="hold-ring"><span id="hold-count">${seconds}</span></div>
          <button class="btn primary wide" type="button" id="hold-btn" data-hold-seconds="${seconds}">Press and hold</button>
          <p class="muted small">Keep holding until the ring completes.</p>
        </div>
        <form id="answer-form" autocomplete="off">
          <input id="answer" type="hidden" value="">
          <button class="btn primary" type="submit" id="answer-btn" hidden>Answer</button>
        </form>
        ${feedback}
      </div>`;
    }
    if (type === "typing") {
      const phrase = payload.phrase || data.question || "";
      return `<div class="question-box" id="answer-area">
        <div class="typing-phrase" id="typing-phrase" data-i18n-skip>${esc(phrase)}</div>
        <p class="muted small">Copy and paste are disabled for this challenge.</p>
        <form class="answer-form" id="answer-form" autocomplete="off">
          <input id="answer" type="text" autocomplete="off" autocapitalize="off" spellcheck="false" enterkeyhint="done" aria-label="Type the phrase" placeholder="Type the phrase exactly" data-i18n-skip required>
          <button class="btn primary" type="submit" id="answer-btn">Answer</button>
        </form>
        ${feedback}
      </div>`;
    }
    if (type === "dice") {
      const target = Number(payload.target) || 1;
      const maxTries = Number(payload.max_tries) || 5;
      const tries = Math.min(maxTries, (attempts || 0) + 1);
      return `<div class="question-box" id="answer-area">
        <div class="dice-wrap">
          <div class="dice-target">Target: <strong>${target}</strong></div>
          <div class="dice-face" id="dice-face">🎲</div>
          <p class="muted small">Try ${tries} of ${maxTries} — the fifth try is guaranteed.</p>
          <button class="btn primary wide" type="button" id="dice-roll">Roll the die</button>
        </div>
        <form id="answer-form" autocomplete="off">
          <input id="answer" type="hidden" value="">
          <button class="btn primary" type="submit" id="answer-btn" hidden>Answer</button>
        </form>
        ${feedback}
      </div>`;
    }
    const isText = type === "text";
    const inputAttrs = isText
      ? 'type="text" autocomplete="off" enterkeyhint="done" aria-label="Your answer" placeholder="Your answer"'
      : 'type="text" inputmode="numeric" pattern="-?[0-9]*" autocomplete="off" enterkeyhint="done" aria-label="Your answer" placeholder="?"';
    return `<div class="question-box" id="answer-area">
      <form class="answer-form" id="answer-form" autocomplete="off">
        <input id="answer" ${inputAttrs} required>
        <button class="btn primary" type="submit" id="answer-btn">Answer</button>
      </form>
      ${feedback}
    </div>`;
  }

  function render() {
    const data = S.data;
    if (!data) return;

    if (data.state !== "ringing") {
      stopPolling();
      const done = data.state === "completed";
      $("#content").innerHTML = `
        <div class="challenge-result">
          <div class="result-icon${done ? "" : " bad"}">${done ? "✓" : "⌛"}</div>
          <h2>${done ? "Alarm silenced" : "The alarm stopped"}</h2>
          <p>${done
            ? (data.completion_mode === "count"
              ? `The finish target was reached. ${greeting()}, ${esc(data.user_name)}.`
              : `Everyone answered. ${greeting()}, ${esc(data.user_name)}.`)
            : `This alarm was ${esc(stateWord(data.state))}${data.stop_reason ? " — " + esc(data.stop_reason) : ""}.`}</p>
        </div>
        ${participantsHtml(data)}`;
      setHeader(
        data.alarm_label,
        done ? "All clear." : "Too late.",
        done ? "The sound has stopped for everyone." : "You can close this page."
      );
      applyProgressWidths();
      document.title = window.UNZZZ_I18N?.t(done ? "Alarm silenced · unzzz" : "Alarm over · unzzz") || (done ? "Alarm silenced · unzzz" : "Alarm over · unzzz");
      return;
    }

    if (data.answered) {
      const remaining = data.completion_mode === "count"
        ? Math.max(0, data.target_count - data.answered_count)
        : Math.max(0, data.total - data.answered_count);
      const allDone = remaining <= 0;
      $("#content").innerHTML = `
        <div class="challenge-result">
          <div class="result-icon">✓</div>
          <h2>${allDone ? "Alarm silenced" : "That's you done"}</h2>
          <p>${allDone
            ? (data.completion_mode === "count"
              ? `Enough answers were reached. ${greeting()}, ${esc(data.user_name)}.`
              : `Everyone answered. ${greeting()}, ${esc(data.user_name)}.`)
            : (data.completion_mode === "count"
              ? `Waiting for ${remaining} more ${remaining === 1 ? "answer" : "answers"} — it stops after ${data.target_count}.`
              : `Waiting for ${remaining} more ${remaining === 1 ? "person" : "people"}. The alarm keeps ringing until everyone answers.`)}</p>
        </div>
        ${participantsHtml(data)}`;
      setHeader(data.alarm_label, `You're up, ${data.user_name}.`, "This link is now a spectator view of the challenge.");
      applyProgressWidths();
      document.title = window.UNZZZ_I18N?.t(allDone ? "Alarm silenced · unzzz" : "Waiting for others · unzzz") || (allDone ? "Alarm silenced · unzzz" : "Waiting for others · unzzz");
      if (allDone) stopPolling();
      return;
    }

    // Ringing, not answered yet.
    resetSelection();
    S.holdDone = false;
    S.diceRolled = false;
    const question = data.question;
    const finishText = data.required > 1
      ? `Each person must pass ${data.required} challenges.`
      : (data.completion_mode === "count"
        ? `The alarm stops after ${data.target_count} correct ${data.target_count === 1 ? "answer" : "answers"}.`
        : "Everyone selected has to answer.");
    $("#content").innerHTML = `
      <div class="question" id="question"${(data.challenge_type === "text" || data.challenge_type === "choice" || data.challenge_type === "typing") ? " data-i18n-skip" : ""}>${esc(question || "…")}</div>
      ${answerAreaHtml(data)}
      <div id="participants">${participantsHtml(data)}</div>`;
    setHeader(
      data.alarm_label,
      `Wake up, ${data.user_name}.`,
      "Solve the challenge to silence the alarm."
    );
    $("#content").insertAdjacentHTML("beforeend",
      `<p class="muted small">The alarm gives up around ${fmtHM(data.ends_at)}. ${esc(finishText)}</p>`);
    document.title = window.UNZZZ_I18N?.t("Wake up · unzzz") || "Wake up · unzzz";
    applyProgressWidths();
    $("#answer-form").addEventListener("submit", submitAnswer);
    const holdButton = $("#hold-btn");
    if (holdButton) bindHold(holdButton);
    const diceButton = $("#dice-roll");
    if (diceButton) bindDice(diceButton, data);
    const field = $("#answer");
    if (field) setTimeout(() => field.focus(), 40);
  }

  function bindHold(button) {
    const seconds = Number(button.dataset.holdSeconds) || 5;
    let timer = null;
    let remaining = seconds;
    const count = $("#hold-count");
    const ring = $("#hold-ring");
    const stop = (cancelled = true) => {
      if (timer) clearInterval(timer);
      timer = null;
      remaining = seconds;
      if (count) count.textContent = String(seconds);
      if (ring) ring.classList.remove("holding");
      if (cancelled) {
        button.textContent = "Press and hold";
        button.disabled = false;
      }
    };
    const start = (event) => {
      if (event) event.preventDefault();
      if (timer || S.holdDone) return;
      remaining = seconds;
      button.textContent = "Keep holding…";
      if (ring) ring.classList.add("holding");
      timer = setInterval(() => {
        remaining -= 1;
        if (count) count.textContent = String(Math.max(0, remaining));
        if (remaining <= 0) {
          clearInterval(timer);
          timer = null;
          S.holdDone = true;
          button.textContent = "Passed";
          button.disabled = true;
          const form = $("#answer-form");
          if (form) form.requestSubmit();
        }
      }, 1000);
    };
    button.addEventListener("pointerdown", start);
    button.addEventListener("pointerup", () => { if (!S.holdDone) stop(); });
    button.addEventListener("pointerleave", () => { if (!S.holdDone) stop(); });
    button.addEventListener("pointercancel", () => { if (!S.holdDone) stop(); });
    button.addEventListener("contextmenu", (event) => event.preventDefault());
  }

  function bindDice(button, data) {
    button.addEventListener("click", () => {
      if (S.diceRolled) return;
      const payload = data.payload || {};
      const target = Number(payload.target) || 1;
      const maxTries = Number(payload.max_tries) || 5;
      const attempt = Math.min(maxTries, (Number(data.attempts) || 0) + 1);
      const roll = attempt >= maxTries ? target : 1 + Math.floor(Math.random() * 6);
      S.diceRolled = true;
      button.disabled = true;
      const face = $("#dice-face");
      if (face) {
        face.textContent = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"][roll - 1];
        face.classList.add("rolling");
      }
      const input = $("#answer");
      if (input) input.value = String(roll);
      setTimeout(() => {
        const form = $("#answer-form");
        if (form) form.requestSubmit();
      }, 650);
    });
  }

  // Typing-test copy/paste protection. This is intentionally broad inside the
  // answer area so the phrase cannot be copied into the input.
  for (const name of ["copy", "cut", "contextmenu"]) {
    document.addEventListener(name, (event) => {
      if (event.target.closest && event.target.closest("#answer-area")) {
        event.preventDefault();
      }
    });
  }
  document.addEventListener("paste", (event) => {
    if (event.target.closest && event.target.closest("#answer-area")) {
      event.preventDefault();
      const feedback = $("#feedback");
      if (feedback) {
        feedback.textContent = "Paste is disabled for typing tests.";
        feedback.className = "feedback bad";
      }
    }
  });

  document.addEventListener("click", (event) => {
    const choice = event.target.closest("[data-choice]");
    if (choice) {
      S.selection.choice = choice.dataset.choice;
      $$(".choice-option").forEach((el) => {
        const on = el === choice;
        el.classList.toggle("selected", on);
        el.setAttribute("aria-pressed", on ? "true" : "false");
      });
      return;
    }
    const color = event.target.closest("[data-color]");
    if (color) {
      S.selection.color = color.dataset.color;
      $$(".color-option").forEach((el) => {
        const on = el === color;
        el.classList.toggle("selected", on);
        el.setAttribute("aria-pressed", on ? "true" : "false");
      });
      return;
    }
    const cell = event.target.closest("[data-cell]");
    if (cell) {
      const index = Number(cell.dataset.cell);
      if (S.selection.cells.has(index)) {
        S.selection.cells.delete(index);
        cell.classList.remove("on");
      } else {
        S.selection.cells.add(index);
        cell.classList.add("on");
      }
    }
  });

  async function fetchState(initial = false) {
    let res;
    try {
      res = await fetch(`/api/s/${encodeURIComponent(token)}`, {
        headers: { Accept: "application/json" },
        cache: "no-store",
      });
    } catch (_err) {
      if (initial) showError("Cannot reach the alarm server. Check that you are on the same network and reload.");
      return;
    }
    let body = null;
    try { body = await res.json(); } catch (_err) { /* noop */ }
    if (!res.ok || !body?.ok) {
      if (initial) showError(body?.error || "This shortlink is not valid.");
      return;
    }
    const prev = S.data;
    S.data = body.challenge;
    S.offset = body.challenge.server_time - Date.now() / 1000;
    const back = $("#back-link");
    if (back) back.href = body.challenge.alarm_slug ? `/${body.challenge.alarm_slug}` : "/";

    // A background refresh must not wipe a half-typed answer. If the question
    // and state are unchanged, update only the participants block.
    const sameQuestion = prev && prev.state === "ringing" && !prev.answered
      && S.data.state === "ringing" && !S.data.answered
      && prev.question === S.data.question
      && (prev.challenge_type || "") === (S.data.challenge_type || "")
      && JSON.stringify(prev.payload || {}) === JSON.stringify(S.data.payload || {})
      && $("#answer-area");
    if (sameQuestion) {
      const host = $("#participants");
      if (host) {
        host.innerHTML = participantsHtml(S.data);
        applyProgressWidths();
      }
      tick();
      return;
    }

    render();
    tick();
    if (S.data.state === "ringing") startPolling();
    else stopPolling();
  }

  async function submitAnswer(event) {
    event.preventDefault();
    if (S.submitting || !S.data) return;
    const data = S.data;
    const type = data.challenge_type || (data.answer_type === "text" ? "text" : "math");
    const feedback = $("#feedback");
    let value;
    if (type === "choice") {
      value = S.selection.choice;
      if (!value) {
        feedback.textContent = "Choose one option first.";
        feedback.className = "feedback bad";
        return;
      }
    } else if (type === "color") {
      value = S.selection.color;
      if (!value) {
        feedback.textContent = "Tap a colour first.";
        feedback.className = "feedback bad";
        return;
      }
    } else if (type === "pattern") {
      value = Array.from(S.selection.cells).sort((a, b) => a - b);
      if (!value.length) {
        feedback.textContent = "Paint at least one cell first.";
        feedback.className = "feedback bad";
        return;
      }
    } else if (type === "hold") {
      if (!S.holdDone) {
        feedback.textContent = "Hold the button for the full time first.";
        feedback.className = "feedback bad";
        return;
      }
      value = "held";
    } else if (type === "dice") {
      const input = $("#answer");
      value = input.value.trim();
      if (!value) {
        feedback.textContent = "Roll the die first.";
        feedback.className = "feedback bad";
        return;
      }
    } else {
      const input = $("#answer");
      value = input.value.trim();
      const isText = type === "text" || type === "typing";
      if (isText && !value) {
        feedback.textContent = "Enter an answer.";
        feedback.className = "feedback bad";
        input.focus();
        return;
      }
      if (!isText && !/^-?\d{1,9}$/.test(value)) {
        feedback.textContent = "Enter a whole number.";
        feedback.className = "feedback bad";
        input.focus();
        return;
      }
    }
    S.submitting = true;
    const button = $("#answer-btn");
    if (button) {
      button.disabled = true;
      button.textContent = "Checking…";
    }
    try {
      const res = await fetch(`/api/s/${encodeURIComponent(token)}/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json", "X-Unzzz-Csrf": "1" },
        body: JSON.stringify({ answer: value }),
      });
      let body = null;
      try { body = await res.json(); } catch (_err) { /* noop */ }
      if (!res.ok || !body?.ok) {
        feedback.textContent = body?.error || "Could not check the answer. Try again.";
        feedback.className = "feedback bad";
        return;
      }
      S.data = body.answer;
      S.offset = body.answer.server_time - Date.now() / 1000;
      if (body.status === "wrong") {
        resetSelection();
        render();
        const q = $("#question");
        if (q) {
          q.classList.add("shake");
          setTimeout(() => q.classList.remove("shake"), 400);
        }
        const fb = $("#feedback");
        if (fb) {
          fb.textContent = body.message || "Not right. Here is a new question.";
          fb.className = "feedback bad";
        }
        const field = $("#answer");
        if (field) { field.value = ""; field.focus(); }
        return;
      }
      render();
      if (body.status === "correct") {
        if (!body.all_done && S.data.required > 1) {
          const fb = $("#feedback");
          if (fb) {
            fb.textContent = `Correct — ${S.data.solved}/${S.data.required} challenges passed.`;
            fb.className = "feedback ok";
          }
        }
        if (body.all_done) {
          // Nothing else to do; polling stops because state is completed.
          stopPolling();
        } else {
          startPolling();
        }
      }
    } catch (_err) {
      feedback.textContent = "Network error — the answer was not sent. Try again.";
      feedback.className = "feedback bad";
    } finally {
      S.submitting = false;
      const btn = $("#answer-btn");
      if (btn) { btn.disabled = false; btn.textContent = "Answer"; }
    }
  }

  function showError(message) {
    stopPolling();
    setHeader("Shortlink", "Hmm.", message);
    $("#content").innerHTML = `
      <div class="challenge-result">
        <div class="result-icon bad">!</div>
        <h2>This link did not work</h2>
        <p>${esc(message)} Ask the person who set the alarm for a fresh shortlink.</p>
      </div>`;
  }

  function startPolling() {
    if (S.timer) return;
    S.timer = setInterval(() => fetchState(false), 2500);
  }

  function stopPolling() {
    if (S.timer) { clearInterval(S.timer); S.timer = null; }
  }

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) fetchState(false);
  });

  setInterval(tick, 1000);
  tick();
  fetchState(true);
})();
