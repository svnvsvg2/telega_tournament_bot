// Глобальное состояние
let currentBracket = {};
let previousBracketMap = {};
let currentMatch = null;
let adminPin = localStorage.getItem("mk1_admin_pin") || "";

let currentInfo = {};

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  checkAdminLogin();
  loadData();

  // Авто-обновление каждые 2 секунды
  setInterval(loadData, 2000);

  // Обработчики кнопок
  document.getElementById("refresh-btn").addEventListener("click", loadData);
  document.getElementById("admin-login-btn").addEventListener("click", handleAdminLogin);
  document.getElementById("generate-bracket-btn").addEventListener("click", generateBracket);
  document.getElementById("reset-bracket-btn").addEventListener("click", resetBracket);
  document.getElementById("close-modal-btn").addEventListener("click", closeModal);
  document.getElementById("save-match-btn").addEventListener("click", saveMatchResult);
  document.getElementById("tv-mode-btn").addEventListener("click", toggleTvMode);

  // Правила и Регламент
  const showRulesBtn = document.getElementById("show-rules-btn");
  if (showRulesBtn) showRulesBtn.addEventListener("click", openRulesModal);

  const closeRulesBtn = document.getElementById("close-rules-btn");
  if (closeRulesBtn) closeRulesBtn.addEventListener("click", closeRulesModal);
});

function toggleTvMode() {
  document.body.classList.toggle("tv-mode");
  const btn = document.getElementById("tv-mode-btn");
  if (document.body.classList.contains("tv-mode")) {
    btn.textContent = "❌ Выйти из Режима Сцены";
  } else {
    btn.textContent = "📺 Режим Сцены";
  }
}

// ---------- Переключение вкладок ----------
function initTabs() {
  const tabs = document.querySelectorAll(".nav-btn");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      const target = tab.getAttribute("data-tab");
      switchTab(target);
    });
  });

  // Кнопки-триггеры внутри страниц
  document.addEventListener("click", (e) => {
    const trigger = e.target.closest(".nav-trigger");
    if (trigger) {
      const target = trigger.getAttribute("data-tab");
      if (target) switchTab(target);
    }
  });
}

function switchTab(targetTab) {
  const tabs = document.querySelectorAll(".nav-btn");
  tabs.forEach(t => {
    if (t.getAttribute("data-tab") === targetTab) {
      t.classList.add("active");
    } else {
      t.classList.remove("active");
    }
  });

  document.querySelectorAll(".tab-content").forEach(c => {
    c.classList.remove("active");
  });

  const activeContent = document.getElementById(`${targetTab}-tab`);
  if (activeContent) activeContent.classList.add("active");
}

// ---------- Загрузка данных ----------
async function loadData() {
  await fetchInfo();
  await fetchBracket();
  await fetchParticipants();
}

async function fetchInfo() {
  try {
    const res = await fetch("/api/info");
    const data = await res.json();
    if (data.ok) {
      currentInfo = data;
      const orgEl = document.getElementById("org-title");
      if (orgEl && data.organization) orgEl.textContent = `${data.organization} ESPORTS`;

      const titleEl = document.getElementById("tourney-title-display");
      if (titleEl && data.tournament) titleEl.textContent = data.tournament;

      const dateEl = document.getElementById("tourney-datetime");
      if (dateEl && data.datetime) dateEl.textContent = data.datetime;

      const playersEl = document.getElementById("tourney-players-count");
      if (playersEl) playersEl.textContent = `${data.confirmed_count} / ${data.max_participants} игроков`;

      const rulesEl = document.getElementById("modal-rules-text");
      if (rulesEl && data.rules) rulesEl.innerHTML = escapeHtml(data.rules).replace(/\n/g, "<br>");
    }
  } catch (err) {
    console.error("Ошибка загрузки информации:", err);
  }
}

function openRulesModal() {
  const modal = document.getElementById("rules-modal");
  if (modal) modal.classList.remove("hidden");
}

