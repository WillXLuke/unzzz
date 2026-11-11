/* unzzz wake-up challenge — runs on the phone that opens a shortlink. */
(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const token = decodeURIComponent(location.pathname.split("/").filter(Boolean).pop() || "");
  const S = {
    data: null, offset: 0, timer: null, submitting: false,
    gameTimers: [],
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

  function stopChallengeTimers() {
    for (const id of S.gameTimers) clearInterval(id);
    S.gameTimers = [];
  }

  function gameInterval(fn, ms) {
    const id = setInterval(fn, ms);
    S.gameTimers.push(id);
    return id;
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
          <div class="paint-section"><span class="paint-label">Target</span><div class="paint-grid target paint-size-${size}">${patternGridHtml(size, payload.target, false)}</div></div>
          <div class="paint-section"><span class="paint-label">Your pattern</span><div class="paint-grid paint-size-${size}" id="paint-grid">${patternGridHtml(size, [], true)}</div></div>
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
          <div class="dice-face" id="dice-face" aria-label="Dice result"><span class="dice-number" id="dice-number">?</span></div>
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
    if (type === "snake") {
      return `<div class="question-box" id="answer-area">
        <div class="game-hud"><span>Apples <strong id="snake-score">0</strong> / 10</span><span class="muted small">Eat 10 apples.</span></div>
        <canvas id="snake-canvas" width="288" height="288" class="snake-canvas" aria-label="Snake game"></canvas>
        <p class="muted small" id="snake-status">Swipe the board, or use arrow keys / WASD.</p>
        <form id="answer-form" autocomplete="off"><input id="answer" type="hidden" value=""><button class="btn primary" type="submit" id="answer-btn" hidden>Answer</button></form>
        ${feedback}
      </div>`;
    }
    if (type === "whac") {
      return `<div class="question-box" id="answer-area">
        <div class="game-hud"><span>Moles <strong id="whac-score">0</strong> / 10</span><span class="muted small">Tap the mole.</span></div>
        <div class="whac-grid" id="whac-grid">${Array.from({ length: 9 }, (_, i) => `<button class="whac-hole" type="button" data-whac="${i}" aria-label="Hole ${i + 1}"></button>`).join("")}</div>
        <p class="muted small" id="whac-status">Hit 10 moles.</p>
        <form id="answer-form" autocomplete="off"><input id="answer" type="hidden" value=""><button class="btn primary" type="submit" id="answer-btn" hidden>Answer</button></form>
        ${feedback}
      </div>`;
    }
    if (type === "dino") {
      return `<div class="question-box" id="answer-area">
        <div class="game-hud"><span>Jumped <strong id="dino-score">0</strong> / 15</span><span class="muted small">Tap or press Space to jump.</span></div>
        <canvas id="dino-canvas" width="480" height="170" class="dino-canvas" aria-label="Dino run game"></canvas>
        <div class="row"><button class="btn primary" type="button" id="dino-jump">Jump</button></div>
        <p class="muted small" id="dino-status">Jump over 15 obstacles.</p>
        <form id="answer-form" autocomplete="off"><input id="answer" type="hidden" value=""><button class="btn primary" type="submit" id="answer-btn" hidden>Answer</button></form>
        ${feedback}
      </div>`;
    }
    if (type === "piano") {
      return `<div class="question-box" id="answer-area">
        <div class="game-hud"><span>Tiles <strong id="piano-score">0</strong></span><span class="muted small" id="piano-clock">Tap a black tile to start · 30s</span></div>
        <div class="piano-grid" id="piano-grid"></div>
        <p class="muted small" id="piano-status">Do not touch the white tiles.</p>
        <form id="answer-form" autocomplete="off"><input id="answer" type="hidden" value=""><button class="btn primary" type="submit" id="answer-btn" hidden>Answer</button></form>
        ${feedback}
      </div>`;
    }
    if (type === "game2048") {
      return `<div class="question-box" id="answer-area">
        <div class="g2048-wrap">
          <div class="g2048-head">
            <span>Score <strong id="g2048-score">0</strong></span>
            <span class="muted small">Target: 128</span>
          </div>
          <div class="g2048-board" id="game2048-board" role="grid" aria-label="2048 board"></div>
          <div class="row between">
            <span class="muted small" id="g2048-status">Use arrow keys or swipe.</span>
            <button class="btn ghost tiny" type="button" id="g2048-restart">Restart</button>
          </div>
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
    document.body.classList.toggle("hold-active", data.challenge_type === "hold");
    S.holdDone = false;
    S.game2048 = null;
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
    const gameBoard = $("#game2048-board");
    if (gameBoard) bind2048(gameBoard);
    if ($("#snake-canvas")) bindSnake(data);
    if ($("#whac-grid")) bindWhac(data);
    if ($("#dino-canvas")) bindDino(data);
    if ($("#piano-grid")) bindPiano(data);
    const field = $("#answer");
    if (field) setTimeout(() => field.focus(), 40);
  }

  function bindHold(button) {
    const seconds = Number(button.dataset.holdSeconds) || 5;
    let timer = null;
    let pointerId = null;
    let remaining = seconds;
    const count = $("#hold-count");
    const ring = $("#hold-ring");
    const stop = (cancelled = true) => {
      if (timer) clearInterval(timer);
      timer = null;
      pointerId = null;
      remaining = seconds;
      if (count) count.textContent = String(seconds);
      if (ring) ring.classList.remove("holding");
      if (cancelled && !S.holdDone) {
        button.textContent = "Press and hold";
        button.disabled = false;
      }
    };
    const start = (event) => {
      if (event) event.preventDefault();
      if (timer || S.holdDone) return;
      if (event && event.pointerType === "mouse" && event.button !== 0) return;
      pointerId = event?.pointerId ?? null;
      if (pointerId != null) {
        try { button.setPointerCapture(pointerId); } catch (_err) { /* noop */ }
      }
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
    button.addEventListener("pointercancel", () => { if (!S.holdDone) stop(); });
    button.addEventListener("lostpointercapture", () => { if (!S.holdDone) stop(); });
    button.addEventListener("pointerleave", (event) => {
      // Touch pointers are captured; leaving the element while still holding
      // should not cancel. Mouse users get a leave-to-cancel affordance.
      if (event.pointerType === "mouse" && !S.holdDone) stop();
    });
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
      const number = $("#dice-number");
      if (number) number.textContent = String(roll);
      if (face) {
        face.classList.remove("rolling");
        void face.offsetWidth;
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
  function finishGame(value, statusEl, message) {
    stopChallengeTimers();
    const input = $("#answer");
    if (input) input.value = String(value);
    if (statusEl) statusEl.textContent = message;
    setTimeout(() => $("#answer-form")?.requestSubmit(), 350);
  }

  function bindSnake(data) {
    const canvas = $("#snake-canvas");
    const ctx = canvas?.getContext("2d");
    if (!ctx) return;
    const cells = 16, cell = 288 / cells, target = 10;
    const game = {
      snake: [{ x: 8, y: 8 }], dir: { x: 1, y: 0 }, next: { x: 1, y: 0 },
      apple: { x: 12, y: 8 }, score: 0, over: false,
    };
    S.snakeGame = game;
    const scoreEl = $("#snake-score");
    const statusEl = $("#snake-status");
    const placeApple = () => {
      do {
        game.apple = {
          x: Math.floor(Math.random() * cells),
          y: Math.floor(Math.random() * cells),
        };
      } while (game.snake.some((part) => part.x === game.apple.x && part.y === game.apple.y));
    };
    const reset = () => {
      game.snake = [{ x: 8, y: 8 }];
      game.dir = { x: 1, y: 0 };
      game.next = { x: 1, y: 0 };
      game.score = 0;
      game.over = false;
      placeApple();
      if (scoreEl) scoreEl.textContent = "0";
      if (statusEl) statusEl.textContent = "Crashed — start again.";
    };
    const draw = () => {
      ctx.fillStyle = "#0b100c";
      ctx.fillRect(0, 0, 288, 288);
      ctx.strokeStyle = "#1c2a20";
      for (let i = 1; i < cells; i++) {
        ctx.beginPath(); ctx.moveTo(i * cell, 0); ctx.lineTo(i * cell, 288); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(0, i * cell); ctx.lineTo(288, i * cell); ctx.stroke();
      }
      ctx.fillStyle = "#ff5c5c";
      ctx.fillRect(game.apple.x * cell + 2, game.apple.y * cell + 2, cell - 4, cell - 4);
      ctx.fillStyle = "#67e8f9";
      game.snake.forEach((part) => ctx.fillRect(part.x * cell + 2, part.y * cell + 2, cell - 4, cell - 4));
    };
    const step = () => {
      if (game.over) return;
      if (game.next.x !== -game.dir.x || game.next.y !== -game.dir.y) game.dir = game.next;
      const head = {
        x: (game.snake[0].x + game.dir.x + cells) % cells,
        y: (game.snake[0].y + game.dir.y + cells) % cells,
      };
      if (game.snake.some((part) => part.x === head.x && part.y === head.y)) {
        game.over = true;
        reset();
        draw();
        return;
      }
      game.snake.unshift(head);
      if (head.x === game.apple.x && head.y === game.apple.y) {
        game.score += 1;
        if (scoreEl) scoreEl.textContent = String(game.score);
        if (game.score >= target) {
          game.over = true;
          finishGame("10", statusEl, "10 apples — checking…");
          return;
        }
        placeApple();
      } else {
        game.snake.pop();
      }
      draw();
    };
    const turn = (direction) => {
      const map = {
        up: { x: 0, y: -1 }, down: { x: 0, y: 1 },
        left: { x: -1, y: 0 }, right: { x: 1, y: 0 },
      };
      const next = map[direction];
      if (next) game.next = next;
    };
    let startPoint = null;
    canvas.addEventListener("pointerdown", (event) => {
      startPoint = { x: event.clientX, y: event.clientY };
      try { canvas.setPointerCapture(event.pointerId); } catch (_err) { /* noop */ }
    });
    canvas.addEventListener("pointerup", (event) => {
      if (!startPoint) return;
      const dx = event.clientX - startPoint.x;
      const dy = event.clientY - startPoint.y;
      startPoint = null;
      if (Math.max(Math.abs(dx), Math.abs(dy)) < 18) return;
      turn(Math.abs(dx) > Math.abs(dy)
        ? (dx > 0 ? "right" : "left")
        : (dy > 0 ? "down" : "up"));
    });
    canvas.addEventListener("pointercancel", () => { startPoint = null; });
    canvas.addEventListener("contextmenu", (event) => event.preventDefault());
    document.addEventListener("keydown", (event) => {
      if (S.snakeGame !== game) return;
      const map = {
        ArrowUp: "up", ArrowDown: "down", ArrowLeft: "left", ArrowRight: "right",
        w: "up", s: "down", a: "left", d: "right",
      };
      const direction = map[event.key];
      if (!direction) return;
      event.preventDefault();
      turn(direction);
    });
    placeApple();
    draw();
    gameInterval(step, 220);
  }

  function bindWhac(data) {
    const grid = $("#whac-grid");
    if (!grid) return;
    const holes = $$("[data-whac]", grid);
    const scoreEl = $("#whac-score");
    const statusEl = $("#whac-status");
    const target = 10;
    let score = 0;
    let active = -1;
    const move = () => {
      holes.forEach((hole) => hole.classList.remove("mole"));
      active = Math.floor(Math.random() * holes.length);
      holes[active].classList.add("mole");
    };
    holes.forEach((hole, index) => {
      hole.addEventListener("click", () => {
        if (index !== active) return;
        score += 1;
        if (scoreEl) scoreEl.textContent = String(score);
        if (score >= target) {
          finishGame("10", statusEl, "10 moles — checking…");
          return;
        }
        move();
      });
    });
    move();
    gameInterval(move, 700);
  }

  function bindDino(data) {
    const canvas = $("#dino-canvas");
    const ctx = canvas?.getContext("2d");
    if (!ctx) return;
    const target = 15;
    const ground = 140;
    const game = {
      dino: { x: 54, y: ground - 38, w: 28, h: 38, vy: 0, jumping: false },
      obstacle: { x: 480, y: ground - 34, w: 22, h: 34 },
      score: 0, over: false, speed: 3.4,
    };
    const scoreEl = $("#dino-score");
    const statusEl = $("#dino-status");
    const jump = () => {
      if (S.dinoGame !== game || game.over) return;
      if (!game.dino.jumping) {
        game.dino.jumping = true;
        game.dino.vy = -11.5;
      }
    };
    const draw = () => {
      ctx.fillStyle = "#0b100c"; ctx.fillRect(0, 0, 480, 170);
      ctx.fillStyle = "#1c2a20"; ctx.fillRect(0, ground, 480, 2);
      ctx.fillStyle = "#67e8f9";
      ctx.fillRect(game.dino.x, game.dino.y, game.dino.w, game.dino.h);
      ctx.fillStyle = "#ff9f43";
      ctx.fillRect(game.obstacle.x, game.obstacle.y, game.obstacle.w, game.obstacle.h);
    };
    const step = () => {
      if (game.over) return;
      game.dino.vy += 0.7;
      game.dino.y += game.dino.vy;
      if (game.dino.y >= ground - game.dino.h) {
        game.dino.y = ground - game.dino.h;
        game.dino.vy = 0;
        game.dino.jumping = false;
      }
      game.obstacle.x -= game.speed;
      const hit = game.obstacle.x < game.dino.x + game.dino.w
        && game.obstacle.x + game.obstacle.w > game.dino.x
        && game.obstacle.y < game.dino.y + game.dino.h
        && game.obstacle.y + game.obstacle.h > game.dino.y;
      if (hit) {
        game.score = 0;
        game.speed = 3.4;
        game.obstacle.x = 480;
        if (scoreEl) scoreEl.textContent = "0";
        if (statusEl) statusEl.textContent = "Crashed — try again.";
      }
      if (game.obstacle.x + game.obstacle.w < game.dino.x) {
        game.score += 1;
        game.speed = Math.min(6.5, game.speed + 0.08);
        if (scoreEl) scoreEl.textContent = String(game.score);
        if (game.score >= target) {
          game.over = true;
          finishGame("15", statusEl, "15 obstacles — checking…");
          return;
        }
        game.obstacle.x = 480;
      }
      draw();
    };
    S.dinoGame = game;
    $("#dino-jump")?.addEventListener("click", jump);
    canvas.addEventListener("pointerdown", (event) => { event.preventDefault(); jump(); });
    document.addEventListener("keydown", (event) => {
      if (S.dinoGame !== game) return;
      if (event.key === " " || event.key === "ArrowUp") {
        event.preventDefault();
        jump();
      }
    });
    draw();
    gameInterval(step, 30);
  }

  function bindPiano(data) {
    const grid = $("#piano-grid");
    if (!grid) return;
    const target = 30;
    const rows = 4, cols = 4;
    let black = Array.from({ length: rows }, () => Math.floor(Math.random() * cols));
    let started = false;
    let left = target;
    let score = 0;
    const clock = $("#piano-clock");
    const scoreEl = $("#piano-score");
    const statusEl = $("#piano-status");
    const render = () => {
      grid.innerHTML = Array.from({ length: rows }, (_, row) =>
        Array.from({ length: cols }, (_, col) =>
          `<button class="piano-cell ${black[row] === col ? "black" : "white"}" type="button" data-piano-row="${row}" data-piano-col="${col}" aria-label="${black[row] === col ? "Black" : "White"} tile"></button>`
        ).join("")
      ).join("");
      $$("[data-piano-row]", grid).forEach((cell) => {
        cell.addEventListener("click", () => {
          const row = Number(cell.dataset.pianoRow);
          const col = Number(cell.dataset.pianoCol);
          if (black[row] !== col) {
            left = target;
            started = false;
            score = 0;
            if (clock) clock.textContent = "Tap a black tile to start · 30s";
            if (scoreEl) scoreEl.textContent = "0";
            if (statusEl) statusEl.textContent = "White tile! Start again.";
            return;
          }
          if (!started) {
            started = true;
            left = target;
            if (statusEl) statusEl.textContent = "Do not touch the white tiles.";
          }
          score += 1;
          if (scoreEl) scoreEl.textContent = String(score);
        });
      });
    };
    const shift = () => {
      black = [Math.floor(Math.random() * cols), ...black.slice(0, rows - 1)];
      render();
    };
    render();
    gameInterval(shift, 700);
    gameInterval(() => {
      if (!started) return;
      left -= 0.1;
      if (clock) clock.textContent = `${Math.max(0, left).toFixed(1)}s`;
      if (left <= 0) {
        finishGame("30", statusEl, "30 seconds — checking…");
      }
    }, 100);
  }

  function bind2048(boardEl) {
    const target = 128;
    const spawn = () => {
      const game = S.game2048;
      if (!game) return false;
      const empty = game.board
        .map((value, index) => value === 0 ? index : -1)
        .filter((index) => index >= 0);
      if (!empty.length) return false;
      game.board[empty[Math.floor(Math.random() * empty.length)]] =
        Math.random() < 0.9 ? 2 : 4;
      return true;
    };
    const hasMoves = () => {
      const board = S.game2048.board;
      if (board.some((value) => value === 0)) return true;
      for (let row = 0; row < 4; row++) {
        for (let col = 0; col < 4; col++) {
          const index = row * 4 + col;
          if (col < 3 && board[index] === board[index + 1]) return true;
          if (row < 3 && board[index] === board[index + 4]) return true;
        }
      }
      return false;
    };
    const render = () => {
      const game = S.game2048;
      boardEl.innerHTML = game.board.map((value) => {
        const shown = value ? String(value) : "";
        return `<div class="g2048-cell tile-${value || 0}" role="gridcell">${shown}</div>`;
      }).join("");
      const score = $("#g2048-score");
      if (score) score.textContent = String(game.score);
      const status = $("#g2048-status");
      if (status) {
        status.textContent = game.won
          ? "128 reached — checking…"
          : game.over ? "No moves left — restart." : "Use arrow keys or swipe.";
      }
    };
    const start = () => {
      S.game2048 = {
        board: Array(16).fill(0), score: 0, won: false, over: false, move,
      };
      spawn();
      spawn();
      render();
    };
    const slide = (line) => {
      const values = line.filter((value) => value);
      const out = [];
      let gained = 0;
      for (let i = 0; i < values.length; i++) {
        if (i + 1 < values.length && values[i] === values[i + 1]) {
          const merged = values[i] * 2;
          out.push(merged);
          gained += merged;
          i += 1;
        } else {
          out.push(values[i]);
        }
      }
      while (out.length < 4) out.push(0);
      return { out, gained };
    };
    const move = (direction) => {
      const game = S.game2048;
      if (!game || game.won || game.over) return;
      const before = game.board.join(",");
      let gained = 0;
      for (let index = 0; index < 4; index++) {
        let positions;
        if (direction === "left") positions = [0, 1, 2, 3].map((c) => index * 4 + c);
        else if (direction === "right") positions = [3, 2, 1, 0].map((c) => index * 4 + c);
        else if (direction === "up") positions = [0, 1, 2, 3].map((r) => r * 4 + index);
        else positions = [3, 2, 1, 0].map((r) => r * 4 + index);
        const result = slide(positions.map((pos) => game.board[pos]));
        gained += result.gained;
        positions.forEach((pos, offset) => { game.board[pos] = result.out[offset]; });
      }
      if (game.board.join(",") === before) return;
      game.score += gained;
      spawn();
      if (game.board.some((value) => value >= target)) {
        game.won = true;
        render();
        const input = $("#answer");
        if (input) input.value = "128";
        setTimeout(() => $("#answer-form")?.requestSubmit(), 450);
        return;
      }
      if (!hasMoves()) game.over = true;
      render();
    };
    start();
    const restart = $("#g2048-restart");
    if (restart) restart.addEventListener("click", start);
    let startPoint = null;
    boardEl.addEventListener("pointerdown", (event) => {
      startPoint = { x: event.clientX, y: event.clientY };
      try { boardEl.setPointerCapture(event.pointerId); } catch (_err) { /* noop */ }
    });
    boardEl.addEventListener("pointerup", (event) => {
      if (!startPoint) return;
      const dx = event.clientX - startPoint.x;
      const dy = event.clientY - startPoint.y;
      startPoint = null;
      if (Math.max(Math.abs(dx), Math.abs(dy)) < 24) return;
      move(Math.abs(dx) > Math.abs(dy)
        ? (dx > 0 ? "right" : "left")
        : (dy > 0 ? "down" : "up"));
    });
    boardEl.addEventListener("pointercancel", () => { startPoint = null; });
    boardEl.addEventListener("contextmenu", (event) => event.preventDefault());
  }

  document.addEventListener("keydown", (event) => {
    const game = S.game2048;
    if (!game || !S.data || S.data.challenge_type !== "game2048" || S.data.answered) return;
    const map = {
      ArrowLeft: "left", ArrowRight: "right", ArrowUp: "up", ArrowDown: "down",
      a: "left", d: "right", w: "up", s: "down",
    };
    const direction = map[event.key];
    if (!direction) return;
    event.preventDefault();
    game.move(direction);
  });

  const holdActive = () => document.body.classList.contains("hold-active");
  for (const name of ["copy", "cut", "contextmenu", "selectstart"]) {
    document.addEventListener(name, (event) => {
      const inAnswer = event.target.closest && event.target.closest("#answer-area");
      if (holdActive() || inAnswer) {
        event.preventDefault();
      }
    });
  }
  document.addEventListener("paste", (event) => {
    const inAnswer = event.target.closest && event.target.closest("#answer-area");
    if (holdActive() || inAnswer) {
      event.preventDefault();
      const feedback = $("#feedback");
      if (feedback) {
        feedback.textContent = holdActive()
          ? "Copy and paste are disabled for this challenge."
          : "Paste is disabled for typing tests.";
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
    } else if (type === "game2048") {
      const input = $("#answer");
      value = input.value.trim();
      if (value !== "128") {
        feedback.textContent = "Reach the 128 tile first.";
        feedback.className = "feedback bad";
        return;
      }
    } else if (["snake", "whac", "dino", "piano"].includes(type)) {
      const input = $("#answer");
      value = input.value.trim();
      if (!value) {
        feedback.textContent = "Finish the game first.";
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
