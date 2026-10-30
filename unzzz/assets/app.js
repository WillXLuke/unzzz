/* unzzz control panel — vanilla JS, no build step. */
(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const esc = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));

  const S = {
    data: null,
    offset: 0,
    view: localStorage.getItem("unzzz-view") || "alarms",
    busy: false,
    pollTimer: null,
    clockTimer: null,
    sig: {},
    editor: null,
    bound: false,
    settingsLoaded: false,
    devicesLoaded: false,
    deviceDirty: false,
    questionEditId: null,
    prevActive: null,
    toastTimer: null,
  };

  class ApiError extends Error {
    constructor(message, status, data) {
      super(message);
      this.status = status;
      this.data = data;
    }
  }

  // ------------------------------------------------------------------ api
  async function api(path, opts = {}) {
    const method = opts.method || "GET";
    const headers = { Accept: "application/json", ...(opts.headers || {}) };
    const init = { method, credentials: "same-origin", headers };
    if (opts.body !== undefined) {
      headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(opts.body);
    }
    if (method !== "GET") headers["X-Unzzz-Csrf"] = "1";
    let res;
    try {
      res = await fetch(path, init);
    } catch (_err) {
      throw new ApiError("Cannot reach the server", 0, null);
    }
    let data = null;
    try { data = await res.json(); } catch (_err) { /* empty body */ }
    if (res.status === 401 && !path.startsWith("/api/login") && !path.startsWith("/api/setup")) {
      showAuth("login");
      throw new ApiError(data?.error || "Please sign in", 401, data);
    }
    if (!res.ok || (data && data.ok === false)) {
      throw new ApiError(data?.error || `Request failed (${res.status})`, res.status, data);
    }
    return data;
  }

  // -------------------------------------------------------------- helpers
  const I18N = () => window.UNZZZ_I18N;
  const LOCALE = () => I18N()?.locale || undefined;

  function tz() { return S.data?.timezone || "UTC"; }

  function fmtHM(ts) {
    if (!ts) return "--:--";
    return new Intl.DateTimeFormat(LOCALE(), {
      timeZone: tz(), hour: "2-digit", minute: "2-digit", hourCycle: "h23",
    }).format(new Date(ts * 1000));
  }

  function fmtClock(ts, withSeconds = false) {
    return new Intl.DateTimeFormat(LOCALE(), {
      timeZone: tz(), hour: "2-digit", minute: "2-digit", hourCycle: "h23",
      ...(withSeconds ? { second: "2-digit" } : {}),
    }).format(new Date(ts * 1000));
  }

  function fmtDate(ts) {
    return new Intl.DateTimeFormat(LOCALE(), {
      timeZone: tz(), weekday: "short", day: "2-digit", month: "short",
    }).format(new Date(ts * 1000));
  }

  function fmtDateTime(ts) {
    return new Intl.DateTimeFormat(LOCALE(), {
      timeZone: tz(), weekday: "short", day: "2-digit", month: "short",
      hour: "2-digit", minute: "2-digit", hourCycle: "h23",
    }).format(new Date(ts * 1000));
  }

  function serverNow() { return Date.now() / 1000 + S.offset; }

  function durationText(seconds) {
    seconds = Math.max(0, Math.floor(seconds));
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `${h}h ${String(m).padStart(2, "0")}m`;
    if (m > 0) return `${m}m ${String(s).padStart(2, "0")}s`;
    return `${s}s`;
  }

  function countdownText(target) {
    return I18N()?.countdown(target - serverNow()) || "any moment now";
  }

  function toast(message, kind = "ok") {
    const el = $("#toast");
    el.textContent = message;
    el.className = `toast show${kind === "error" ? " error" : ""}`;
    el.hidden = false;
    clearTimeout(S.toastTimer);
    S.toastTimer = setTimeout(() => {
      el.classList.remove("show");
      el.hidden = true;
    }, 3600);
  }

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      toast("Shortlink copied");
    } catch (_err) {
      // Clipboard API needs a secure context; plain HTTP on the LAN does not have one.
      window.prompt("Copy this shortlink:", text);
    }
  }

  function confirmAction({ title, text, confirmLabel = "Confirm", danger = true }) {
    const dialog = $("#confirm-dialog");
    if (dialog.open) return Promise.resolve(false);
    $("#confirm-title").textContent = title;
    $("#confirm-text").textContent = text;
    const ok = $("#confirm-ok");
    ok.textContent = confirmLabel;
    ok.className = `btn ${danger ? "danger" : "primary"}`;
    return new Promise((resolve) => {
      const onClose = () => {
        dialog.removeEventListener("close", onClose);
        resolve(dialog.returnValue === "confirm");
      };
      dialog.addEventListener("close", onClose);
      dialog.returnValue = "cancel";
      if (typeof dialog.showModal === "function") dialog.showModal();
      else { resolve(false); }
    });
  }

  function setView(view) {
    const views = ["alarms", "users", "challenges", "links", "music", "special", "history", "settings"];
    if (!views.includes(view)) view = "alarms";
    S.view = view;
    localStorage.setItem("unzzz-view", view);
    $$(".tab").forEach((tab) => {
      const active = tab.dataset.view === view;
      tab.classList.toggle("active", active);
      if (active) tab.scrollIntoView({ block: "nearest", inline: "center" });
    });
    $$(".view").forEach((section) => { section.hidden = section.id !== `view-${view}`; });
    if (view === "history" && S.data && !S.sig.history) renderHistory(S.data);
    if (view === "settings" && S.data) loadAudioDevices();
  }

  // ---------------------------------------------------------------- screens
  function showAuth(mode) {
    stopTimers();
    S.data = null;
    S.sig = {};
    S.settingsLoaded = false;
    S.devicesLoaded = false;
    S.deviceDirty = false;
    S.questionEditId = null;
    S.prevActive = null;
    $("#app").hidden = true;
    $("#screen-loading").hidden = true;
    $("#screen-auth").hidden = false;
    $("#login-form").hidden = mode !== "login";
    $("#setup-form").hidden = mode !== "setup";
    $("#auth-version").textContent = "2.3.2";
    $("#login-error").textContent = "";
    $("#setup-error").textContent = "";
    setTimeout(() => {
      const input = mode === "login" ? $("#login-password") : $("#setup-password");
      if (input) input.focus();
    }, 30);
  }

  function showApp(data) {
    S.data = data;
    S.offset = data.server_time - Date.now() / 1000;
    $("#screen-loading").hidden = true;
    $("#screen-auth").hidden = true;
    $("#app").hidden = false;
    $("#version").textContent = data.version;
    $("#tz-label").textContent = data.timezone;
    if (!S.bound) { bindUI(); S.bound = true; }
    setView(S.view);
    applyState(data);
    startTimers();
  }

  function startTimers() {
    if (!S.pollTimer) S.pollTimer = setInterval(refresh, 2500);
    if (!S.clockTimer) S.clockTimer = setInterval(tickClock, 1000);
    tickClock();
  }

  function stopTimers() {
    if (S.pollTimer) { clearInterval(S.pollTimer); S.pollTimer = null; }
    if (S.clockTimer) { clearInterval(S.clockTimer); S.clockTimer = null; }
  }

  async function boot() {
    let res;
    try {
      res = await fetch("/api/state", { credentials: "same-origin" });
    } catch (_err) {
      showAuth("login");
      $("#login-error").textContent = "Cannot reach the server.";
      return;
    }
    let data = null;
    try { data = await res.json(); } catch (_err) { /* noop */ }
    if (data && data.needs_setup) { showAuth("setup"); return; }
    if (res.status === 401 || !data || !data.ok) {
      showAuth("login");
      return;
    }
    showApp(data);
  }

  async function refresh() {
    if (S.busy || !S.data) return;
    S.busy = true;
    try {
      const data = await api("/api/state");
      applyState(data);
    } catch (err) {
      if (err.status !== 401 && err.status !== 0) console.warn("refresh failed:", err.message);
      if (err.status === 401) showAuth("login");
    } finally {
      S.busy = false;
    }
  }

  // ------------------------------------------------------------------ state
  function applyState(data) {
    const previous = S.data;
    S.data = data;
    S.offset = data.server_time - Date.now() / 1000;
    $("#tz-label").textContent = data.timezone;
    $("#version").textContent = data.version;
    $("#tab-alarm-count").textContent = String(data.alarms.length);
    const activeUsers = data.users.filter((u) => u.active).length;
    $("#tab-user-count").textContent = `${activeUsers}/${data.users.length}`;

    const activeIds = new Set(data.active_events.map((e) => e.id));
    if (previous && S.prevActive !== null) {
      const had = S.prevActive;
      const still = [...had].some((id) => activeIds.has(id));
      if (had.size > 0 && !still) toast("Alarm silenced. Nice work.");
    }
    S.prevActive = activeIds;

    renderAudioWarning();
    renderAlarms(data);
    renderUsers(data);
    renderQuestions(data);
    renderLinks(data);
    renderMusic(data);
    renderCalendars(data);
    renderHistory(data);
    renderSettings(data);
    renderRingDock(data);
    tickClock();
  }

  function sigOf(obj) { return JSON.stringify(obj); }

  // ---------------------------------------------------------------- alarms
  function baseUrl() {
    return S.data?.settings?.effective_base_url || location.origin;
  }

  function alarmParticipants(alarm) {
    return alarm?.participants || [];
  }

  const CHALLENGE_TYPE_LABEL = {
    math: "Maths",
    text: "Text",
    choice: "Choice",
    random_choice: "Random choice",
    color: "Colour",
    pattern: "Pattern",
  };

  const PLAN_OPTIONS = [
    ["math", "Generated maths"],
    ["text", "Text question"],
    ["choice", "Multiple choice"],
    ["random_choice", "Random multiple choice"],
    ["color", "Colour match"],
    ["pattern3", "Pattern paint 3×3"],
    ["pattern6", "Pattern paint 6×6"],
    ["pattern9", "Pattern paint 9×9"],
    ["hold", "Button hold"],
    ["typing", "Typing test"],
    ["dice", "Roll dice"],
  ];

  function planValueToDescriptor(value) {
    const match = /^pattern([369])$/.exec(value || "");
    if (match) return { type: "pattern", size: Number(match[1]) };
    return { type: value || "math" };
  }

  function descriptorToValue(item) {
    if (!item) return "math";
    if (item.type === "pattern") return `pattern${item.size || 3}`;
    return item.type || "math";
  }

  function planOptionsHtml(selected) {
    return PLAN_OPTIONS.map(([value, label]) =>
      `<option value="${value}"${value === selected ? " selected" : ""}>${label}</option>`
    ).join("");
  }

  function ensureChallengePlan(count) {
    if (!Array.isArray(S.challengePlan)) S.challengePlan = [];
    const fallback = S.challengePlan[S.challengePlan.length - 1] || { type: "math" };
    while (S.challengePlan.length < count) {
      S.challengePlan.push({ ...fallback });
    }
    if (S.challengePlan.length > count) S.challengePlan.length = count;
  }

  function renderChallengePlan(count) {
    const host = $("#challenge-plan-list");
    if (!host) return;
    ensureChallengePlan(count);
    host.innerHTML = S.challengePlan.map((item, index) => `
      <div class="plan-step" data-plan-index="${index}">
        <span class="plan-order">${index + 1}</span>
        <select data-plan-type aria-label="Challenge ${index + 1}">${planOptionsHtml(descriptorToValue(item))}</select>
        <button class="btn ghost tiny" type="button" data-plan-move="up" data-plan-index="${index}"${index === 0 ? " disabled" : ""} aria-label="Move up">↑</button>
        <button class="btn ghost tiny" type="button" data-plan-move="down" data-plan-index="${index}"${index === count - 1 ? " disabled" : ""} aria-label="Move down">↓</button>
      </div>`).join("");
  }

  function currentChallengePlan() {
    const count = Math.max(1, Math.min(10, Number($("#alarm-challenge-count").value) || 1));
    if (count <= 1) {
      return [planValueToDescriptor($("#alarm-challenge-type").value)];
    }
    ensureChallengePlan(count);
    $("#challenge-plan-list")?.querySelectorAll("[data-plan-index]").forEach((row) => {
      const index = Number(row.dataset.planIndex);
      const select = row.querySelector("[data-plan-type]");
      if (select && index < S.challengePlan.length) {
        S.challengePlan[index] = planValueToDescriptor(select.value);
      }
    });
    return S.challengePlan.slice(0, count);
  }

  function completionText(alarm) {
    if (alarm.mode !== "challenge") return "Standard";
    const count = alarmParticipants(alarm).length;
    const typeLabel = CHALLENGE_TYPE_LABEL[alarm.challenge_type] || "Maths";
    const type = I18N()?.translate(typeLabel) || typeLabel;
    const each = alarm.challenge_count > 1
      ? (I18N()?.t("card.each", { n: alarm.challenge_count }) || ` · ${alarm.challenge_count} each`)
      : "";
    if (alarm.completion_mode === "count") {
      return (I18N()?.t("card.count", { type, count, target: alarm.target_count })
        || `${type} · ${count} selected · stops after ${alarm.target_count} answers`) + each;
    }
    return (I18N()?.t("card.all", { type, count })
      || `${type} · ${count} selected · all must answer`) + each;
  }

  function openLinkDialog(alarm) {
    if (!alarm || !alarm.slug) return;
    const link = alarm.link || `${baseUrl()}/${alarm.slug}`;
    S.currentLink = link;
    $("#link-title").textContent = `${alarm.label} · shortlink`;
    $("#link-url").textContent = link;
    const qr = $("#link-qr");
    qr.src = `${alarm.qr_url || `/qr/${alarm.slug}.svg`}?v=${Date.now()}`;
    $("#open-link").href = link;
    const dialog = $("#link-dialog");
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
  }

  function closeLinkDialog() {
    const dialog = $("#link-dialog");
    if (dialog.open) dialog.close();
    else dialog.removeAttribute("open");
  }

  function renderAlarms(data) {
    const sig = sigOf(data.alarms) + sigOf(data.active_events.map((e) => [e.id, e.state]));
    const host = $("#alarms");
    if (S.sig.alarms === sig) return;
    S.sig.alarms = sig;

    host.innerHTML = data.alarms.map((alarm) => {
      const ringing = data.active_events.some(
        (e) => e.alarm_id === alarm.id && (e.state === "ringing" || e.state === "snoozed")
      );
      const snoozed = data.active_events.some((e) => e.alarm_id === alarm.id && e.state === "snoozed");
      const modeBadge = ringing
        ? `<span class="live-tag">${snoozed ? "Snoozed" : "Ringing"}</span>`
        : `<span class="badge ${alarm.mode === "challenge" ? "challenge" : ""}">${alarm.mode === "challenge" ? "Challenge" : "Standard"}</span>`;
      const nextText = !alarm.enabled
        ? "Paused"
        : ringing
          ? (snoozed ? "Snoozed — will ring again" : "Ringing right now")
          : (alarm.next_fire ? (I18N()?.next(alarm.next_fire, serverNow()) || alarm.next_human) : alarm.next_human);
      const extras = [];
      if (alarm.mode === "challenge") extras.push(completionText(alarm));
      if (alarm.skip_next) extras.push("Next ring skipped");
      if (alarm.muted) extras.push("Muted — no sound");
      if (alarm.music_name) extras.push(I18N()?.t("card.music", { name: alarm.music_name }) || `Music · ${alarm.music_name}`);
      if (alarm.calendar_name) extras.push(I18N()?.t("card.calendar", { name: alarm.calendar_name }) || `Special days · ${alarm.calendar_name}`);
      return `
        <article class="alarm-card${alarm.enabled ? "" : " off"}${ringing ? " ringing" : ""}">
          <div class="alarm-top">
            <div class="alarm-time">${esc(alarm.time)}</div>
            ${modeBadge}
          </div>
          <div class="alarm-label" title="${esc(alarm.label)}">${esc(alarm.label)}</div>
          <div class="alarm-days">${esc(I18N()?.days(alarm) || alarm.days_text)}</div>
          ${extras.length ? `<div class="alarm-detail">${esc(extras.join(" · "))}</div>` : ""}
          <div class="alarm-next">${esc(nextText)}</div>
          <div class="alarm-actions">
            <button class="switch${alarm.enabled ? " on" : ""}" type="button" role="switch"
                    aria-checked="${alarm.enabled}" aria-label="Toggle ${esc(alarm.label)}"
                    data-action="toggle" data-id="${alarm.id}"><span></span></button>
            <span class="spacer"></span>
            ${alarm.slug ? `<button class="btn ghost tiny" type="button" data-action="link" data-id="${alarm.id}" title="Shortlink and QR code">QR</button>` : ""}
            ${alarm.enabled && alarm.next_fire ? `<button class="btn ghost tiny" type="button" data-action="skip" data-id="${alarm.id}" data-skip="${alarm.skip_next ? "0" : "1"}" title="Skip the next scheduled ring">${alarm.skip_next ? "Undo skip" : "Skip next"}</button>` : ""}
            <button class="btn ghost tiny" type="button" data-action="ring" data-id="${alarm.id}"${ringing ? " disabled" : ""}>${ringing ? (snoozed ? "Snoozed" : "Ringing") : "Ring now"}</button>
            <button class="btn tiny" type="button" data-action="edit" data-id="${alarm.id}">Edit</button>
          </div>
        </article>`;
    }).join("");

    $("#alarms-empty").hidden = data.alarms.length > 0;
    $("#alarm-count").textContent = data.alarms.length
      ? `${data.alarms.length} total · ${data.alarms.filter((a) => a.enabled).length} enabled`
      : "";
  }

  function findAlarm(id) {
    return S.data?.alarms.find((a) => a.id === Number(id)) || null;
  }

  async function toggleAlarm(id, enabled) {
    try {
      await api(`/api/alarms/${id}/toggle`, { method: "POST", body: { enabled } });
      await refresh();
      toast(enabled ? "Alarm enabled" : "Alarm paused");
    } catch (err) { toast(err.message, "error"); }
  }

  async function skipAlarm(id, skip) {
    try {
      await api(`/api/alarms/${id}/skip`, { method: "POST", body: { skip } });
      await refresh();
      toast(skip ? "Next ring will be skipped" : "Skip cancelled");
    } catch (err) { toast(err.message, "error"); }
  }

  async function ringNow(id) {
    const alarm = findAlarm(id);
    const ok = await confirmAction({
      title: "Ring this alarm now?",
      text: `${alarm ? alarm.label : "This alarm"} will start on the server speaker immediately.`,
      confirmLabel: "Ring now",
      danger: false,
    });
    if (!ok) return;
    try {
      await api(`/api/alarms/${id}/ring`, { method: "POST", body: {} });
      await refresh();
      toast("Alarm ringing");
    } catch (err) { toast(err.message, "error"); }
  }

  // ------------------------------------------------------------ alarm modal
  function randomSlug() {
    const bytes = new Uint8Array(4);
    crypto.getRandomValues(bytes);
    return "alarm-" + Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  }

  function renderParticipantPicker(selectedIds) {
    const selected = new Set((selectedIds || []).map(Number));
    const users = S.data?.users || [];
    const host = $("#alarm-users");
    if (!users.length) {
      host.innerHTML = `<span class="picker-empty">No users yet. Add people in the Users tab first.</span>`;
      updateParticipantCount();
      return;
    }
    host.innerHTML = users.map((user) => `
      <label class="pick-user${selected.has(user.id) ? " checked" : ""}${user.active ? "" : " paused"}">
        <input type="checkbox" value="${user.id}"${selected.has(user.id) ? " checked" : ""}>
        <span>${esc(user.name)}</span>
        ${user.active ? "" : "<small>paused</small>"}
      </label>`).join("");
    updateParticipantCount();
  }

  function selectedParticipantIds() {
    return $$("#alarm-users input:checked").map((input) => Number(input.value));
  }

  function updateParticipantCount() {
    const max = S.data?.limits?.max_alarm_users || 6;
    const count = selectedParticipantIds().length;
    $("#participant-count").textContent = `${count} / ${max} selected`;
    $$("#alarm-users .pick-user").forEach((label) => {
      label.classList.toggle("checked", $("input", label).checked);
    });
  }

  function updateSlugPreview() {
    const value = $("#alarm-slug").value.trim().toLowerCase();
    const preview = value ? `${baseUrl()}/${value}` : `${baseUrl()}/<auto-generated>`;
    $("#slug-preview").textContent = preview;
  }

  function updateCalendarVisibility() {
    const once = $("#alarm-once").value;
    const repeat = $$("#day-picker .day.on").length > 0;
    $("#calendar-field").hidden = Boolean(once) || !repeat;
  }

  function updateChallengeOptions() {
    const mode = $('input[name="mode"]:checked')?.value || "standard";
    const challenge = mode === "challenge";
    $("#challenge-options").hidden = !challenge;
    const completion = $("#alarm-completion").value;
    $("#target-row").hidden = !challenge || completion !== "count";
    const target = $("#alarm-target");
    const max = Math.max(1, selectedParticipantIds().length || 1);
    target.max = String(max);
    if (Number(target.value) > max) target.value = String(max);

    const count = Math.max(1, Math.min(10, Number($("#alarm-challenge-count").value) || 1));
    const multi = count > 1;
    $("#single-challenge-type-field").hidden = multi;
    $("#challenge-plan-wrap").hidden = !multi;
    if (!multi && S.challengePlan?.length) {
      $("#alarm-challenge-type").value = descriptorToValue(S.challengePlan[0]);
    }
    renderChallengePlan(count);

    const type = multi ? S.challengePlan[0]?.type : planValueToDescriptor($("#alarm-challenge-type").value).type;
    const patternSize = multi
      ? S.challengePlan[0]?.size
      : planValueToDescriptor($("#alarm-challenge-type").value).size;
    const questions = S.data?.questions || [];
    const hint = $("#challenge-type-hint");
    if (multi) {
      hint.textContent = `A different challenge can be used for each of the ${count} steps.`;
    } else if (type === "text" || type === "choice" || type === "random_choice") {
      const poolKind = type === "random_choice" ? "choice" : type;
      const poolCount = poolKind === "choice"
        ? questions.filter((q) => q.kind === "choice").length
        : questions.filter((q) => (q.kind || "text") === "text").length;
      hint.textContent = poolCount
        ? (type === "random_choice"
          ? `A random sequence from ${poolCount} multiple-choice questions is shared by the session.`
          : `${poolCount} ${poolKind === "choice" ? "multiple-choice" : "text"} question${poolCount === 1 ? "" : "s"} available.`)
        : `No ${poolKind === "choice" ? "multiple-choice" : "text"} questions yet — add one in Challenges.`;
    } else if (type === "color") {
      hint.textContent = "Each person gets a target swatch and four colours to choose from.";
    } else if (type === "pattern") {
      hint.textContent = `Each person paints a ${patternSize || 3}×${patternSize || 3} target pattern.`;
    } else if (type === "hold") {
      hint.textContent = "Hold the on-screen button for five seconds.";
    } else if (type === "typing") {
      hint.textContent = "Type a generated phrase exactly. Copy and paste are disabled.";
    } else if (type === "dice") {
      hint.textContent = "Roll a die and match the target; the fifth try is guaranteed.";
    } else {
      hint.textContent = "Arithmetic generated per person.";
    }
    updateParticipantCount();
    updateSlugPreview();
    updateCalendarVisibility();
  }

  function openAlarmDialog(alarm) {
    S.editor = alarm ? alarm.id : null;
    const dialog = $("#alarm-dialog");
    $("#alarm-dialog-title").textContent = alarm ? "Edit alarm" : "New alarm";
    $("#alarm-label").value = alarm ? alarm.label : "Wake up";
    $("#alarm-time").value = alarm ? alarm.time : "07:00";
    $("#alarm-once").value = alarm?.once_date || "";
    $("#alarm-challenge-count").value = String(alarm?.challenge_count || 1);
    $("#alarm-snooze").value = alarm?.snooze_minutes ?? 9;
    $("#alarm-max-snooze").value = alarm?.max_snoozes ?? 2;
    $("#alarm-max-ring").value = alarm?.max_ring_minutes ?? 15;
    $("#alarm-enabled").checked = alarm ? alarm.enabled : true;
    $("#alarm-error").textContent = "";
    $("#alarm-delete").hidden = !alarm;
    $("#alarm-completion").value = alarm?.completion_mode || "all";
    $("#alarm-target").value = alarm?.target_count || 1;
    const count = Number(alarm?.challenge_count || 1);
    const savedPlan = Array.isArray(alarm?.challenge_plan) && alarm.challenge_plan.length
      ? alarm.challenge_plan.map((item) => ({ ...item }))
      : Array.from({ length: count }, () => ({
        type: alarm?.challenge_type || "math",
        ...(alarm?.challenge_type === "pattern" ? { size: 3 } : {}),
      }));
    S.challengePlan = savedPlan.slice(0, count);
    ensureChallengePlan(count);
    $("#alarm-challenge-type").value = descriptorToValue(S.challengePlan[0]);
    $("#alarm-muted").checked = Boolean(alarm?.muted);
    $("#alarm-slug").value = alarm?.slug || randomSlug();

    const days = new Set(alarm ? alarm.days : [1, 2, 3, 4, 5]);
    $$("#day-picker .day").forEach((btn) => {
      btn.classList.toggle("on", days.has(Number(btn.dataset.day)));
    });
    const mode = alarm ? alarm.mode : "standard";
    $$('input[name="mode"]').forEach((input) => { input.checked = input.value === mode; });

    const selected = alarm
      ? alarm.participant_ids
      : (S.data?.users || []).filter((u) => u.active).slice(0, 6).map((u) => u.id);
    renderParticipantPicker(selected);

    $("#alarm-music").innerHTML = '<option value="">Built-in beep</option>' +
      (S.data?.music || []).map((m) => `<option value="${m.id}">${esc(m.name)}</option>`).join("");
    $("#alarm-music").value = alarm?.music_id ? String(alarm.music_id) : "";

    $("#alarm-calendar").innerHTML = '<option value="">None — use the week pattern</option>' +
      (S.data?.calendars || []).map((c) => `<option value="${c.id}">${esc(c.name)}</option>`).join("");
    $("#alarm-calendar").value = alarm?.calendar_id ? String(alarm.calendar_id) : "";

    updateChallengeOptions();
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
    setTimeout(() => $("#alarm-label").focus(), 40);
  }

  function closeAlarmDialog() {
    const dialog = $("#alarm-dialog");
    if (dialog.open) dialog.close();
    else dialog.removeAttribute("open");
  }

  async function saveAlarm(event) {
    event.preventDefault();
    const error = $("#alarm-error");
    error.textContent = "";
    const label = $("#alarm-label").value.trim();
    const time = $("#alarm-time").value;
    const once = $("#alarm-once").value;
    const days = $$("#day-picker .day.on").map((b) => Number(b.dataset.day));
    const mode = $('input[name="mode"]:checked')?.value || "standard";
    const participants = mode === "challenge" ? selectedParticipantIds() : [];
    if (!label) { error.textContent = "Give the alarm a label."; return; }
    if (!/^\d{2}:\d{2}$/.test(time)) { error.textContent = "Pick a time."; return; }
    if (days.length && once) { error.textContent = "Choose repeat days or a one-time date, not both."; return; }
    if (!days.length && !once) { error.textContent = "Pick at least one weekday, or a one-time date."; return; }
    if (mode === "challenge") {
      if (!participants.length) { error.textContent = "Select at least one user."; return; }
      if (participants.length > (S.data?.limits?.max_alarm_users || 6)) {
        error.textContent = "An alarm can select at most six users.";
        return;
      }
      const challengeCount = Number($("#alarm-challenge-count").value);
      if (!Number.isInteger(challengeCount) || challengeCount < 1 || challengeCount > 10) {
        error.textContent = "Challenges per person must be between 1 and 10.";
        return;
      }
      const plan = currentChallengePlan();
      for (const step of plan) {
        if (!["text", "choice", "random_choice"].includes(step.type)) continue;
        const poolKind = step.type === "random_choice" ? "choice" : step.type;
        const available = (S.data?.questions || []).filter(
          (q) => (q.kind || "text") === poolKind
        ).length;
        if (!available) {
          error.textContent = "Add a question of this type in the Challenges tab first.";
          return;
        }
      }
    }
    const completionMode = $("#alarm-completion").value;
    const target = Number($("#alarm-target").value) || 1;
    if (mode === "challenge" && completionMode === "count" && (target < 1 || target > participants.length)) {
      error.textContent = "The finish target must be between 1 and the number of selected users.";
      return;
    }
    const slug = $("#alarm-slug").value.trim().toLowerCase();
    if (slug && !/^[a-z0-9][a-z0-9_-]{2,39}$/.test(slug)) {
      error.textContent = "Shortlink must be 3-40 characters: a-z, 0-9, - or _.";
      return;
    }
    const payload = {
      label,
      time,
      days,
      once_date: once || null,
      enabled: $("#alarm-enabled").checked,
      mode,
      challenge_count: Number($("#alarm-challenge-count").value),
      snooze_minutes: Number($("#alarm-snooze").value) || 9,
      max_snoozes: Number($("#alarm-max-snooze").value) || 0,
      max_ring_minutes: Number($("#alarm-max-ring").value) || 15,
      participants,
      completion_mode: completionMode,
      target_count: completionMode === "count" ? target : 1,
      challenge_type: currentChallengePlan()[0]?.type || "math",
      challenge_plan: currentChallengePlan(),
      muted: $("#alarm-muted").checked,
      music_id: $("#alarm-music").value ? Number($("#alarm-music").value) : null,
      calendar_id: once ? null : ($("#alarm-calendar").value ? Number($("#alarm-calendar").value) : null),
      slug,
    };
    const save = $("#alarm-save");
    const wasEditing = Boolean(S.editor);
    save.disabled = true;
    save.textContent = "Saving…";
    try {
      const result = wasEditing
        ? await api(`/api/alarms/${S.editor}`, { method: "PUT", body: payload })
        : await api("/api/alarms", { method: "POST", body: payload });
      closeAlarmDialog();
      await refresh();
      toast(wasEditing ? "Alarm updated" : "Alarm created");
      if (!wasEditing && mode === "challenge" && result?.alarm?.slug) {
        openLinkDialog(result.alarm);
      }
    } catch (err) {
      error.textContent = err.message;
    } finally {
      save.disabled = false;
      save.textContent = "Save alarm";
    }
  }

  async function deleteAlarm() {
    if (!S.editor) return;
    const ok = await confirmAction({
      title: "Delete this alarm?",
      text: "The schedule is removed. Past rings stay in the history.",
      confirmLabel: "Delete",
    });
    if (!ok) return;
    try {
      await api(`/api/alarms/${S.editor}`, { method: "DELETE" });
      closeAlarmDialog();
      await refresh();
      toast("Alarm deleted");
    } catch (err) { toast(err.message, "error"); }
  }

  // ----------------------------------------------------------------- users
  function renderUsers(data) {
    const sig = sigOf(data.users) + data.limits.max_users;
    if (S.sig.users === sig) return;
    const host = $("#users");
    if (host.contains(document.activeElement)) return; // don't clobber an in-progress rename
    S.sig.users = sig;

    const max = data.limits.max_users;
    const active = data.users.filter((u) => u.active).length;
    $("#user-count").textContent = `${data.users.length} users · ${active} active`;
    $("#user-limit").textContent = data.users.length >= max
      ? `The server limit is ${max} users. Delete someone to add another.`
      : `No six-person limit here. Each alarm can still select at most ${data.limits.max_alarm_users} users.`;
    $("#add-user-name").disabled = data.users.length >= max;
    $("#add-user-btn").disabled = data.users.length >= max;

    host.innerHTML = data.users.map((user) => `
      <li class="user-row${user.active ? "" : " paused"}" data-id="${user.id}">
        <span class="avatar">${esc(Array.from(user.name)[0] || "?")}</span>
        <input type="text" value="${esc(user.name)}" maxlength="30" aria-label="Name for ${esc(user.name)}">
        <span class="badge ${user.active ? "on" : "off"}">${user.active ? "Active" : "Paused"}</span>
        <div class="user-actions">
          <button class="btn ghost tiny" type="button" data-action="save">Save</button>
          <button class="btn ghost tiny" type="button" data-action="toggle">${user.active ? "Pause" : "Resume"}</button>
          <button class="btn danger tiny" type="button" data-action="delete">Delete</button>
        </div>
      </li>`).join("");
  }

  async function addUser(event) {
    event.preventDefault();
    const input = $("#add-user-name");
    const name = input.value.trim();
    if (!name) return;
    try {
      await api("/api/users", { method: "POST", body: { name } });
      input.value = "";
      await refresh();
      toast(`${name} added`);
    } catch (err) { toast(err.message, "error"); }
  }

  async function userAction(button) {
    const row = button.closest(".user-row");
    const id = row?.dataset.id;
    if (!id) return;
    const action = button.dataset.action;
    try {
      if (action === "save") {
        const name = $("input", row).value.trim();
        if (!name) { toast("Name cannot be empty", "error"); return; }
        await api(`/api/users/${id}`, { method: "PUT", body: { name } });
        await refresh();
        toast("Name saved");
      } else if (action === "toggle") {
        const paused = row.classList.contains("paused");
        await api(`/api/users/${id}`, { method: "PUT", body: { active: paused } });
        await refresh();
        toast(paused ? "Person resumed" : "Person paused");
      } else if (action === "delete") {
        const name = $("input", row)?.value || "this person";
        const ok = await confirmAction({
          title: `Delete ${name}?`,
          text: "Their answers in past alarms stay in the history. Future challenge alarms will not ask them.",
          confirmLabel: "Delete",
        });
        if (!ok) return;
        await api(`/api/users/${id}`, { method: "DELETE" });
        await refresh();
        toast("Person deleted");
      }
    } catch (err) { toast(err.message, "error"); }
  }

  // ------------------------------------------------------------ questions
  function renderQuestions(data) {
    const questions = data.questions || [];
    const sig = sigOf(questions);
    $("#question-count").textContent = `${questions.length} question${questions.length === 1 ? "" : "s"}`;
    $("#questions-empty").hidden = questions.length > 0;
    if (S.sig.questions === sig) return;
    S.sig.questions = sig;
    $("#questions-body").innerHTML = questions.map((q) => {
      const kind = q.kind === "choice"
        ? `<span class="badge warn">Choice</span>`
        : `<span class="badge">Text</span>`;
      const answer = q.kind === "choice"
        ? `${esc(q.answer)} <span class="muted small">(${(q.options || []).length} options)</span>`
        : esc(q.answer);
      return `
        <tr data-id="${q.id}">
          <td>${kind}</td>
          <td class="question-text">${esc(q.question)}</td>
          <td class="answer-text">${answer}</td>
          <td>
            <button class="btn ghost tiny" type="button" data-question-action="edit">Edit</button>
            <button class="btn danger tiny" type="button" data-question-action="delete">Delete</button>
          </td>
        </tr>`;
    }).join("");
  }

  function updateQuestionKind() {
    const choice = $("#question-kind").value === "choice";
    $("#choice-options-field").hidden = !choice;
    $("#answer-label").textContent = choice ? "Correct answer" : "Answer";
    $("#answer-hint").textContent = choice
      ? "Must exactly match one of the options above."
      : "Text answers ignore case and extra spaces.";
  }

  function resetQuestionForm() {
    S.questionEditId = null;
    $("#question-id").value = "";
    $("#question-kind").value = "text";
    $("#question-text").value = "";
    $("#question-options").value = "";
    $("#question-answer").value = "";
    $("#question-error").textContent = "";
    $("#question-save").textContent = "Add question";
    $("#question-cancel").hidden = true;
    updateQuestionKind();
  }

  async function saveQuestion(event) {
    event.preventDefault();
    const error = $("#question-error");
    error.textContent = "";
    const kind = $("#question-kind").value;
    const question = $("#question-text").value.trim();
    const answer = $("#question-answer").value.trim();
    const options = $("#question-options").value.split("\n").map((x) => x.trim()).filter(Boolean);
    if (!question || !answer) { error.textContent = "A question and an answer are required."; return; }
    if (kind === "choice") {
      if (options.length < 2 || options.length > 6) {
        error.textContent = "Multiple choice needs 2–6 options, one per line.";
        return;
      }
      if (!options.includes(answer)) {
        error.textContent = "The correct answer must exactly match one option.";
        return;
      }
    }
    const payload = { question, answer, kind, options: kind === "choice" ? options : [] };
    const button = $("#question-save");
    button.disabled = true;
    try {
      if (S.questionEditId) {
        await api(`/api/questions/${S.questionEditId}`, { method: "PUT", body: payload });
        toast("Question updated");
      } else {
        await api("/api/questions", { method: "POST", body: payload });
        toast("Question added");
      }
      resetQuestionForm();
      await refresh();
    } catch (err) {
      error.textContent = err.message;
    } finally {
      button.disabled = false;
    }
  }

  async function importQuestions(event) {
    event.preventDefault();
    const input = $("#question-csv");
    const error = $("#question-import-error");
    error.textContent = "";
    const file = input.files?.[0];
    if (!file) { error.textContent = "Choose a CSV file."; return; }
    if (file.size > 2 * 1024 * 1024) {
      error.textContent = "That CSV is too large.";
      return;
    }
    const button = $("#question-import");
    button.disabled = true;
    button.textContent = "Importing…";
    try {
      const csv = await file.text();
      const data = await api("/api/questions/import", { method: "POST", body: { csv } });
      input.value = "";
      await refresh();
      toast(`${data.imported} question${data.imported === 1 ? "" : "s"} imported`);
    } catch (err) {
      error.textContent = err.message;
    } finally {
      button.disabled = false;
      button.textContent = "Import questions";
    }
  }

  async function questionAction(button) {
    const row = button.closest("tr");
    const id = Number(row?.dataset.id);
    if (!id) return;
    const item = (S.data?.questions || []).find((q) => q.id === id);
    if (!item) return;
    if (button.dataset.questionAction === "edit") {
      S.questionEditId = id;
      $("#question-id").value = String(id);
      $("#question-kind").value = item.kind || "text";
      $("#question-text").value = item.question;
      $("#question-options").value = (item.options || []).join("\n");
      $("#question-answer").value = item.answer;
      $("#question-save").textContent = "Save question";
      $("#question-cancel").hidden = false;
      updateQuestionKind();
      $("#question-text").focus();
      return;
    }
    if (button.dataset.questionAction === "delete") {
      const ok = await confirmAction({
        title: "Delete this question?",
        text: "Alarms already using custom questions pick a new one when they ring. This cannot be undone.",
        confirmLabel: "Delete",
      });
      if (!ok) return;
      try {
        await api(`/api/questions/${id}`, { method: "DELETE" });
        await refresh();
        toast("Question deleted");
      } catch (err) { toast(err.message, "error"); }
    }
  }

  // ---------------------------------------------------------------- music
  function formatBytes(bytes) {
    const n = Number(bytes) || 0;
    if (n < 1024) return `${n} B`;
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
    return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  }

  function renderMusic(data) {
    const tracks = data.music || [];
    const preview = data.music_preview || {};
    const sig = sigOf(tracks) + sigOf(preview);
    $("#music-count").textContent = `${tracks.length} track${tracks.length === 1 ? "" : "s"}`;
    $("#music-empty").hidden = tracks.length > 0;
    const previewError = $("#music-preview-error");
    if (previewError) previewError.textContent = preview.error || "";
    if (S.sig.music === sig) return;
    S.sig.music = sig;
    $("#music-list").innerHTML = tracks.map((track) => {
      const playing = Boolean(preview.playing && preview.music_id === track.id);
      return `
      <li class="music-item" data-id="${track.id}">
        <div class="track-info">
          <div class="track-name">${esc(track.name)}</div>
          <div class="track-meta">${esc(formatBytes(track.size))} · ${esc(track.mime || "audio")}</div>
        </div>
        <audio controls preload="none" src="${esc(track.file_url)}"></audio>
        <div class="music-actions">
          <button class="btn ghost tiny" type="button" data-music-action="test"${playing ? " disabled" : ""}>${playing ? "Playing…" : "Test on server"}</button>
          <button class="btn tiny" type="button" data-music-action="stop"${playing ? "" : " disabled"}>Stop</button>
          <button class="btn danger tiny" type="button" data-music-action="delete">Delete</button>
        </div>
      </li>`;
    }).join("");
  }

  async function uploadMusic(event) {
    event.preventDefault();
    const input = $("#music-file");
    const error = $("#music-error");
    error.textContent = "";
    const file = input.files?.[0];
    if (!file) { error.textContent = "Choose an audio file."; return; }
    if (file.size > (S.data?.limits?.max_music_bytes || 25 * 1024 * 1024)) {
      error.textContent = "That file is larger than 25 MB.";
      return;
    }
    const display = $("#music-name").value.trim();
    const button = $("#music-upload");
    button.disabled = true;
    button.textContent = "Uploading…";
    try {
      const url = `/api/music?name=${encodeURIComponent(file.name)}${display ? `&display=${encodeURIComponent(display)}` : ""}`;
      const res = await fetch(url, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": file.type || "application/octet-stream",
          "X-Unzzz-Csrf": "1",
        },
        body: file,
      });
      let data = null;
      try { data = await res.json(); } catch (_err) { /* noop */ }
      if (res.status === 401) { showAuth("login"); return; }
      if (!res.ok || !data?.ok) throw new Error(data?.error || "Upload failed");
      input.value = "";
      $("#music-name").value = "";
      await refresh();
      toast("Music uploaded");
    } catch (err) {
      error.textContent = err.message;
    } finally {
      button.disabled = false;
      button.textContent = "Upload music";
    }
  }

  async function testServerMusic(id) {
    try {
      await api(`/api/music/${id}/test`, { method: "POST", body: {} });
      await refresh();
      toast("Server test started");
    } catch (err) { toast(err.message, "error"); }
  }

  async function stopServerMusic(id) {
    try {
      await api(`/api/music/${id}/stop`, { method: "POST", body: {} });
      await refresh();
      toast("Server test stopped");
    } catch (err) { toast(err.message, "error"); }
  }

  async function deleteMusic(id) {
    const track = (S.data?.music || []).find((m) => m.id === id);
    const ok = await confirmAction({
      title: `Delete ${track ? track.name : "this track"}?`,
      text: "The file is removed from the server. Alarms using it must be changed first.",
      confirmLabel: "Delete",
    });
    if (!ok) return;
    try {
      await api(`/api/music/${id}`, { method: "DELETE" });
      await refresh();
      toast("Music deleted");
    } catch (err) { toast(err.message, "error"); }
  }

  // ------------------------------------------------------------------ links
  function linkExpiryText(ts) {
    return ts ? fmtDateTime(ts) : "No expiry";
  }

  function renderLinks(data) {
    const links = data.links || [];
    const sig = sigOf(links);
    $("#links-count").textContent = `${links.length} link${links.length === 1 ? "" : "s"}`;
    $("#links-empty").hidden = links.length > 0;
    $("#all-link-row").hidden = links.some((item) => item.kind === "all");
    if (S.sig.links === sig) return;
    S.sig.links = sig;
    $("#links-list").innerHTML = links.map((item) => `
      <li class="link-item" data-link-kind="${esc(item.kind)}"${item.id != null ? ` data-link-id="${item.id}"` : ""}>
        <div class="link-info">
          <div class="link-title">${esc(item.label)} <span class="badge">${esc(item.mode === "all" ? "All-in-one" : item.mode)}</span></div>
          <div class="link-url">${esc(item.url)}</div>
          <div class="link-meta">Expires: ${esc(linkExpiryText(item.expires_at))}</div>
        </div>
        <div class="link-actions">
          <button class="btn ghost tiny" type="button" data-link-action="edit">Modify</button>
          <button class="btn ghost tiny" type="button" data-link-action="qr">QR</button>
          <a class="btn tiny" href="${esc(item.url)}" target="_blank" rel="noopener">Open link</a>
        </div>
      </li>`).join("");
  }

  function localInput(ts) {
    if (!ts) return "";
    const d = new Date(ts * 1000);
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  function openLinkEditor(kind, id) {
    const item = (S.data?.links || []).find(
      (entry) => entry.kind === kind && (id == null || entry.id === id)
    );
    S.linkEdit = { kind, id: id ?? null, exists: Boolean(item) };
    $("#link-edit-kind").value = kind;
    $("#link-edit-id").value = id ?? "";
    $("#link-edit-title").textContent = item ? `Edit ${item.label}` : "Create all-in-one link";
    $("#link-edit-target").textContent = item ? item.url : "A shortcut that opens the most recent alarm challenge.";
    $("#link-edit-slug").value = item?.slug || "all";
    $("#link-edit-expiry").value = localInput(item?.expires_at);
    $("#link-edit-delete").hidden = kind !== "all" || !item;
    $("#link-edit-error").textContent = "";
    const dialog = $("#link-edit-dialog");
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
  }

  function closeLinkEditor() {
    const dialog = $("#link-edit-dialog");
    if (dialog.open) dialog.close();
    else dialog.removeAttribute("open");
  }

  async function saveLinkEditor(event) {
    event.preventDefault();
    const error = $("#link-edit-error");
    error.textContent = "";
    const edit = S.linkEdit;
    if (!edit) return;
    const slug = $("#link-edit-slug").value.trim().toLowerCase();
    const expiryValue = $("#link-edit-expiry").value;
    const expires = expiryValue ? new Date(expiryValue).getTime() / 1000 : null;
    try {
      if (edit.kind === "all") {
        if (!edit.exists) {
          await api("/api/links/all", { method: "POST", body: { slug, expires_at: expires } });
        } else {
          await api("/api/links/all", { method: "PUT", body: { slug, expires_at: expires } });
        }
      } else {
        await api(`/api/links/alarm/${edit.id}`, { method: "PUT", body: { slug, expires_at: expires } });
      }
      closeLinkEditor();
      await refresh();
      toast("Link saved");
    } catch (err) {
      error.textContent = err.message;
    }
  }

  async function deleteAllLink() {
    const edit = S.linkEdit;
    if (!edit || edit.kind !== "all" || !edit.exists) return;
    try {
      await api("/api/links/all", { method: "DELETE", body: {} });
      closeLinkEditor();
      await refresh();
      toast("All-in-one link deleted");
    } catch (err) {
      const error = $("#link-edit-error");
      if (error) error.textContent = err.message;
    }
  }

  async function linkAction(button) {
    const row = button.closest(".link-item");
    if (!row) return;
    const kind = row.dataset.linkKind;
    const id = row.dataset.linkId ? Number(row.dataset.linkId) : null;
    const item = (S.data?.links || []).find(
      (entry) => entry.kind === kind && (id == null || entry.id === id)
    );
    if (!item) return;
    if (button.dataset.linkAction === "edit") openLinkEditor(kind, id);
    else if (button.dataset.linkAction === "qr") openLinkDialog({
      label: item.label,
      slug: item.slug,
      link: item.url,
      qr_url: item.qr_url,
    });
  }

  // -------------------------------------------------------------- calendars
  function renderCalendars(data) {
    const calendars = data.calendars || [];
    const sig = sigOf(calendars);
    $("#calendar-count").textContent = `${calendars.length} calendar${calendars.length === 1 ? "" : "s"}`;
    $("#calendar-empty").hidden = calendars.length > 0;
    if (S.sig.calendars === sig) return;
    S.sig.calendars = sig;
    $("#calendar-list").innerHTML = calendars.map((cal) => `
      <div class="calendar-item" data-id="${cal.id}">
        <div class="calendar-info">
          <div class="calendar-name">${esc(cal.name)}</div>
          <div class="calendar-meta">${cal.first_date ? `${esc(cal.first_date)} → ${esc(cal.last_date)}` : "No dates"}</div>
          <div class="calendar-counts">
            <span class="badge on">${cal.working_days || 0} work</span>
            <span class="badge">${cal.holiday_days || 0} holiday</span>
            <span class="badge ${cal.alarms_using ? "warn" : ""}">${cal.alarms_using || 0} alarm${cal.alarms_using === 1 ? "" : "s"}</span>
          </div>
        </div>
        <button class="btn danger tiny" type="button" data-calendar-action="delete">Delete</button>
      </div>`).join("");
  }

  async function importCalendar(event) {
    event.preventDefault();
    const error = $("#calendar-error");
    error.textContent = "";
    const name = $("#calendar-name").value.trim();
    const input = $("#calendar-file");
    const file = input.files?.[0];
    if (!name) { error.textContent = "Give the calendar a name."; return; }
    if (!file) { error.textContent = "Choose a CSV file."; return; }
    if (file.size > 2 * 1024 * 1024) { error.textContent = "That CSV is too large."; return; }
    const button = $("#calendar-upload");
    button.disabled = true;
    button.textContent = "Importing…";
    try {
      const csv = await file.text();
      await api("/api/calendars", { method: "POST", body: { name, csv } });
      input.value = "";
      $("#calendar-name").value = "";
      await refresh();
      toast("Calendar imported");
    } catch (err) {
      error.textContent = err.message;
    } finally {
      button.disabled = false;
      button.textContent = "Import calendar";
    }
  }

  async function deleteCalendar(id) {
    const cal = (S.data?.calendars || []).find((c) => c.id === id);
    const ok = await confirmAction({
      title: `Delete ${cal ? cal.name : "this calendar"}?`,
      text: "Alarms using it fall back to their weekday pattern and are rescheduled.",
      confirmLabel: "Delete",
    });
    if (!ok) return;
    try {
      await api(`/api/calendars/${id}`, { method: "DELETE" });
      await refresh();
      toast("Calendar deleted");
    } catch (err) { toast(err.message, "error"); }
  }

  // --------------------------------------------------------------- history
  const STATE_LABEL = {
    completed: ["Answered", "on"],
    stopped: ["Stopped", ""],
    expired: ["Timed out", "warn"],
    interrupted: ["Interrupted", "warn"],
    missed: ["Missed", "danger"],
    skipped: ["Skipped", "warn"],
    ringing: ["Ringing", "danger"],
    snoozed: ["Snoozed", "warn"],
  };

  function renderHistory(data) {
    const sig = sigOf(data.history) + tz();
    if (S.sig.history === sig) return;
    S.sig.history = sig;
    const body = $("#history-body");
    body.innerHTML = data.history.map((event) => {
      const [label, cls] = STATE_LABEL[event.state] || [event.state, ""];
      const answers = event.total > 0 ? `${event.answered}/${event.total}` : "—";
      const when = fmtDateTime(event.fired_at);
      const reason = event.stop_reason ? `<div class="history-sub">${esc(event.stop_reason)}</div>` : "";
      return `
        <tr>
          <td class="history-time">${esc(when)}</td>
          <td><div class="history-label" data-i18n-skip>${esc(event.alarm_label)}</div>${reason}</td>
          <td><span class="badge ${event.mode === "challenge" ? "challenge" : ""}">${event.mode === "challenge" ? "Challenge" : "Standard"}</span></td>
          <td><span class="badge ${cls}">${esc(label)}</span></td>
          <td class="ratio">${esc(answers)}</td>
        </tr>`;
    }).join("");
    $("#history-empty").hidden = data.history.length > 0;
  }

  // -------------------------------------------------------------- settings
  function renderSettings(data) {
    if (!S.settingsLoaded) {
      $("#setting-timezone").value = data.settings.timezone;
      $("#setting-baseurl").value = data.settings.base_url;
      $("#setting-link-retention").value = String(data.settings.link_retention_minutes ?? 30);
      $("#setting-target-volume").value = String(data.volume?.target ?? 80);
      $("#about-version").textContent = data.version;
      $("#about-data").textContent = data.system.data_dir;
      S.settingsLoaded = true;
    }
    $("#audio-backend").textContent = data.audio.backend;
    $("#audio-status").textContent = data.audio.available ? "ready" : "not available";
    $("#audio-hint").textContent = data.audio.hint;
    const volume = data.volume || {};
    $("#current-volume").textContent = volume.current == null
      ? "Unavailable"
      : `${volume.current}%`;
    $("#volume-backend").textContent = volume.backend && volume.backend !== "none"
      ? volume.backend
      : "—";
    $("#volume-hint").textContent = volume.error || "";
    const testButton = $("#audio-test");
    // Keep the test button available even when the current selection looks
    // unsupported: the test result (and the exact player error) is more useful
    // than a disabled button.
    testButton.disabled = false;
    testButton.textContent = "Play test beep";
    const select = $("#setting-audio-device");
    if (S.devicesLoaded && !S.deviceDirty && select) {
      select.value = data.settings.audio_device || "";
    }
  }

  async function loadAudioDevices(force = false) {
    if (!S.data) return;
    if (S.devicesLoaded && !force) {
      const select = $("#setting-audio-device");
      if (select) select.value = S.deviceDirty ? select.value : (S.data.settings.audio_device || "");
      return;
    }
    try {
      const data = await api("/api/audio/devices");
      const select = $("#setting-audio-device");
      const current = S.deviceDirty ? select.value : (data.current || S.data.settings.audio_device || "");
      const devices = data.devices || [];
      if (current && !devices.some((d) => d.value === current)) {
        devices.push({ value: current, label: `Custom · ${current}` });
      }
      select.innerHTML = devices.map((d) => `<option value="${esc(d.value)}">${esc(d.label)}</option>`).join("");
      select.value = current;
      S.devicesLoaded = true;
      $("#device-hint").textContent = data.audio.hint;
    } catch (err) {
      toast(err.message, "error");
    }
  }

  async function saveAudioDevice(showToast = true) {
    if (!S.data) return false;
    const select = $("#setting-audio-device");
    if (!select) return false;
    try {
      await api("/api/settings", {
        method: "POST",
        body: {
          timezone: $("#setting-timezone").value.trim(),
          base_url: $("#setting-baseurl").value.trim(),
          audio_device: select.value,
          link_retention_minutes: Number($("#setting-link-retention").value),
          target_volume: Number($("#setting-target-volume").value),
        },
      });
      S.settingsLoaded = false;
      S.devicesLoaded = false;
      S.deviceDirty = false;
      await refresh();
      if (S.view === "settings") await loadAudioDevices();
      if (showToast) toast("Playback device saved");
      return true;
    } catch (err) {
      toast(err.message, "error");
      return false;
    }
  }

  async function saveVolumeTarget(event) {
    event.preventDefault();
    const error = $("#settings-error");
    if (error) error.textContent = "";
    try {
      await api("/api/settings", {
        method: "POST",
        body: {
          timezone: $("#setting-timezone").value.trim(),
          base_url: $("#setting-baseurl").value.trim(),
          audio_device: $("#setting-audio-device").value,
          link_retention_minutes: Number($("#setting-link-retention").value),
          target_volume: Number($("#setting-target-volume").value),
        },
      });
      S.settingsLoaded = false;
      S.devicesLoaded = false;
      S.deviceDirty = false;
      await refresh();
      if (S.view === "settings") await loadAudioDevices();
      toast("Target volume saved");
    } catch (err) {
      if (error) error.textContent = err.message;
      toast(err.message, "error");
    }
  }

  async function refreshDevices() {
    S.devicesLoaded = false;
    await loadAudioDevices(true);
    toast("Device list refreshed");
  }

  function renderAudioWarning() {
    const audio = S.data?.audio;
    const el = $("#audio-warning");
    if (!audio) { el.hidden = true; return; }
    if (!audio.available) {
      el.hidden = false;
      el.textContent = `No sound output: ${audio.hint}`;
    } else if (audio.last_error) {
      el.hidden = false;
      el.textContent = `Audio problem: ${audio.last_error}`;
    } else {
      el.hidden = true;
    }
  }

  async function saveSettings(event) {
    event.preventDefault();
    const error = $("#settings-error");
    error.textContent = "";
    try {
      await api("/api/settings", {
        method: "POST",
        body: {
          timezone: $("#setting-timezone").value.trim(),
          base_url: $("#setting-baseurl").value.trim(),
          audio_device: $("#setting-audio-device").value,
          link_retention_minutes: Number($("#setting-link-retention").value),
          target_volume: Number($("#setting-target-volume").value),
        },
      });
      S.settingsLoaded = false;
      S.devicesLoaded = false;
      S.deviceDirty = false;
      await refresh();
      if (S.view === "settings") await loadAudioDevices();
      toast("Settings saved");
    } catch (err) { error.textContent = err.message; }
  }

  async function testAudio() {
    const btn = $("#audio-test");
    const select = $("#setting-audio-device");
    // The device select is saved on change, but make the test itself robust
    // against a selection made a moment ago (or a failed autosave).
    if (select && S.data && select.value !== (S.data.settings.audio_device || "")) {
      if (!(await saveAudioDevice(false))) return;
    }
    btn.disabled = true;
    btn.textContent = "Playing…";
    try {
      await api("/api/audio/test", { method: "POST", body: {} });
      toast("Test beep played");
    } catch (err) {
      toast(err.message, "error");
      const hint = $("#audio-hint");
      if (hint) hint.textContent = err.message;
      const status = $("#audio-status");
      if (status) status.textContent = "error";
    } finally {
      btn.disabled = false;
      btn.textContent = "Play test beep";
      await refresh();
    }
  }

  async function changePassword(event) {
    event.preventDefault();
    const error = $("#pw-error");
    error.textContent = "";
    const current = $("#pw-current").value;
    const next = $("#pw-new").value;
    const again = $("#pw-new2").value;
    if (next !== again) { error.textContent = "New passwords do not match."; return; }
    try {
      await api("/api/password", { method: "POST", body: { current, new: next } });
      $("#pw-current").value = $("#pw-new").value = $("#pw-new2").value = "";
      toast("Password changed");
    } catch (err) { error.textContent = err.message; }
  }

  // ------------------------------------------------------------------ ring
  function renderRingDock(data) {
    const dock = $("#ring-dock");
    const events = data.active_events;
    document.body.classList.toggle("ringing", events.length > 0);
    const sig = sigOf(events.map((e) => [
      e.id, e.state, e.answered, e.total, e.snooze_count, e.snooze_allowed,
      e.completion_mode, e.target_count, e.alarm_slug,
      e.challenges.map((c) => [c.user_name, c.answered, c.url]),
    ]));
    if (S.sig.ring === sig) return;
    S.sig.ring = sig;
    if (!events.length) {
      dock.hidden = true;
      dock.innerHTML = "";
      return;
    }
    dock.hidden = false;

    const header = `
      <div class="ring-top">
        <span class="ring-pulse"></span>
        <div>
          <div class="ring-title">${events.some((e) => e.state === "ringing") ? "Alarm ringing" : "Alarm snoozed"}</div>
          <div class="ring-meta">${esc(data.timezone)} · stop it before it gives up</div>
        </div>
        <span class="spacer"></span>
        ${events[0].state === "ringing" ? `<span class="ring-elapsed" data-ts="${events[0].fired_at}">0s</span>` : ""}
      </div>`;

    const blocks = events.map((event) => {
      const challenge = event.mode === "challenge";
      const people = event.challenges || [];
      const target = event.completion_mode === "count"
        ? Math.min(event.target_count || 1, event.total || 1)
        : (event.total || 0);
      const progressPct = target ? Math.min(100, Math.round((event.answered / target) * 100)) : 0;
      const progressLabel = event.completion_mode === "count"
        ? `${event.answered}/${target} needed · ${event.total} selected`
        : `${event.answered}/${event.total} answered`;
      const canSnooze = event.snooze_allowed !== undefined
        ? event.snooze_allowed
        : (!challenge || event.total <= 1);
      const links = challenge
        ? `<div class="person-links">${people.map((p) => p.answered
            ? `<span class="person-link answered"><span class="who">${esc(p.user_name)}</span><span class="mini">✓ answered</span></span>`
            : `<span class="person-link"><span class="who">${esc(p.user_name)}</span>
                 <a class="mini open" href="${esc(p.url)}" target="_blank" rel="noopener">Open</a>
                 <button class="mini" type="button" data-action="copy" data-url="${esc(p.url)}">Copy</button></span>`
          ).join("")}
          ${people.some((p) => !p.answered) ? `<button class="mini" type="button" data-action="copyall" data-id="${event.id}">Copy all</button>` : ""}
          </div>`
        : "";

      const actions = [];
      if (event.alarm_slug) {
        actions.push(`<button class="btn ghost" type="button" data-action="qr" data-id="${event.id}">Link &amp; QR</button>`);
      }
      if (event.state === "ringing") {
        const snoozesLeft = event.max_snoozes - event.snooze_count;
        if (canSnooze && snoozesLeft > 0) {
          actions.push(`<button class="btn ghost" type="button" data-action="snooze" data-id="${event.id}">Snooze ${event.snooze_minutes} min (${snoozesLeft} left)</button>`);
        }
        if (!challenge) {
          actions.push(`<button class="btn stop" type="button" data-action="stop" data-id="${event.id}">Stop alarm</button>`);
        } else {
          actions.push(`<button class="btn danger" type="button" data-action="force" data-id="${event.id}">Emergency stop</button>`);
        }
      } else if (event.state === "snoozed") {
        actions.push(`<span class="ring-waiting">Rings again ${event.snooze_until ? "at " + fmtHM(event.snooze_until) : "soon"}</span>`);
        actions.push(`<button class="btn ghost" type="button" data-action="stop" data-id="${event.id}">Cancel snooze</button>`);
      }

      const finishNote = event.total === 1
        ? "This single-user challenge can be answered or snoozed from this panel."
        : (event.completion_mode === "count"
          ? `The sound stops after ${target} correct ${target === 1 ? "answer" : "answers"}; ${event.total} users are selected.`
          : "All selected users must answer; the sound stops when the last one does.");
      return `
        <div class="ring-event">
          <div class="ring-event-head">
            <span class="badge ${challenge ? "challenge" : ""}">${challenge ? "Challenge" : "Standard"}</span>
            <span class="ring-title" data-i18n-skip>${esc(event.alarm_label)}</span>
            <span class="ring-meta">fired ${fmtHM(event.fired_at)}${event.ends_at ? ` · gives up ${fmtHM(event.ends_at)}` : ""}${event.music_name ? ` · ${esc(event.music_name)}` : ""}</span>
          </div>
          ${challenge ? `
            <div class="ring-progress">
              <div class="progress"><span class="progress-fill" data-progress="${progressPct}"></span></div>
              <span class="ring-progress-text">${progressLabel}</span>
            </div>
            ${links}
            ${event.answered < target ? `<div class="ring-waiting">Each person opens their own shortlink and answers the question. ${esc(finishNote)}</div>` : ""}
          ` : `<div class="ring-waiting">Stop it from here${canSnooze ? ", or snooze if you need a few more minutes" : ""}.</div>`}
          <div class="ring-actions">${actions.join("")}</div>
        </div>`;
    }).join("");

    dock.innerHTML = `<div class="ring-dock-inner">${header}${blocks}</div>`;
    $$("[data-progress]", dock).forEach((el) => {
      el.style.width = `${Number(el.dataset.progress) || 0}%`;
    });
  }

  async function ringAction(button) {
    const action = button.dataset.action;
    if (action === "copy") {
      copyText(button.dataset.url);
      return;
    }
    if (action === "copyall") {
      const event = S.data?.active_events.find((e) => String(e.id) === button.dataset.id);
      if (!event) return;
      const lines = event.challenges
        .filter((c) => !c.answered)
        .map((c) => `${c.user_name}: ${c.url}`);
      copyText(lines.join("\n"));
      return;
    }
    if (action === "qr") {
      const event = S.data?.active_events.find((e) => String(e.id) === button.dataset.id);
      if (!event || !event.alarm_slug) return;
      openLinkDialog({
        label: event.alarm_label,
        slug: event.alarm_slug,
        link: event.alarm_link,
        qr_url: event.alarm_qr,
      });
      return;
    }
    const id = button.dataset.id;
    if (!id) return;
    if (action === "force") {
      const ok = await confirmAction({
        title: "Emergency stop?",
        text: "This overrides the challenge before everyone has answered. It is logged in the history.",
        confirmLabel: "Stop anyway",
      });
      if (!ok) return;
      await eventStop(id, true);
    } else if (action === "stop") {
      await eventStop(id, false);
    } else if (action === "snooze") {
      try {
        await api(`/api/events/${id}/snooze`, { method: "POST", body: {} });
        await refresh();
        toast("Snoozed");
      } catch (err) { toast(err.message, "error"); }
    }
  }

  async function eventStop(id, force) {
    try {
      await api(`/api/events/${id}/stop`, { method: "POST", body: { force } });
      await refresh();
      toast("Alarm stopped");
    } catch (err) { toast(err.message, "error"); }
  }

  // ----------------------------------------------------------------- clock
  function tickClock() {
    if (!S.data) return;
    const now = serverNow();
    $("#live-clock").textContent = fmtClock(now);
    $("#live-date").textContent = fmtDate(now);

    const next = S.data.next_alarm;
    if (next && next.next_fire) {
      $("#next-time").textContent = next.time;
      $("#next-label").textContent = next.label;
      $("#next-days").textContent = I18N()?.days(next) || next.days_text;
      $("#next-count").textContent = `${countdownText(next.next_fire)} · ${fmtDate(next.next_fire)}${next.skip_next ? " · " + (I18N()?.translate("next ring skipped") || "next ring skipped") : ""}`;
    } else {
      $("#next-time").textContent = "--:--";
      $("#next-label").textContent = "Nothing scheduled";
      $("#next-days").textContent = "";
      $("#next-count").textContent = "";
    }

    const live = S.data.active_events[0];
    const challenge = live && live.mode === "challenge";
    if (live) {
      const target = live.completion_mode === "count"
        ? Math.min(live.target_count || 1, live.total || 1)
        : (live.total || 0);
      const label = live.completion_mode === "count"
        ? `${live.answered} of ${target} needed`
        : `${live.answered} of ${live.total} answered`;
      $("#answered-ratio").textContent = challenge
        ? label
        : (live.state === "snoozed" ? "Snoozed" : "Standard alarm ringing");
      $("#next-mode").textContent = challenge ? "Challenge" : "Standard";
      const pct = challenge && target ? Math.min(100, Math.round((live.answered / target) * 100)) : (live.state === "snoozed" ? 100 : 0);
      $("#next-progress-fill").style.width = `${pct}%`;
      $("#next-note").textContent = challenge
        ? (live.completion_mode === "count"
          ? `The sound stops after ${target} correct ${target === 1 ? "answer" : "answers"} (${live.total} users selected).`
          : (live.total === 1
            ? "One user must answer; snooze is allowed for this single-user challenge."
            : "All selected users must answer before the sound stops."))
        : "Stop or snooze from the ringing card below.";
    } else {
      const nextCount = next?.participants?.length || 0;
      $("#answered-ratio").textContent = next?.mode === "challenge"
        ? (next.completion_mode === "count"
          ? `${nextCount} selected · stops after ${next.target_count}`
          : `${nextCount} ${nextCount === 1 ? "user" : "users"} must answer`)
        : "Every alarm stops on your command";
      $("#next-mode").textContent = next ? (next.mode === "challenge" ? "Challenge" : "Standard") : "—";
      $("#next-progress-fill").style.width = "0%";
      $("#next-note").textContent = next?.skip_next
        ? "The next scheduled ring will be skipped; following occurrences still run."
        : next?.mode === "challenge"
          ? (nextCount === 1
            ? "A single-user challenge can be snoozed as well as answered."
            : "When it rings, each selected user gets a private shortlink.")
          : "Standard alarms stop or snooze from this panel.";
    }

    $$(".ring-elapsed[data-ts]").forEach((el) => {
      el.textContent = durationText(now - Number(el.dataset.ts));
    });
  }

  // ------------------------------------------------------------------ bind
  function bindUI() {
    $$(".tab").forEach((tab) => tab.addEventListener("click", () => setView(tab.dataset.view)));

    $("#new-alarm").addEventListener("click", () => openAlarmDialog(null));
    $("#alarms-empty").addEventListener("click", (event) => {
      if (event.target.closest('[data-action="new-alarm"]')) openAlarmDialog(null);
    });
    $("#alarms").addEventListener("click", (event) => {
      const btn = event.target.closest("[data-action]");
      if (!btn) return;
      const id = btn.dataset.id;
      if (btn.dataset.action === "toggle") {
        const card = btn.closest(".alarm-card");
        toggleAlarm(id, card.classList.contains("off"));
      } else if (btn.dataset.action === "ring") {
        ringNow(id);
      } else if (btn.dataset.action === "edit") {
        const alarm = findAlarm(id);
        if (alarm) openAlarmDialog(alarm);
      } else if (btn.dataset.action === "link") {
        const alarm = findAlarm(id);
        if (alarm) openLinkDialog(alarm);
      } else if (btn.dataset.action === "skip") {
        skipAlarm(id, btn.dataset.skip === "1");
      }
    });

    $("#ring-dock").addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-action]");
      if (btn) ringAction(btn);
    });

    $("#add-user-form").addEventListener("submit", addUser);
    $("#users").addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-action]");
      if (btn) userAction(btn);
    });
    $("#users").addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        const row = event.target.closest(".user-row");
        const btn = row?.querySelector('[data-action="save"]');
        if (btn) { event.preventDefault(); userAction(btn); }
      }
    });

    $("#alarm-challenge-count").addEventListener("input", updateChallengeOptions);
    $("#alarm-challenge-type").addEventListener("change", () => {
      S.challengePlan = [planValueToDescriptor($("#alarm-challenge-type").value)];
    });
    $("#challenge-plan-list").addEventListener("change", (event) => {
      const row = event.target.closest("[data-plan-index]");
      if (!row) return;
      const index = Number(row.dataset.planIndex);
      S.challengePlan[index] = planValueToDescriptor(event.target.value);
    });
    $("#challenge-plan-list").addEventListener("click", (event) => {
      const btn = event.target.closest("[data-plan-move]");
      if (!btn) return;
      const index = Number(btn.dataset.planIndex);
      const target = btn.dataset.planMove === "up" ? index - 1 : index + 1;
      if (target < 0 || target >= S.challengePlan.length) return;
      [S.challengePlan[index], S.challengePlan[target]] = [S.challengePlan[target], S.challengePlan[index]];
      renderChallengePlan(S.challengePlan.length);
    });
    $("#links-list").addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-link-action]");
      if (btn) linkAction(btn);
    });
    $("#create-all-link").addEventListener("click", () => openLinkEditor("all", null));
    $("#link-edit-form").addEventListener("submit", saveLinkEditor);
    $("#link-edit-delete").addEventListener("click", deleteAllLink);
    $$("[data-close-link-edit]").forEach((btn) => btn.addEventListener("click", closeLinkEditor));
    $("#question-form").addEventListener("submit", saveQuestion);
    $("#question-import-form").addEventListener("submit", importQuestions);
    $("#question-cancel").addEventListener("click", resetQuestionForm);
    $("#question-kind").addEventListener("change", updateQuestionKind);
    updateQuestionKind();
    $("#questions-body").addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-question-action]");
      if (btn) questionAction(btn);
    });

    $("#music-form").addEventListener("submit", uploadMusic);
    $("#music-list").addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-music-action]");
      if (!btn) return;
      const id = Number(btn.closest(".music-item").dataset.id);
      if (btn.dataset.musicAction === "test") testServerMusic(id);
      else if (btn.dataset.musicAction === "stop") stopServerMusic(id);
      else if (btn.dataset.musicAction === "delete") deleteMusic(id);
    });

    $("#calendar-form").addEventListener("submit", importCalendar);
    $("#calendar-list").addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-calendar-action]");
      if (btn) deleteCalendar(Number(btn.closest(".calendar-item").dataset.id));
    });

    $("#refresh-history").addEventListener("click", refresh);
    $("#settings-form").addEventListener("submit", saveSettings);
    $("#password-form").addEventListener("submit", changePassword);
    $("#audio-test").addEventListener("click", testAudio);
    $("#audio-warning").addEventListener("click", () => setView("settings"));
    $("#refresh-devices").addEventListener("click", refreshDevices);
    $("#setting-audio-device").addEventListener("change", () => {
      S.deviceDirty = true;
      saveAudioDevice();
    });
    $("#volume-form").addEventListener("submit", saveVolumeTarget);

    $$("[data-close-link]").forEach((btn) => btn.addEventListener("click", closeLinkDialog));
    $("#copy-link").addEventListener("click", () => { if (S.currentLink) copyText(S.currentLink); });

    $("#logout").addEventListener("click", async () => {
      try { await api("/api/logout", { method: "POST", body: {} }); } catch (_err) { /* ignore */ }
      showAuth("login");
    });

    // alarm dialog
    $("#alarm-form").addEventListener("submit", saveAlarm);
    $("#alarm-delete").addEventListener("click", deleteAlarm);
    $$("[data-close-dialog]").forEach((btn) => btn.addEventListener("click", closeAlarmDialog));
    $("#day-picker").addEventListener("click", (event) => {
      const btn = event.target.closest(".day");
      if (!btn) return;
      btn.classList.toggle("on");
      if (btn.classList.contains("on")) $("#alarm-once").value = "";
      updateChallengeOptions();
    });
    $("#alarm-once").addEventListener("change", () => {
      if ($("#alarm-once").value) {
        $$("#day-picker .day").forEach((btn) => btn.classList.remove("on"));
      }
      updateChallengeOptions();
    });
    $("#clear-once").addEventListener("click", () => {
      $("#alarm-once").value = "";
      updateChallengeOptions();
    });
    $$('input[name="mode"]').forEach((input) => input.addEventListener("change", updateChallengeOptions));
    $("#alarm-completion").addEventListener("change", updateChallengeOptions);
    $("#alarm-challenge-type").addEventListener("change", updateChallengeOptions);
    $("#alarm-users").addEventListener("change", (event) => {
      const checked = selectedParticipantIds();
      const max = S.data?.limits?.max_alarm_users || 6;
      if (checked.length > max) {
        event.target.checked = false;
        toast(`An alarm can select at most ${max} users.`, "error");
      }
      updateChallengeOptions();
    });
    $("#random-slug").addEventListener("click", () => {
      $("#alarm-slug").value = randomSlug();
      updateSlugPreview();
    });
    $("#alarm-slug").addEventListener("input", updateSlugPreview);

    document.addEventListener("visibilitychange", () => {
      if (!document.hidden && S.data) refresh();
    });
  }

  function bindAuthUI() {
    $("#login-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const error = $("#login-error");
      error.textContent = "";
      const button = $("#login-form button[type=submit]");
      button.disabled = true;
      try {
        await api("/api/login", { method: "POST", body: { password: $("#login-password").value } });
        $("#login-password").value = "";
        await boot();
      } catch (err) {
        error.textContent = err.message;
      } finally { button.disabled = false; }
    });
    $("#setup-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const error = $("#setup-error");
      error.textContent = "";
      const first = $("#setup-password").value;
      const second = $("#setup-password2").value;
      if (first.length < 8) { error.textContent = "Use at least 8 characters."; return; }
      if (first !== second) { error.textContent = "Passwords do not match."; return; }
      const button = $("#setup-form button[type=submit]");
      button.disabled = true;
      try {
        await api("/api/setup", { method: "POST", body: { password: first } });
        $("#setup-password").value = $("#setup-password2").value = "";
        await boot();
      } catch (err) {
        error.textContent = err.message;
      } finally { button.disabled = false; }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    bindAuthUI();
    boot();
  });
})();
