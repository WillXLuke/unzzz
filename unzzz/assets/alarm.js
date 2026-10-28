/* Public shared shortlink landing page for a challenge alarm. */
(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const slug = decodeURIComponent(location.pathname.split("/").filter(Boolean).pop() || "");
  const S = { data: null, offset: 0, timer: null, claiming: false };

  const esc = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));

  function fmtHM(ts) {
    if (!ts) return "--:--";
    return new Intl.DateTimeFormat(window.UNZZZ_I18N?.locale, {
      timeZone: S.data?.timezone, hour: "2-digit", minute: "2-digit", hourCycle: "h23",
    }).format(new Date(ts * 1000));
  }

  function fmtClock(ts) {
    return new Intl.DateTimeFormat(window.UNZZZ_I18N?.locale, {
      timeZone: S.data?.timezone, hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
    }).format(new Date(ts * 1000));
  }

  function tick() {
    $("#clock").textContent = fmtClock(Date.now() / 1000 + S.offset);
  }

  function setHeader(eyebrow, headline, sub) {
    $("#eyebrow").textContent = eyebrow;
    $("#headline").textContent = headline;
    $("#sub").textContent = sub;
  }

  function stateWord(state) {
    return ({
      completed: "answered and silenced",
      stopped: "stopped by an admin",
      expired: "timed out",
      interrupted: "interrupted by a server restart",
      missed: "missed",
      snoozed: "snoozed",
      ringing: "ringing",
    }[state] || state);
  }

  function eventParticipants(data, event) {
    if (event?.challenges?.length) {
      return event.challenges.map((c) => ({
        id: c.user_id,
        name: c.user_name,
        active: true,
      }));
    }
    return data.participants;
  }

  function participantRows(data, event = data.event) {
    return eventParticipants(data, event).map((p) => {
      const ch = event?.challenges?.find((c) => c.user_id === p.id);
      const answered = Boolean(ch?.answered);
      const canClaim = event && event.state === "ringing" && !answered;
      return `
        <li class="participant${answered ? " done" : ""}">
          <span class="p-check">✓</span>
          <span class="p-name">${esc(p.name)}${p.active ? "" : " (paused)"}</span>
          ${canClaim
            ? `<button class="btn primary tiny" type="button" data-claim="${p.id}" data-name="${esc(p.name)}">I am ${esc(p.name)}</button>`
            : `<span class="p-status">${answered ? "answered" : (event ? "waiting" : "not ringing")}</span>`}
        </li>`;
    }).join("");
  }

  function render() {
    const data = S.data;
    if (!data) return;
    applyProgress();
    const event = data.event;

    if (data.state === "idle") {
      let next = "not scheduled";
      if (data.alarm.next_fire) {
        const i18n = window.UNZZZ_I18N;
        const exact = fmtHM(data.alarm.next_fire);
        next = i18n?.next(data.alarm.next_fire, Date.now() / 1000 + S.offset)
          || data.alarm.next_human;
        if (!next.includes(exact)) next = `${next} (${exact})`;
      }
      const last = data.last_event;
      if (last && ["completed", "stopped", "expired", "interrupted", "missed", "skipped"].includes(last.state)) {
        const done = last.state === "completed";
        $("#content").innerHTML = `
          <div class="challenge-result">
            <div class="result-icon${done ? "" : " bad"}">${done ? "✓" : "⌛"}</div>
            <h2>${done ? "Last alarm silenced" : "The last alarm ended"}</h2>
            <p>${done ? (last.completion_mode === "count" ? "Enough answers were reached." : "Everyone selected answered.") : `It was ${esc(stateWord(last.state))}${last.stop_reason ? " — " + esc(last.stop_reason) : ""}.`}</p>
          </div>
          <ul class="participant-list">${participantRows(data, last)}</ul>
          <p class="muted small">Next ring: ${esc(next)}.</p>`;
        setHeader(data.alarm.label, "Quiet for now.", "This link will work again when the alarm rings.");
        document.title = window.UNZZZ_I18N?.t("Alarm quiet · unzzz") || "Alarm quiet · unzzz";
        return;
      }
      $("#content").innerHTML = `
        <div class="challenge-result">
          <div class="result-icon">☾</div>
          <h2>Not ringing right now</h2>
          <p>Next ring: ${esc(next)}.</p>
        </div>
        <ul class="participant-list">${participantRows(data)}</ul>`;
      setHeader(data.alarm.label, "This alarm is quiet.", data.alarm.enabled ? "Keep this link — it will work when the alarm rings." : "This alarm is disabled.");
      document.title = window.UNZZZ_I18N?.t("Alarm quiet · unzzz") || "Alarm quiet · unzzz";
      return;
    }

    if (event.state === "completed" || event.state === "stopped" || event.state === "expired" || event.state === "interrupted" || event.state === "missed") {
      $("#content").innerHTML = `
        <div class="challenge-result">
          <div class="result-icon${event.state === "completed" ? "" : " bad"}">${event.state === "completed" ? "✓" : "⌛"}</div>
          <h2>${event.state === "completed" ? "Alarm silenced" : "The alarm is over"}</h2>
          <p>It was ${esc(stateWord(event.state))}${event.stop_reason ? " — " + esc(event.stop_reason) : ""}.</p>
        </div>
        <ul class="participant-list">${participantRows(data)}</ul>`;
      setHeader(data.alarm.label, "All clear.", "The sound has stopped.");
      document.title = window.UNZZZ_I18N?.t("Alarm over · unzzz") || "Alarm over · unzzz";
      return;
    }

    if (event.state === "snoozed") {
      $("#content").innerHTML = `
        <div class="challenge-result">
          <div class="result-icon">☾</div>
          <h2>Snoozed</h2>
          <p>This alarm rings again at ${fmtHM(event.snooze_until)}. Open this link then to answer.</p>
        </div>
        <ul class="participant-list">${participantRows(data)}</ul>`;
      setHeader(data.alarm.label, "Give it a minute.", "The alarm is snoozed.");
      document.title = window.UNZZZ_I18N?.t("Alarm snoozed · unzzz") || "Alarm snoozed · unzzz";
      return;
    }

    const target = event.completion_mode === "count"
      ? `${event.target_count} correct ${event.target_count === 1 ? "answer" : "answers"}`
      : "every selected person";
    const answered = event.challenges.filter((c) => c.answered).length;
    $("#content").innerHTML = `
      <div class="row between">
        <span class="muted small">${answered} / ${event.total} answered</span>
        <span class="muted small">${event.completion_mode === "count" ? `target ${event.target_count}` : "all"}</span>
      </div>
      <div class="progress"><span class="progress-fill" data-progress="${event.completion_mode === "count" ? Math.min(100, Math.round((answered / event.target_count) * 100)) : Math.round((answered / event.total) * 100)}"></span></div>
      <p class="challenge-sub">Choose your name. The alarm stops after ${esc(target)}.</p>
      <ul class="participant-list">${participantRows(data)}</ul>`;
    setHeader(data.alarm.label, "Who is up?", "Pick your own name to get your question.");
    document.title = window.UNZZZ_I18N?.t("Wake up · unzzz") || "Wake up · unzzz";
  }

  function applyProgress() {
    document.querySelectorAll("[data-progress]").forEach((el) => {
      el.style.width = `${Number(el.dataset.progress) || 0}%`;
    });
  }

  async function claim(userId, name) {
    if (S.claiming) return;
    S.claiming = true;
    try {
      const res = await fetch(`/api/alarm/${encodeURIComponent(slug)}/claim`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json", "X-Unzzz-Csrf": "1" },
        body: JSON.stringify({ user_id: userId }),
      });
      const body = await res.json().catch(() => null);
      if (!res.ok || !body?.ok) {
        alert(body?.error || "Could not open your question.");
        await refresh();
        return;
      }
      location.href = body.url;
    } catch (_err) {
      alert("Cannot reach the alarm server.");
    } finally {
      S.claiming = false;
    }
  }

  async function refresh() {
    if (S.claiming) return;
    let res;
    try {
      res = await fetch(`/api/alarm/${encodeURIComponent(slug)}`, { cache: "no-store" });
    } catch (_err) {
      setHeader("Alarm shortlink", "Offline.", "Cannot reach the alarm server.");
      return;
    }
    const body = await res.json().catch(() => null);
    if (!res.ok || !body?.ok) {
      setHeader("Alarm shortlink", "Link not found.", body?.error || "Ask the person who set the alarm for a fresh link.");
      $("#content").innerHTML = "";
      return;
    }
    S.data = body;
    S.offset = body.server_time - Date.now() / 1000;
    render();
    tick();
    if (S.timer) clearInterval(S.timer);
    S.timer = setInterval(refresh, 2500);
  }

  document.addEventListener("click", (event) => {
    const btn = event.target.closest("[data-claim]");
    if (btn) claim(Number(btn.dataset.claim), btn.dataset.name);
  });

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) refresh();
  });

  setInterval(tick, 1000);
  tick();
  refresh();
})();