function closeRulesModal() {
  const modal = document.getElementById("rules-modal");
  if (modal) modal.classList.add("hidden");
}

async function fetchBracket() {
  try {
    const res = await fetch("/api/bracket");
    const data = await res.json();
    if (data.ok) {
      currentBracket = data.bracket;
      renderBracket(data.bracket);
      if (adminPin && document.getElementById("admin-tab").classList.contains("active")) {
        renderAdminMatches(data.bracket);
      }
    }
  } catch (err) {
    console.error("Ошибка загрузки сетки:", err);
  }
}

async function fetchParticipants() {
  try {
    const res = await fetch("/api/participants");
    const data = await res.json();
    if (data.ok) {
      allParticipantsList = data.participants || [];
      renderParticipants(data.participants);
    }
  } catch (err) {
    console.error("Ошибка загрузки участников:", err);
  }
}

// ---------- Отрисовка Турнирной Сетки ----------
function renderBracket(bracket) {
  if (!bracket) return;

  // 1. Верхняя сетка
  if (bracket.winners) {
    for (let r = 1; r <= 4; r++) {
      const roundEl = document.getElementById(`winners-round-${r}`);
      if (roundEl) renderMatchesList(roundEl, bracket.winners[r] || []);
    }
  }

  // 2. Сетка Лузеров
  if (bracket.losers) {
    for (let r = 1; r <= 6; r++) {
      const roundEl = document.getElementById(`losers-round-${r}`);
      if (roundEl) renderMatchesList(roundEl, bracket.losers[r] || []);
    }
  }

  // 3. Гранд-Финал
  const grandEl = document.getElementById("grand-final-matches");
  if (grandEl && bracket.grand_final) {
    renderMatchesList(grandEl, bracket.grand_final);
  }

  // 4. Сброс Сетки (Bracket Reset)
  const resetEl = document.getElementById("reset-final-matches");
  if (resetEl && bracket.reset) {
    renderMatchesList(resetEl, bracket.reset);
  }
}

function renderMatchesList(roundEl, matches) {
  matches.forEach(m => {
    const matchKey = `match_${m.id}`;
    const prev = previousBracketMap[matchKey];

    const hasChanged = prev && (
      prev.score1 !== m.score1 ||
      prev.score2 !== m.score2 ||
      prev.status !== m.status ||
      prev.winner_slot !== m.winner_slot ||
      prev.player1_name !== m.player1_name ||
      prev.player2_name !== m.player2_name
    );

    let matchCard = document.getElementById(`card-match-${m.id}`);
    if (!matchCard) {
      matchCard = document.createElement("div");
      matchCard.id = `card-match-${m.id}`;
      roundEl.appendChild(matchCard);
    }

    matchCard.className = `match-card status-${m.status} ${hasChanged ? "score-updated" : ""}`;
    matchCard.onclick = () => {
      if (adminPin) openMatchModal(m);
    };

    const p1Winner = m.winner_slot === 1 ? "winner" : "";
    const p2Winner = m.winner_slot === 2 ? "winner" : "";

    let statusBadge = "";
    if (m.status === "live") statusBadge = '<span class="match-status-badge live">🔴 LIVE</span>';
    else if (m.status === "completed") statusBadge = '<span class="match-status-badge completed">✅ Завершён</span>';
    else if (m.status === "not_needed") statusBadge = '<span class="match-status-badge">🚫 Не требуется</span>';
    else statusBadge = '<span class="match-status-badge">⏳ Ожидает</span>';

    matchCard.innerHTML = `
      <div class="match-card-header">
        <span>Матч #${m.id}</span>
        ${statusBadge}
      </div>
      <div class="player-slot ${p1Winner}">
        <div class="player-info">
          <span class="player-name">${escapeHtml(m.player1_name || 'TBD')}</span>
          <span class="player-nick">${escapeHtml(m.player1_nickname || '')}</span>
        </div>
        <span class="player-score">${m.score1}</span>
      </div>
      <div class="player-slot ${p2Winner}">
        <div class="player-info">
          <span class="player-name">${escapeHtml(m.player2_name || 'TBD')}</span>
          <span class="player-nick">${escapeHtml(m.player2_nickname || '')}</span>
        </div>
        <span class="player-score">${m.score2}</span>
      </div>
    `;

    previousBracketMap[matchKey] = { ...m };
  });
}


