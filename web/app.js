// ==========================================================================
// DARACYBER ESPORTS — MK1 TOURNAMENT SINGLE EVENT ENGINE (OPTIMIZED)
// ==========================================================================

const DEFAULT_BOT_URL = "https://t.me/comp_games_lovers_bot";
const DEFAULT_BOT_USERNAME = "comp_games_lovers_bot";

let currentBracket = {};
let previousBracketHash = "";
let previousParticipantsHash = "";
let currentMatch = null;
let allParticipantsList = [];
let filteredParticipants = [];
let currentFilterStatus = "all";
let currentSearchQuery = "";
let currentInfo = {
  bot_url: DEFAULT_BOT_URL,
  bot_username: DEFAULT_BOT_USERNAME
};

// Проверка сохранённой авторизации админа
let adminAuth = JSON.parse(localStorage.getItem("mk1_admin_auth") || "null");

// Таймер адаптивного опроса
let pollingTimer = null;

document.addEventListener("DOMContentLoaded", () => {
  initRouting();
  
  // Первичная полная загрузка
  fetchInfo();
  loadData();

  // Адаптивный опрос: 3 сек когда вкладка активна, 10 сек когда свернута
  startAdaptivePolling();

  document.addEventListener("visibilitychange", () => {
    startAdaptivePolling();
    if (!document.hidden) {
      loadData();
    }
  });

  // Клавиша Escape для закрытия модальных окон или выхода из режима сцены
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      const modal = document.getElementById("match-modal");
      if (modal && !modal.classList.contains("hidden")) {
        closeModal();
      } else if (document.body.classList.contains("stage-mode")) {
        toggleStageMode();
      }
    }
  });
});

function startAdaptivePolling() {
  if (pollingTimer) clearInterval(pollingTimer);
  const interval = document.hidden ? 10000 : 3000;
  pollingTimer = setInterval(loadData, interval);
}

// ==========================================================================
// НАВИГАЦИЯ
// ==========================================================================
function initRouting() {
  const path = window.location.pathname.toLowerCase().replace(/\/$/, "");

  if (path === "/admin" || path.startsWith("/admin")) {
    showAdmin();
  } else {
    showTournament();
  }

  if (adminAuth) {
    applyAdminState();
  }
}

function showTournament() {
  document.querySelectorAll(".page-view").forEach(p => p.classList.remove("active"));
  const target = document.getElementById("page-tournament");
  if (target) target.classList.add("active");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function showAdmin() {
  document.querySelectorAll(".page-view").forEach(p => p.classList.remove("active"));
  const target = document.getElementById("page-admin");
  if (target) target.classList.add("active");
  checkAdminState();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function switchTab(tabName) {
  document.querySelectorAll(".main-nav .nav-item").forEach(btn => btn.classList.remove("active"));
  const navBtn = document.getElementById(`nav-btn-${tabName}`);
  if (navBtn) navBtn.classList.add("active");

  document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
  const targetContent = document.getElementById(`tab-content-${tabName}`);
  if (targetContent) targetContent.classList.add("active");

  showTournament();
}

function toggleStageMode() {
  document.body.classList.toggle("stage-mode");
  const btn = document.getElementById("stage-mode-btn");
  if (document.body.classList.contains("stage-mode")) {
    btn.innerHTML = '<i class="fas fa-compress"></i> Выйти со Сцены';
  } else {
    btn.innerHTML = '<i class="fas fa-expand"></i> Режим Сцены';
  }
}

// ==========================================================================
// ЗАГРУЗКА ДАННЫХ С СЕРВЕРА (С ДИФФ-ПРОВЕРКОЙ)
// ==========================================================================
async function loadData() {
  await Promise.all([
    fetchBracket(),
    fetchParticipants()
  ]);
}

async function fetchInfo() {
  try {
    const res = await fetch("/api/info");
    const data = await res.json();
    if (data.ok) {
      currentInfo = {
        ...data,
        bot_url: data.bot_url || DEFAULT_BOT_URL,
        bot_username: data.bot_username || DEFAULT_BOT_USERNAME
      };
      updateInfoUI(currentInfo);
    }
  } catch (err) {
    console.error("Ошибка при получении информации о турнире:", err);
  }
}

function updateInfoUI(data) {
  const navOrg = document.getElementById("nav-org-name");
  if (navOrg && data.organization) navOrg.textContent = data.organization;

  const footerOrg = document.getElementById("footer-org-name");
  if (footerOrg && data.organization) footerOrg.textContent = data.organization;

  const detailTitle = document.getElementById("detail-tourney-title");
  if (detailTitle && data.tournament) detailTitle.textContent = data.tournament;

  const detailDate = document.getElementById("detail-tourney-date");
  if (detailDate && data.datetime) detailDate.innerHTML = `<i class="far fa-clock"></i> ${data.datetime}`;

  const countStr = `${data.confirmed_count} / ${data.max_participants}`;

  const detailPill = document.getElementById("detail-tourney-registered-pill");
  if (detailPill) detailPill.innerHTML = `<i class="fas fa-user-check"></i> ${countStr} Участников`;

  const navCount = document.getElementById("nav-participants-count");
  if (navCount) navCount.textContent = data.confirmed_count;

  const rulesEl = document.getElementById("rules-content-display");
  if (rulesEl && data.rules) {
    rulesEl.innerHTML = escapeHtml(data.rules).replace(/\n/g, "<br>");
  }

  const botUrl = data.bot_url || DEFAULT_BOT_URL;
  const botUser = data.bot_username || DEFAULT_BOT_USERNAME;

  const detailTg = document.getElementById("detail-tg-btn");
  if (detailTg) {
    detailTg.href = botUrl;
    detailTg.innerHTML = `<i class="fab fa-telegram-plane"></i> Регистрация в Telegram (@${botUser})`;
  }

  const alertTg = document.getElementById("alert-bot-link");
  if (alertTg) {
    alertTg.href = botUrl;
    alertTg.textContent = `@${botUser}`;
  }

  const footerTg = document.getElementById("footer-tg-link");
  if (footerTg) footerTg.href = botUrl;
}

async function fetchBracket() {
  try {
    const res = await fetch("/api/bracket");
    const data = await res.json();
    if (data.ok) {
      const newHash = JSON.stringify(data.bracket);
      // Перерисовываем DOM только если данные реально изменились
      if (newHash !== previousBracketHash) {
        previousBracketHash = newHash;
        currentBracket = data.bracket || {};
        renderBracket(currentBracket);
        if (adminAuth && document.getElementById("page-admin").classList.contains("active")) {
          renderAdminMatches(currentBracket);
        }
      }
    }
  } catch (err) {
    console.error("Ошибка при получении турнирной сетки:", err);
  }
}

async function fetchParticipants() {
  try {
    const res = await fetch("/api/participants");
    const data = await res.json();
    if (data.ok) {
      const newHash = JSON.stringify(data.participants);
      // Перерисовываем участников только при реальном изменении списка
      if (newHash !== previousParticipantsHash) {
        previousParticipantsHash = newHash;
        allParticipantsList = data.participants || [];
        applyParticipantsFilter();
      }
    }
  } catch (err) {
    console.error("Ошибка при получении участников:", err);
  }
}

// ==========================================================================
// ОТРИСОВКА ТУРНИРНОЙ СЕТКИ (DOUBLE ELIMINATION)
// ==========================================================================
function renderBracket(bracket) {
  if (!bracket) return;

  if (bracket.winners) {
    for (let r = 1; r <= 4; r++) {
      const roundEl = document.getElementById(`winners-round-${r}`);
      if (roundEl) renderMatchesColumn(roundEl, bracket.winners[r] || []);
    }
  }

  if (bracket.losers) {
    for (let r = 1; r <= 6; r++) {
      const roundEl = document.getElementById(`losers-round-${r}`);
      if (roundEl) renderMatchesColumn(roundEl, bracket.losers[r] || []);
    }
  }

  const grandEl = document.getElementById("grand-final-matches");
  if (grandEl && bracket.grand_final) {
    renderMatchesColumn(grandEl, bracket.grand_final);
  }

  const resetEl = document.getElementById("reset-final-matches");
  if (resetEl && bracket.reset) {
    renderMatchesColumn(resetEl, bracket.reset);
  }
}

function renderMatchesColumn(container, matches) {
  matches.forEach(m => {
    let card = document.getElementById(`match-node-${m.id}`);
    if (!card) {
      card = document.createElement("div");
      card.id = `match-node-${m.id}`;
      container.appendChild(card);
    }

    card.className = `match-card status-${m.status}`;
    card.style.cursor = adminAuth ? "pointer" : "default";
    if (adminAuth) {
      card.title = "Нажмите для редактирования матча";
    }

    card.onclick = () => {
      if (adminAuth) openMatchModal(m);
    };

    const p1Win = m.winner_slot === 1 ? "winner" : "";
    const p2Win = m.winner_slot === 2 ? "winner" : "";

    const isBronzeMatch = (m.id === 29 || (m.bracket_type === "losers" && m.round === 6));
    const matchHeaderLabel = isBronzeMatch ? `МАТЧ #29 • 🥉 ЗА 3-Е МЕСТО` : `МАТЧ #${m.id}`;

    let statusHtml = "";
    if (m.status === "live") {
      statusHtml = `<span class="match-status-badge live">🔴 LIVE</span>`;
    } else if (m.status === "completed") {
      statusHtml = `<span class="match-status-badge completed">✅ Завершён</span>`;
    } else if (m.status === "not_needed") {
      statusHtml = `<span class="match-status-badge">🚫 Не требуется</span>`;
    } else if (isBronzeMatch) {
      statusHtml = `<span class="match-status-badge bronze-badge">🥉 Бронза / Финал</span>`;
    } else {
      statusHtml = `<span class="match-status-badge">⏳ Ожидание</span>`;
    }

    card.innerHTML = `
      <div class="match-card-header">
        <span>${matchHeaderLabel}</span>
        ${statusHtml}
      </div>
      <div class="player-slot ${p1Win}">
        <div class="player-info">
          <span class="player-name">${escapeHtml(m.player1_name || 'TBD')}</span>
          <span class="player-nick">${escapeHtml(m.player1_nickname || '')}</span>
        </div>
        <span class="player-score">${m.score1}</span>
      </div>
      <div class="player-slot ${p2Win}">
        <div class="player-info">
          <span class="player-name">${escapeHtml(m.player2_name || 'TBD')}</span>
          <span class="player-nick">${escapeHtml(m.player2_nickname || '')}</span>
        </div>
        <span class="player-score">${m.score2}</span>
      </div>
    `;
  });
}

// ==========================================================================
// УЧАСТНИКИ: ПОИСК И ФИЛЬТРАЦИЯ
// ==========================================================================
function onSearchParticipants() {
  const query = document.getElementById("participant-search").value.trim().toLowerCase();
  currentSearchQuery = query;
  applyParticipantsFilter();
}

function filterParticipantStatus(status, element) {
  currentFilterStatus = status;
  document.querySelectorAll(".filter-buttons-group .filter-btn").forEach(btn => btn.classList.remove("active"));
  if (element) {
    element.classList.add("active");
  }
  applyParticipantsFilter();
}

function applyParticipantsFilter() {
  const container = document.getElementById("participants-list-container");
  if (!container) return;

  const total = allParticipantsList.length;
  const confirmed = allParticipantsList.filter(p => p.confirmed).length;
  const pending = total - confirmed;

  const countAll = document.getElementById("count-all");
  if (countAll) countAll.textContent = total;
  const countConf = document.getElementById("count-confirmed");
  if (countConf) countConf.textContent = confirmed;
  const countPend = document.getElementById("count-pending");
  if (countPend) countPend.textContent = pending;

  filteredParticipants = allParticipantsList.filter(p => {
    if (currentFilterStatus === "confirmed" && !p.confirmed) return false;
    if (currentFilterStatus === "pending" && p.confirmed) return false;

    if (currentSearchQuery) {
      const matchName = (p.name || "").toLowerCase().includes(currentSearchQuery);
      const matchNick = (p.nickname || "").toLowerCase().includes(currentSearchQuery);
      const matchUser = (p.username || "").toLowerCase().includes(currentSearchQuery);
      return matchName || matchNick || matchUser;
    }
    return true;
  });

  renderParticipantsList(filteredParticipants);
}

function renderParticipantsList(list) {
  const container = document.getElementById("participants-list-container");
  if (!container) return;

  container.innerHTML = "";

  if (list.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--text-muted);">
        <i class="fas fa-search" style="font-size: 32px; margin-bottom: 12px; opacity: 0.5;"></i>
        <p>Участники не найдены по заданным критериям.</p>
      </div>
    `;
    return;
  }

  const fragment = document.createDocumentFragment();
  list.forEach(p => {
    const card = document.createElement("div");
    card.className = "participant-card";

    const initial = (p.name || "P").charAt(0).toUpperCase();
    const isConf = p.confirmed;
    const statusText = isConf ? '<span class="status-badge-confirmed">✅ Подтверждён</span>' : '<span class="status-badge-pending">⏳ Ожидает</span>';

    card.innerHTML = `
      <div class="participant-avatar-glyph">${initial}</div>
      <div class="participant-details">
        <span class="p-name">${escapeHtml(p.name)}</span>
        <span class="p-nick">🎮 ${escapeHtml(p.nickname)}</span>
        <div class="p-meta">
          <span>@${escapeHtml(p.username || 'скрыт')}</span>
          <span>•</span>
          ${statusText}
        </div>
      </div>
    `;

    fragment.appendChild(card);
  });
  container.appendChild(fragment);
}

// ==========================================================================
// АДМИН-ПАНЕЛЬ
// ==========================================================================
function applyAdminState() {
  const badge = document.getElementById("admin-status-indicator");
  const hint = document.getElementById("admin-bracket-hint");
  if (adminAuth) {
    if (badge) badge.classList.remove("hidden");
    if (hint) hint.classList.remove("hidden");
  } else {
    if (badge) badge.classList.add("hidden");
    if (hint) hint.classList.add("hidden");
  }
}

function checkAdminState() {
  const authView = document.getElementById("admin-auth-view");
  const dashView = document.getElementById("admin-dashboard-view");

  if (adminAuth) {
    if (authView) authView.classList.add("hidden");
    if (dashView) dashView.classList.remove("hidden");
    applyAdminState();
    renderAdminMatches(currentBracket);
  } else {
    if (authView) authView.classList.remove("hidden");
    if (dashView) dashView.classList.add("hidden");
    applyAdminState();
  }
}

async function executeAdminLogin() {
  const input = document.getElementById("admin-passcode-input");
  const errorEl = document.getElementById("admin-auth-error");
  const passcode = input.value.trim();

  if (!passcode) {
    errorEl.textContent = "Пожалуйста, введите пароль (4321)";
    errorEl.classList.remove("hidden");
    return;
  }

  try {
    const res = await fetch("/api/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: passcode, pin: passcode, login: "admin" })
    });
    const data = await res.json();

    if (data.ok) {
      adminAuth = { password: passcode, pin: passcode, login: "admin" };
      localStorage.setItem("mk1_admin_auth", JSON.stringify(adminAuth));
      input.value = "";
      errorEl.classList.add("hidden");
      checkAdminState();
      loadData();
    } else {
      errorEl.textContent = data.message || "Неверный пароль администратора";
      errorEl.classList.remove("hidden");
    }
  } catch (err) {
    errorEl.textContent = "Ошибка соединения с сервером";
    errorEl.classList.remove("hidden");
  }
}

function logoutAdmin() {
  adminAuth = null;
  localStorage.removeItem("mk1_admin_auth");
  checkAdminState();
  loadData();
}

async function seedTestPlayers() {
  if (!confirm("Заполнить турнир 16 тестовыми игроками и автоматически сформировать сетку Double Elimination?")) return;

  try {
    const res = await fetch("/api/admin/seed_test_players", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(adminAuth)
    });
    const data = await res.json();
    alert(data.message || "Тестовый турнир сформирован!");
    previousBracketHash = "";
    previousParticipantsHash = "";
    fetchInfo();
    loadData();
  } catch (err) {
    alert("Ошибка запроса к серверу");
  }
}

async function generateBracket() {
  if (!confirm("Сформировать турнирную сетку на основе участников из Telegram бота?")) return;

  try {
    const payload = { ...adminAuth, shuffle: true };
    const res = await fetch("/api/admin/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    alert(data.message || "Сетка успешно создана!");
    previousBracketHash = "";
    loadData();
  } catch (err) {
    alert("Ошибка запроса к серверу");
  }
}

async function resetBracket() {
  if (!confirm("Вы действительно хотите полностью сбросить турнирную сетку?")) return;

  try {
    const res = await fetch("/api/admin/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(adminAuth)
    });
    const data = await res.json();
    alert(data.message || "Сетка очищена!");
    previousBracketHash = "";
    loadData();
  } catch (err) {
    alert("Ошибка запроса к серверу");
  }
}

// ==========================================================================
// ИМПОРТ СПИСКА ИГРОКОВ
// ==========================================================================
async function importPlayersList() {
  const textarea = document.getElementById("import-players-textarea");
  const resultMsg = document.getElementById("import-result-msg");
  const text = textarea.value.trim();

  if (!text) {
    resultMsg.textContent = "⚠️ Введите список игроков!";
    resultMsg.className = "import-result-msg error";
    return;
  }

  if (!confirm("Импортировать список игроков и сформировать турнирную сетку? Текущие участники будут заменены.")) return;

  resultMsg.textContent = "⏳ Импорт...";
  resultMsg.className = "import-result-msg";

  try {
    const payload = { ...adminAuth, players_text: text };
    const res = await fetch("/api/admin/import_players", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (data.ok) {
      resultMsg.textContent = `✅ ${data.message}`;
      resultMsg.className = "import-result-msg success";
      previousBracketHash = "";
      previousParticipantsHash = "";
      fetchInfo();
      loadData();
    } else {
      resultMsg.textContent = `❌ ${data.message}`;
      resultMsg.className = "import-result-msg error";
    }
  } catch (err) {
    resultMsg.textContent = "❌ Ошибка соединения с сервером";
    resultMsg.className = "import-result-msg error";
  }
}

// ==========================================================================
// МОДАЛЬНОЕ ОКНО РЕДАКТИРОВАНИЯ МАТЧА
// ==========================================================================
function openMatchModal(m) {
  currentMatch = { ...m };
  
  const idEl = document.getElementById("modal-match-id");
  if (idEl) idEl.textContent = `#${m.id}`;

  const roundEl = document.getElementById("modal-match-round");
  if (roundEl) {
    let typeName = "Winners Bracket";
    if (m.id === 29 || (m.bracket_type === "losers" && m.round === 6)) {
      typeName = "🥉 МАТЧ ЗА 3-Е МЕСТО / Финал LB";
    } else if (m.bracket_type === "losers") {
      typeName = "Losers Bracket";
    } else if (m.bracket_type === "grand_final") {
      typeName = "👑 Гранд-Финал (Bo5)";
    } else if (m.bracket_type === "reset") {
      typeName = "🔥 Сброс Сетки (Bo5)";
    }
    roundEl.textContent = `${typeName} (Раунд ${m.round})`;
  }

  document.getElementById("modal-p1-name-input").value = m.player1_name || "";
  document.getElementById("modal-p1-nick-input").value = m.player1_nickname || "";
  document.getElementById("modal-p2-name-input").value = m.player2_name || "";
  document.getElementById("modal-p2-nick-input").value = m.player2_nickname || "";

  const p1Select = document.getElementById("modal-p1-select");
  const p2Select = document.getElementById("modal-p2-select");

  p1Select.innerHTML = '<option value="">-- Выбрать участника --</option>';
  p2Select.innerHTML = '<option value="">-- Выбрать участника --</option>';

  allParticipantsList.forEach(p => {
    const val = JSON.stringify({ name: p.name, nickname: p.nickname });
    
    const o1 = document.createElement("option");
    o1.value = val;
    o1.textContent = `${p.name} (${p.nickname})`;
    p1Select.appendChild(o1);

    const o2 = document.createElement("option");
    o2.value = val;
    o2.textContent = `${p.name} (${p.nickname})`;
    p2Select.appendChild(o2);
  });

  document.getElementById("modal-score1").textContent = m.score1;
  document.getElementById("modal-score2").textContent = m.score2;
  document.getElementById("modal-status-select").value = m.status;

  const modal = document.getElementById("match-modal");
  if (modal) modal.classList.remove("hidden");
}

function onSelectPlayer(num) {
  const select = document.getElementById(`modal-p${num}-select`);
  if (!select || !select.value) return;
  try {
    const p = JSON.parse(select.value);
    document.getElementById(`modal-p${num}-name-input`).value = p.name || "";
    document.getElementById(`modal-p${num}-nick-input`).value = p.nickname || "";
  } catch (e) {}
}

function closeModal() {
  const modal = document.getElementById("match-modal");
  if (modal) modal.classList.add("hidden");
  currentMatch = null;
}

function adjustScore(num, delta) {
  if (!currentMatch) return;
  if (num === 1) {
    currentMatch.score1 = Math.max(0, currentMatch.score1 + delta);
    document.getElementById("modal-score1").textContent = currentMatch.score1;
  } else {
    currentMatch.score2 = Math.max(0, currentMatch.score2 + delta);
    document.getElementById("modal-score2").textContent = currentMatch.score2;
  }
}

function selectWinner(num) {
  if (!currentMatch) return;
  currentMatch.winner_slot = num;
  currentMatch.status = "completed";
  document.getElementById("modal-status-select").value = "completed";
  saveMatchResult();
}

async function saveMatchResult() {
  if (!currentMatch || !adminAuth) return;

  const status = document.getElementById("modal-status-select").value;
  const p1Name = document.getElementById("modal-p1-name-input").value.trim();
  const p1Nick = document.getElementById("modal-p1-nick-input").value.trim();
  const p2Name = document.getElementById("modal-p2-name-input").value.trim();
  const p2Nick = document.getElementById("modal-p2-nick-input").value.trim();

  const payload = {
    ...adminAuth,
    match_id: currentMatch.id,
    score1: currentMatch.score1,
    score2: currentMatch.score2,
    status: status,
    winner_slot: currentMatch.winner_slot || 0,
    player1_name: p1Name,
    player1_nickname: p1Nick,
    player2_name: p2Name,
    player2_nickname: p2Nick
  };

  try {
    const res = await fetch("/api/admin/match", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.ok) {
      closeModal();
      previousBracketHash = "";
      loadData();
    } else {
      alert(data.message || "Ошибка сохранения матча");
    }
  } catch (err) {
    alert("Ошибка соединения с сервером при сохранении матча");
  }
}

// ==========================================================================
// НАВИГАЦИЯ ПО РАУНДАМ (ДЛЯ МОБИЛЬНЫХ УСТРОЙСТВ И ПЛАНШЕТОВ)
// ==========================================================================
function jumpToRound(treeType, roundNum, btn) {
  const container = document.getElementById(`scroll-container-${treeType}`);
  const targetCol = document.getElementById(`${treeType}-col-${roundNum}`);
  if (!container || !targetCol) return;

  // Обновляем активную кнопку
  const navContainer = document.getElementById(`${treeType}-round-nav`);
  if (navContainer) {
    navContainer.querySelectorAll(".round-nav-pill").forEach(b => b.classList.remove("active"));
  }
  if (btn) btn.classList.add("active");

  // Плавная прокрутка к выбранному раунду
  const offset = targetCol.offsetLeft - container.offsetLeft - 8;
  container.scrollTo({ left: offset, behavior: "smooth" });
}

// ==========================================================================
// УПРАВЛЕНИЕ МАТЧАМИ В АДМИНКЕ (ПО СЕТКЕ: WINNERS / LOSERS / FINALS)
// ==========================================================================
let currentAdminCategory = "all";

function filterAdminCategory(cat, btn) {
  currentAdminCategory = cat;
  document.querySelectorAll(".admin-filter-pills .admin-filter-pill").forEach(b => b.classList.remove("active"));
  if (btn) btn.classList.add("active");

  const wBlock = document.getElementById("admin-group-winners");
  const lBlock = document.getElementById("admin-group-losers");
  const fBlock = document.getElementById("admin-group-finals");

  if (wBlock) wBlock.style.display = (cat === "all" || cat === "winners") ? "block" : "none";
  if (lBlock) lBlock.style.display = (cat === "all" || cat === "losers") ? "block" : "none";
  if (fBlock) fBlock.style.display = (cat === "all" || cat === "finals") ? "block" : "none";
}

function renderAdminMatches(bracket) {
  const wContainer = document.getElementById("admin-list-winners");
  const lContainer = document.getElementById("admin-list-losers");
  const fContainer = document.getElementById("admin-list-finals");

  if (!wContainer || !lContainer || !fContainer) return;

  // 1. Верхняя Сетка
  const winnersMatches = [];
  if (bracket.winners) {
    for (let r in bracket.winners) winnersMatches.push(...bracket.winners[r]);
  }
  renderAdminGroupList(wContainer, winnersMatches, "winners");

  // 2. Сетка Лузеров
  const losersMatches = [];
  if (bracket.losers) {
    for (let r in bracket.losers) losersMatches.push(...bracket.losers[r]);
  }
  renderAdminGroupList(lContainer, losersMatches, "losers");

  // 3. Финалы
  const finalsMatches = [];
  if (bracket.grand_final) finalsMatches.push(...bracket.grand_final);
  if (bracket.reset) finalsMatches.push(...bracket.reset);
  renderAdminGroupList(fContainer, finalsMatches, "finals");
}

function renderAdminGroupList(container, matches, type) {
  container.innerHTML = "";

  if (matches.length === 0) {
    container.innerHTML = "<p style='color: var(--text-muted); padding: 10px;'>Матчи в этой категории пока не сформированы.</p>";
    return;
  }

  const fragment = document.createDocumentFragment();
  matches.forEach(m => {
    const row = document.createElement("div");
    row.className = `admin-match-row status-${m.status}`;
    row.onclick = () => openMatchModal(m);

    let stageName = `WB Раунд ${m.round}`;
    if (m.id === 29 || (m.bracket_type === "losers" && m.round === 6)) {
      stageName = `🥉 Матч за 3-е место / Финал LB`;
    } else if (m.bracket_type === "losers") {
      stageName = `LB Раунд ${m.round}`;
    } else if (m.bracket_type === "grand_final") {
      stageName = `👑 Гранд-Финал (Bo5)`;
    } else if (m.bracket_type === "reset") {
      stageName = `🔥 Сброс Сетки (Bo5)`;
    }

    let statusText = "⏳ Ожидание";
    let statusClass = "pending";
    if (m.status === "live") {
      statusText = "🔴 LIVE";
      statusClass = "live";
    } else if (m.status === "completed") {
      statusText = "✅ Завершён";
      statusClass = "completed";
    } else if (m.status === "not_needed") {
      statusText = "🚫 Не требуется";
      statusClass = "not_needed";
    }

    const p1Win = m.winner_slot === 1 ? "win" : "";
    const p2Win = m.winner_slot === 2 ? "win" : "";

    row.innerHTML = `
      <div class="admin-match-header-row">
        <span class="am-id">#${m.id}</span>
        <span class="am-stage">${stageName}</span>
        <span class="am-status badge-${statusClass}">${statusText}</span>
      </div>
      <div class="admin-match-players-box">
        <div class="am-player ${p1Win}">
          <span class="am-name">${escapeHtml(m.player1_name || 'TBD')}</span>
          <span class="am-nick">${escapeHtml(m.player1_nickname ? `(${m.player1_nickname})` : '')}</span>
          <span class="am-score">${m.score1}</span>
        </div>
        <div class="am-player ${p2Win}">
          <span class="am-name">${escapeHtml(m.player2_name || 'TBD')}</span>
          <span class="am-nick">${escapeHtml(m.player2_nickname ? `(${m.player2_nickname})` : '')}</span>
          <span class="am-score">${m.score2}</span>
        </div>
      </div>
      <div class="admin-match-action-hint">
        <i class="fas fa-edit"></i> Нажмите для редактирования
      </div>
    `;

    fragment.appendChild(row);
  });
  container.appendChild(fragment);
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