// ---------- Отрисовка Участников ----------
function renderParticipants(participants) {
  const container = document.getElementById("participants-list");
  const countBadge = document.getElementById("participants-count");

  countBadge.textContent = `${participants.length} игроков`;
  container.innerHTML = "";

  if (participants.length === 0) {
    container.innerHTML = "<p class='info-text'>Участники ещё не зарегистрированы через бота.</p>";
    return;
  }

  participants.forEach(p => {
    const card = document.createElement("div");
    card.className = "participant-card";

    const initial = p.name ? p.name.charAt(0).toUpperCase() : "P";
    const confirmedBadge = p.confirmed ? "✅ Подтверждён" : "⏳ Ожидает";

    card.innerHTML = `
      <div class="avatar-icon">${initial}</div>
      <div>
        <div style="font-weight: 700;">${escapeHtml(p.name)}</div>
        <div style="font-size: 13px; color: var(--gold-primary);">🎮 ${escapeHtml(p.nickname)}</div>
        <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Telegram: @${escapeHtml(p.username || 'скрыт')} • ${confirmedBadge}</div>
      </div>
    `;
    container.appendChild(card);
  });
}

let adminAuth = JSON.parse(localStorage.getItem("mk1_admin_auth") || "null") || (adminPin ? { login: "admin", password: adminPin } : null);

// ---------- Авторизация и Роутинг /admin ----------
function checkAdminRoute() {
  if (window.location.pathname.startsWith("/admin") || window.location.hash === "#admin") {
    switchTab("admin");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  checkAdminLogin();
  checkAdminRoute();
  loadData();

  // Авто-обновление каждые 2 секунды
  setInterval(loadData, 2000);

  // Обработчики кнопок
  document.getElementById("refresh-btn").addEventListener("click", loadData);
  document.getElementById("admin-login-btn").addEventListener("click", handleAdminLogin);
  document.getElementById("generate-bracket-btn").addEventListener("click", generateBracket);
  document.getElementById("reset-bracket-btn").addEventListener("click", resetBracket);

  const seedTestBtn = document.getElementById("seed-test-btn");
  if (seedTestBtn) seedTestBtn.addEventListener("click", seedTestPlayers);

  document.getElementById("close-modal-btn").addEventListener("click", closeModal);
  document.getElementById("save-match-btn").addEventListener("click", saveMatchResult);
  document.getElementById("tv-mode-btn").addEventListener("click", toggleTvMode);

  // Правила и Регламент
  const showRulesBtn = document.getElementById("show-rules-btn");
  if (showRulesBtn) showRulesBtn.addEventListener("click", openRulesModal);

  const closeRulesBtn = document.getElementById("close-rules-btn");
  if (closeRulesBtn) closeRulesBtn.addEventListener("click", closeRulesModal);
});

// ---------- Админ-Авторизация (Логин + Пароль) ----------
async function handleAdminLogin() {
  const loginInput = document.getElementById("admin-login-input").value.trim();
  const passwordInput = document.getElementById("admin-password-input").value.trim();
  const errorEl = document.getElementById("login-error");

  try {
    const res = await fetch("/api/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ login: loginInput, password: passwordInput, pin: passwordInput })
    });
    const data = await res.json();

    if (data.ok) {
      adminAuth = { login: loginInput, password: passwordInput };
      adminPin = passwordInput;
      localStorage.setItem("mk1_admin_auth", JSON.stringify(adminAuth));
      localStorage.setItem("mk1_admin_pin", passwordInput);
      checkAdminLogin();
      loadData();
    } else {
      errorEl.textContent = data.message || "Неверный логин или пароль";
      errorEl.classList.remove("hidden");
    }
  } catch (err) {
    errorEl.textContent = "Ошибка подключения к серверу";
    errorEl.classList.remove("hidden");
  }
}

function checkAdminLogin() {
  const loginCard = document.getElementById("admin-login-card");
  const panelContent = document.getElementById("admin-panel-content");
  const adminBadge = document.getElementById("admin-badge");

  if (adminAuth) {
    loginCard.classList.add("hidden");
    panelContent.classList.remove("hidden");
    adminBadge.classList.remove("hidden");
  } else {
    loginCard.classList.remove("hidden");
    panelContent.classList.add("hidden");
    adminBadge.classList.add("hidden");
  }
}

// ---------- Тестовый Режим & Сетка ----------
async function seedTestPlayers() {
  if (!confirm("Заполнить турнир 16 тестовыми игроками и сформировать сетку Double Elimination?")) return;

  try {
    const payload = adminAuth || { pin: adminPin };
    const res = await fetch("/api/admin/seed_test_players", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    alert(data.message);
    loadData();
  } catch (err) {
    alert("Ошибка при вызове тестового режима");
  }
}

async function generateBracket() {
  if (!confirm("Сформировать турнирную сетку на основе участников из Telegram бота?")) return;

  try {
    const payload = adminAuth || { pin: adminPin };
    payload.shuffle = true;
    const res = await fetch("/api/admin/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    alert(data.message);
    loadData();
  } catch (err) {
    alert("Ошибка соединения");
  }
}

async function resetBracket() {
  if (!confirm("Вы уверены, что хотите сбросить сетку?")) return;

  try {
    const payload = adminAuth || { pin: adminPin };
    const res = await fetch("/api/admin/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    alert(data.message);
    loadData();
  } catch (err) {
    alert("Ошибка соединения");
  }
}

let allParticipantsList = [];

// ---------- Редактирование Матча в Модалке ----------
function openMatchModal(m) {
  currentMatch = { ...m };
  document.getElementById("modal-match-id").textContent = `#${m.id}`;

  document.getElementById("modal-p1-name-input").value = m.player1_name || "";
  document.getElementById("modal-p1-nick-input").value = m.player1_nickname || "";
  document.getElementById("modal-p2-name-input").value = m.player2_name || "";
  document.getElementById("modal-p2-nick-input").value = m.player2_nickname || "";

  const p1Select = document.getElementById("modal-p1-select");
  const p2Select = document.getElementById("modal-p2-select");

  p1Select.innerHTML = '<option value="">-- Выбрать из участников --</option>';
  p2Select.innerHTML = '<option value="">-- Выбрать из участников --</option>';

  allParticipantsList.forEach(p => {
    const opt1 = document.createElement("option");
    opt1.value = JSON.stringify({ name: p.name, nickname: p.nickname });
    opt1.textContent = `${p.name} (${p.nickname})`;
    p1Select.appendChild(opt1);

    const opt2 = document.createElement("option");
    opt2.value = JSON.stringify({ name: p.name, nickname: p.nickname });
    opt2.textContent = `${p.name} (${p.nickname})`;
    p2Select.appendChild(opt2);
  });

  document.getElementById("modal-score1").textContent = m.score1;
  document.getElementById("modal-score2").textContent = m.score2;
  document.getElementById("modal-status-select").value = m.status;

  document.getElementById("match-modal").classList.remove("hidden");
}

function onSelectPlayer(playerNum) {
  const select = document.getElementById(`modal-p${playerNum}-select`);
  if (!select.value) return;
  try {
    const p = JSON.parse(select.value);
    document.getElementById(`modal-p${playerNum}-name-input`).value = p.name || "";
    document.getElementById(`modal-p${playerNum}-nick-input`).value = p.nickname || "";
  } catch (e) {}
}

function closeModal() {
  document.getElementById("match-modal").classList.add("hidden");
  currentMatch = null;
}

function adjustScore(playerNum, delta) {
  if (!currentMatch) return;
  if (playerNum === 1) {
    currentMatch.score1 = Math.max(0, currentMatch.score1 + delta);
    document.getElementById("modal-score1").textContent = currentMatch.score1;
  } else {
    currentMatch.score2 = Math.max(0, currentMatch.score2 + delta);
    document.getElementById("modal-score2").textContent = currentMatch.score2;
  }
}

function selectWinner(playerNum) {
  if (!currentMatch) return;
  currentMatch.winner_slot = playerNum;
  currentMatch.status = "completed";
  document.getElementById("modal-status-select").value = "completed";
  saveMatchResult();
}

async function saveMatchResult() {
  if (!currentMatch) return;

  const status = document.getElementById("modal-status-select").value;
  const p1Name = document.getElementById("modal-p1-name-input").value.trim();
  const p1Nick = document.getElementById("modal-p1-nick-input").value.trim();
  const p2Name = document.getElementById("modal-p2-name-input").value.trim();
  const p2Nick = document.getElementById("modal-p2-nick-input").value.trim();

  const payload = adminAuth ? { ...adminAuth } : { pin: adminPin };
  payload.match_id = currentMatch.id;
  payload.score1 = currentMatch.score1;
  payload.score2 = currentMatch.score2;
  payload.status = status;
  payload.winner_slot = currentMatch.winner_slot || 0;
  payload.player1_name = p1Name;
  payload.player1_nickname = p1Nick;
  payload.player2_name = p2Name;
  payload.player2_nickname = p2Nick;

  try {
    const res = await fetch("/api/admin/match", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.ok) {
      closeModal();
      loadData();
    } else {
      alert(data.message || "Ошибка сохранения");
    }
  } catch (err) {
    alert("Ошибка соединения при сохранении");
  }
}

function renderAdminMatches(bracket) {
  const container = document.getElementById("admin-matches-list");
  if (!container) return;
  container.innerHTML = "<h3>Список всех матчей сетки</h3>";

  const allMatches = [];
  if (bracket.winners) {
    for (let r in bracket.winners) allMatches.push(...bracket.winners[r]);
  }
  if (bracket.losers) {
    for (let r in bracket.losers) allMatches.push(...bracket.losers[r]);
  }
  if (bracket.grand_final) allMatches.push(...bracket.grand_final);
  if (bracket.reset) allMatches.push(...bracket.reset);

  allMatches.forEach(m => {
    const div = document.createElement("div");
    div.className = "bracket-controls";
    div.style.cursor = "pointer";
    div.onclick = () => openMatchModal(m);

    let tag = "Bo1";
    if (m.bracket_type === "grand_final" || m.bracket_type === "reset") tag = "Bo5";

    let label = `Матч #${m.id}`;
    if (m.bracket_type === "winners") label += ` (WB Раунд ${m.round} - ${tag})`;
    else if (m.bracket_type === "losers") label += ` (LB Раунд ${m.round} - ${tag})`;
    else if (m.bracket_type === "grand_final") label += ` (👑 Гранд-Финал - ${tag})`;
    else if (m.bracket_type === "reset") label += ` (🔥 Сброс Сетки - ${tag})`;

    div.innerHTML = `
      <div>
        <strong>${label}</strong>: 
        ${escapeHtml(m.player1_name || 'TBD')} vs ${escapeHtml(m.player2_name || 'TBD')}
      </div>
      <div>
        <span class="score-val" style="font-size: 16px;">${m.score1} : ${m.score2}</span>
        <button class="btn btn-secondary" style="margin-left: 12px; padding: 4px 10px; font-size: 12px;">Изменить</button>
      </div>
    `;
    container.appendChild(div);
  });
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
