const INTERESTS = ["STEM","Research","Technology","Business","Entrepreneurship","Leadership","Community","Writing","Arts","Design","Health","Environment","Public Policy"];
const STATUS_LABELS = {
  planning: "Planning",
  in_progress: "In progress",
  submitted: "Submitted",
  interview: "Interview",
  won: "Won / accepted",
  rejected: "Not selected",
};

const state = {
  user: null,
  page: "discover",
  type: "All",
  query: "",
  sort: "match",
  verifiedOnly: false,
  discoverItems: [],
  stats: {},
  detailId: null,
};

const $ = (id) => document.getElementById(id);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

function esc(value = "") {
  return String(value).replace(/[&<>'"]/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[ch]));
}

function money(value) {
  const n = Number(value || 0);
  return n ? `$${n.toLocaleString()}` : "Experience-based";
}

function formatDate(value) {
  if (!value) return "No deadline";
  const d = new Date(`${value}T12:00:00`);
  return new Intl.DateTimeFormat("en-CA", {month:"short", day:"numeric", year:"numeric"}).format(d);
}

function daysUntil(value) {
  const now = new Date(); now.setHours(12,0,0,0);
  const d = new Date(`${value}T12:00:00`);
  return Math.ceil((d - now) / 86400000);
}

async function api(path, options = {}) {
  const config = {method: options.method || "GET", headers: {"Content-Type":"application/json"}};
  if (options.body !== undefined) config.body = JSON.stringify(options.body);
  const res = await fetch(path, config);
  let data = {};
  try { data = await res.json(); } catch (_) {}
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

function toast(message) {
  const el = $("toast");
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => el.classList.remove("show"), 2200);
}

function showAuth(mode = "login") {
  $("authScreen").classList.remove("hidden");
  $("appScreen").classList.add("hidden");
  setAuthMode(mode);
}

function showApp() {
  $("authScreen").classList.add("hidden");
  $("appScreen").classList.remove("hidden");
  const first = (state.user.name || "A").trim().charAt(0).toUpperCase();
  $("avatar").textContent = first;
  $("sideName").textContent = state.user.name;
  $("sideMeta").textContent = state.user.role === "admin" ? "Administrator" : `${state.user.grade ? `Grade ${state.user.grade}` : "Student"}`;
  $("adminNav").classList.toggle("hidden", state.user.role !== "admin");
  $("discoverTitle").textContent = state.user.role === "admin" ? "Explore the student experience." : `Find your next move, ${state.user.name.split(" ")[0]}.`;
  renderProfileLine();
  navigate(state.user.role === "admin" ? "admin" : "discover");
}

function setAuthMode(mode) {
  const login = mode === "login";
  $("loginTab").classList.toggle("active", login);
  $("registerTab").classList.toggle("active", !login);
  $("loginForm").classList.toggle("hidden", !login);
  $("registerForm").classList.toggle("hidden", login);
}

function selectedInterests(containerId) {
  return $$(`#${containerId} input:checked`).map(x => x.value);
}

function renderProfileLine() {
  if (!state.user) return;
  const bits = [];
  if (state.user.grade) bits.push(`Grade ${state.user.grade}`);
  if (state.user.location) bits.push(state.user.location);
  if (state.user.interests?.length) bits.push(state.user.interests.slice(0, 4).join(" · "));
  $("profileLine").textContent = bits.length ? bits.join("  •  ") : "Complete your profile to improve recommendations.";
}

async function boot() {
  renderInterestChoices();
  try {
    const {user} = await api("/api/me");
    state.user = user;
    if (user) showApp(); else showAuth("login");
  } catch (err) {
    showAuth("login");
    toast(err.message);
  }
}

function renderInterestChoices() {
  const profile = $("profileInterests");
  profile.innerHTML = INTERESTS.map(x => `<label><input type="checkbox" value="${esc(x)}" /> ${esc(x)}</label>`).join("");
}

async function loadDashboardStats() {
  const {stats} = await api("/api/dashboard");
  state.stats = stats;
  $("availableStat").textContent = stats.available;
  $("savedStat").textContent = stats.saved;
  $("applicationsStat").textContent = stats.applications;
  $("dueSoonStat").textContent = stats.due_soon;
  $("savedBadge").textContent = stats.saved;
  $("applicationsBadge").textContent = stats.applications;
}

function cardHTML(o) {
  const days = daysUntil(o.deadline);
  const sourceTag = o.verified ? `<span class="tag verified">✓ Verified</span>` : (o.is_demo ? `<span class="tag demo">Demo</span>` : `<span class="tag">Unverified</span>`);
  const deadlineClass = days >= 0 && days <= 30 ? "soon" : "";
  const tracked = Boolean(o.application);
  return `
    <article class="opp-card" data-card-id="${o.id}">
      <div class="opp-top">
        <div><h3 class="opp-title">${esc(o.title)}</h3><p class="opp-org">${esc(o.org)}</p></div>
        <button class="save-icon ${o.saved ? "saved" : ""}" data-save="${o.id}" type="button" aria-label="${o.saved ? "Remove from saved" : "Save opportunity"}">${o.saved ? "★" : "☆"}</button>
      </div>
      <p class="opp-desc">${esc(o.description || "No description provided.")}</p>
      <div class="tags">
        <span class="tag">${esc(o.type)}</span>
        <span class="tag">${esc(o.location)}</span>
        <span class="tag ${deadlineClass}">${days < 0 ? "Closed" : `Due ${formatDate(o.deadline)}`}</span>
        ${state.user?.role === "student" ? `<span class="tag match">${o.match_score}% match</span>` : ""}
        ${sourceTag}
      </div>
      <div class="opp-footer">
        <span class="value">${money(o.value)}</span>
        <div class="card-actions">
          <button class="details-btn" data-details="${o.id}" type="button">Details</button>
          <button class="track-btn" data-track="${o.id}" type="button">${tracked ? STATUS_LABELS[o.application.status] || "Tracked" : "Track application"}</button>
        </div>
      </div>
    </article>`;
}

async function loadDiscover() {
  await loadDashboardStats();
  const params = new URLSearchParams({sort: state.sort});
  if (state.type !== "All") params.set("type", state.type);
  if (state.query) params.set("q", state.query);
  if (state.verifiedOnly) params.set("verified", "1");
  const data = await api(`/api/opportunities?${params}`);
  state.discoverItems = data.items;
  $("resultCount").textContent = `${data.total} result${data.total === 1 ? "" : "s"}`;
  $("opportunityGrid").innerHTML = data.items.slice(0, 100).map(cardHTML).join("");
  $("discoverEmpty").classList.toggle("hidden", data.items.length > 0);
}

async function loadSaved() {
  await loadDashboardStats();
  const {items} = await api("/api/opportunities?saved=1&sort=deadline");
  $("savedGrid").innerHTML = items.map(cardHTML).join("");
  $("savedEmpty").classList.toggle("hidden", items.length > 0);
}

async function loadApplications() {
  await loadDashboardStats();
  const {items} = await api("/api/opportunities?applications=1&sort=deadline");
  const counts = Object.fromEntries(Object.keys(STATUS_LABELS).map(k => [k, 0]));
  items.forEach(o => counts[o.application?.status] = (counts[o.application?.status] || 0) + 1);
  $("applicationSummary").innerHTML = Object.entries(STATUS_LABELS).map(([key,label]) => `<span class="pipeline-pill">${label}<strong>${counts[key] || 0}</strong></span>`).join("");
  $("applicationList").innerHTML = items.map(o => `
    <article class="application-row" data-application-row="${o.id}">
      <div><h3>${esc(o.title)}</h3><p>${esc(o.org)} • due ${formatDate(o.deadline)}</p></div>
      <select class="status-select" data-app-status="${o.id}">${Object.entries(STATUS_LABELS).map(([key,label]) => `<option value="${key}" ${o.application.status === key ? "selected" : ""}>${label}</option>`).join("")}</select>
      <input class="notes-input" data-app-notes="${o.id}" value="${esc(o.application.notes || "")}" placeholder="Next step or notes…" />
      <button class="save-status-btn" data-save-status="${o.id}" type="button">Save</button>
    </article>`).join("");
  $("applicationsEmpty").classList.toggle("hidden", items.length > 0);
}

async function loadAdmin() {
  if (state.user.role !== "admin") return navigate("discover");
  const {stats, recent} = await api("/api/admin/stats");
  $("adminStudents").textContent = stats.students;
  $("adminOpportunities").textContent = stats.opportunities;
  $("adminVerified").textContent = stats.verified;
  $("adminApplications").textContent = stats.applications;
  $("adminOpportunityTable").innerHTML = `
    <table class="data-table"><thead><tr><th>Opportunity</th><th>Type</th><th>Deadline</th><th>Source</th><th></th></tr></thead>
    <tbody>${recent.map(o => `<tr><td><strong>${esc(o.title)}</strong><br><span>${esc(o.org)}</span></td><td>${esc(o.type)}</td><td>${formatDate(o.deadline)}</td><td>${o.verified ? "Verified" : o.is_demo ? "Demo" : "Unverified"}</td><td><div class="row-actions"><button data-admin-edit="${o.id}" type="button">Edit</button><button class="danger" data-admin-delete="${o.id}" type="button">Delete</button></div></td></tr>`).join("")}</tbody></table>`;
  await loadDashboardStats();
}

async function navigate(page) {
  if (!state.user) return;
  if (page === "admin" && state.user.role !== "admin") page = "discover";
  state.page = page;
  $$(".page").forEach(p => p.classList.add("hidden"));
  $(`${page}Page`).classList.remove("hidden");
  $$(".nav-item").forEach(n => n.classList.toggle("active", n.dataset.nav === page));
  document.querySelector(".sidebar")?.classList.remove("mobile-open");
  try {
    if (page === "discover") await loadDiscover();
    if (page === "saved") await loadSaved();
    if (page === "applications") await loadApplications();
    if (page === "admin") await loadAdmin();
  } catch (err) { toast(err.message); }
}

async function toggleSave(id) {
  const {saved} = await api(`/api/opportunities/${id}/save`, {method:"POST", body:{}});
  toast(saved ? "Saved to your shortlist" : "Removed from saved");
  await refreshCurrentPage();
}

async function refreshCurrentPage() {
  if (state.page === "discover") return loadDiscover();
  if (state.page === "saved") return loadSaved();
  if (state.page === "applications") return loadApplications();
  if (state.page === "admin") return loadAdmin();
}

async function openDetail(id, focusTracker = false) {
  try {
    const {item:o} = await api(`/api/opportunities/${id}`);
    state.detailId = id;
    const tracker = o.application || {status:"planning", notes:""};
    $("detailContent").innerHTML = `
      <div class="detail-wrap">
        <span class="eyebrow">${esc(o.type)} ${o.verified ? "• verified" : o.is_demo ? "• demo listing" : ""}</span>
        <h2>${esc(o.title)}</h2>
        <p class="detail-org">${esc(o.org)}</p>
        <p class="detail-description">${esc(o.description || "No description provided.")}</p>
        <div class="detail-meta">
          <div><span>Deadline</span><strong>${formatDate(o.deadline)}</strong></div>
          <div><span>Location</span><strong>${esc(o.location)}</strong></div>
          <div><span>Value</span><strong>${money(o.value)}</strong></div>
          <div><span>Eligibility</span><strong>${esc((o.grades || []).join(", ") || "See source")}</strong></div>
          <div><span>Interests</span><strong>${esc((o.interests || []).join(", ") || "General")}</strong></div>
          <div><span>Match</span><strong>${o.match_score}%</strong></div>
        </div>
        ${o.is_demo ? `<p class="form-note"><strong>Demo listing:</strong> this record is fictional and exists to test the product. Do not submit personal information or treat it as a real opportunity.</p>` : ""}
        <div class="detail-actions">
          <button class="btn secondary" data-detail-save="${o.id}" type="button">${o.saved ? "★ Saved" : "☆ Save opportunity"}</button>
          ${o.url ? `<a class="btn primary" data-outbound="${o.id}" href="${esc(o.url)}" target="_blank" rel="noopener noreferrer">Open official source ↗</a>` : `<button class="btn primary" type="button" disabled>No source link yet</button>`}
        </div>
        <div class="tracker-box" id="trackerBox">
          <div><span class="eyebrow">Application tracker</span><h3>What happens next?</h3></div>
          <label>Status<select id="detailStatus">${Object.entries(STATUS_LABELS).map(([key,label]) => `<option value="${key}" ${tracker.status === key ? "selected" : ""}>${label}</option>`).join("")}</select></label>
          <label>Notes<textarea id="detailNotes" rows="4" placeholder="Essay draft, recommendation request, interview date…">${esc(tracker.notes || "")}</textarea></label>
          <button class="btn primary" data-detail-track="${o.id}" type="button">${o.application ? "Update application" : "Add to application tracker"}</button>
        </div>
      </div>`;
    $("detailDialog").showModal();
    if (focusTracker) setTimeout(() => $("trackerBox")?.scrollIntoView({behavior:"smooth", block:"center"}), 100);
  } catch (err) { toast(err.message); }
}

async function saveApplication(id, status, notes) {
  await api(`/api/opportunities/${id}/application`, {method:"POST", body:{status, notes}});
  toast("Application tracker updated");
  await loadDashboardStats();
}

function openProfile() {
  $("profileName").value = state.user.name || "";
  $("profileGrade").value = state.user.grade || "11";
  $("profileLocation").value = state.user.location || "";
  $$("#profileInterests input").forEach(box => box.checked = state.user.interests?.includes(box.value));
  $("profileDialog").showModal();
}

function openOpportunityEditor(o = null) {
  $("opportunityForm").reset();
  $("oppId").value = o?.id || "";
  $("opportunityFormTitle").textContent = o ? "Edit opportunity" : "Add opportunity";
  $("oppTitle").value = o?.title || "";
  $("oppOrg").value = o?.org || "";
  $("oppType").value = o?.type || "Scholarship";
  $("oppDeadline").value = o?.deadline || "";
  $("oppValue").value = o?.value || 0;
  $("oppLocation").value = o?.location || "Online";
  $("oppUrl").value = o?.url || "";
  $("oppInterests").value = (o?.interests || []).join(", ");
  $("oppGrades").value = (o?.grades || []).join(", ");
  $("oppDescription").value = o?.description || "";
  $("oppVerified").checked = Boolean(o?.verified);
  $("opportunityDialog").showModal();
}

function opportunityPayload() {
  return {
    title: $("oppTitle").value.trim(), org: $("oppOrg").value.trim(), type: $("oppType").value,
    deadline: $("oppDeadline").value, value: Number($("oppValue").value || 0), location: $("oppLocation").value.trim(),
    url: $("oppUrl").value.trim(), interests: $("oppInterests").value, grades: $("oppGrades").value,
    description: $("oppDescription").value.trim(), verified: $("oppVerified").checked,
  };
}

// Auth controls
$("loginTab").addEventListener("click", () => setAuthMode("login"));
$("registerTab").addEventListener("click", () => setAuthMode("register"));

$("loginForm").addEventListener("submit", async e => {
  e.preventDefault();
  try {
    const {user} = await api("/api/login", {method:"POST", body:{email:$("loginEmail").value, password:$("loginPassword").value}});
    state.user = user; showApp(); toast("Signed in");
  } catch (err) { toast(err.message); }
});

$("registerForm").addEventListener("submit", async e => {
  e.preventDefault();
  try {
    const {user} = await api("/api/register", {method:"POST", body:{
      name:$("registerName").value, grade:$("registerGrade").value, location:$("registerLocation").value,
      email:$("registerEmail").value, password:$("registerPassword").value, interests:selectedInterests("registerInterests"),
    }});
    state.user = user; showApp(); toast("Your Access account is ready");
  } catch (err) { toast(err.message); }
});

$("logoutBtn").addEventListener("click", async () => {
  try { await api("/api/logout", {method:"POST", body:{}}); } catch (_) {}
  state.user = null; showAuth("login");
});

// Navigation
addEventListener("click", e => {
  const nav = e.target.closest("[data-nav]");
  if (nav && state.user) { e.preventDefault(); navigate(nav.dataset.nav); }
});
$("mobileMenuBtn").addEventListener("click", () => document.querySelector(".sidebar").classList.toggle("mobile-open"));

// Discover controls
let searchTimer;
$("searchInput").addEventListener("input", e => {
  clearTimeout(searchTimer); state.query = e.target.value.trim();
  searchTimer = setTimeout(() => state.page === "discover" && loadDiscover().catch(err => toast(err.message)), 220);
});
$("sortSelect").addEventListener("change", e => { state.sort = e.target.value; loadDiscover().catch(err => toast(err.message)); });
$("verifiedOnly").addEventListener("change", e => { state.verifiedOnly = e.target.checked; loadDiscover().catch(err => toast(err.message)); });
$("typeFilters").addEventListener("click", e => {
  const chip = e.target.closest("[data-type]"); if (!chip) return;
  state.type = chip.dataset.type; $$(".filter-chip").forEach(x => x.classList.toggle("active", x === chip));
  loadDiscover().catch(err => toast(err.message));
});

// Card/detail/application events
addEventListener("click", async e => {
  const save = e.target.closest("[data-save]");
  if (save) { e.stopPropagation(); try { await toggleSave(Number(save.dataset.save)); } catch (err) { toast(err.message); } return; }
  const details = e.target.closest("[data-details]");
  if (details) { openDetail(Number(details.dataset.details)); return; }
  const track = e.target.closest("[data-track]");
  if (track) { openDetail(Number(track.dataset.track), true); return; }
  const detailSave = e.target.closest("[data-detail-save]");
  if (detailSave) { try { await toggleSave(Number(detailSave.dataset.detailSave)); await openDetail(Number(detailSave.dataset.detailSave)); } catch (err) { toast(err.message); } return; }
  const detailTrack = e.target.closest("[data-detail-track]");
  if (detailTrack) {
    try {
      const id = Number(detailTrack.dataset.detailTrack);
      await saveApplication(id, $("detailStatus").value, $("detailNotes").value);
      await openDetail(id);
    } catch (err) { toast(err.message); }
    return;
  }
  const outbound = e.target.closest("[data-outbound]");
  if (outbound) api(`/api/opportunities/${outbound.dataset.outbound}/click`, {method:"POST", body:{}}).catch(()=>{});
  const saveStatus = e.target.closest("[data-save-status]");
  if (saveStatus) {
    const id = Number(saveStatus.dataset.saveStatus);
    try { await saveApplication(id, document.querySelector(`[data-app-status="${id}"]`).value, document.querySelector(`[data-app-notes="${id}"]`).value); await loadApplications(); } catch (err) { toast(err.message); }
    return;
  }
  const edit = e.target.closest("[data-admin-edit]");
  if (edit) {
    try { const {item} = await api(`/api/opportunities/${edit.dataset.adminEdit}`); openOpportunityEditor(item); } catch (err) { toast(err.message); }
    return;
  }
  const del = e.target.closest("[data-admin-delete]");
  if (del) {
    if (!confirm("Delete this opportunity from the database?")) return;
    try { await api(`/api/admin/opportunities/${del.dataset.adminDelete}`, {method:"DELETE"}); toast("Opportunity deleted"); await loadAdmin(); } catch (err) { toast(err.message); }
  }
});

// Profile
$("profileBtn").addEventListener("click", openProfile);
$("profileHeroBtn").addEventListener("click", openProfile);
$("profileForm").addEventListener("submit", async e => {
  e.preventDefault();
  try {
    const {user} = await api("/api/me/profile", {method:"PUT", body:{name:$("profileName").value, grade:$("profileGrade").value, location:$("profileLocation").value, interests:selectedInterests("profileInterests")}});
    state.user = user; $("profileDialog").close(); showApp(); toast("Profile updated");
  } catch (err) { toast(err.message); }
});

// Admin
$("newOpportunityBtn").addEventListener("click", () => openOpportunityEditor());
$("opportunityForm").addEventListener("submit", async e => {
  e.preventDefault();
  const id = $("oppId").value;
  try {
    if (id) await api(`/api/admin/opportunities/${id}`, {method:"PUT", body:opportunityPayload()});
    else await api("/api/admin/opportunities", {method:"POST", body:opportunityPayload()});
    $("opportunityDialog").close(); toast(id ? "Opportunity updated" : "Opportunity added"); await loadAdmin();
  } catch (err) { toast(err.message); }
});

$("importCsvBtn").addEventListener("click", async () => {
  const file = $("csvInput").files?.[0];
  if (!file) return toast("Choose a CSV file first");
  try {
    const text = await file.text();
    const result = await api("/api/admin/import-csv", {method:"POST", body:{csv:text}});
    $("importResult").textContent = `Imported ${result.imported} row(s).${result.errors.length ? ` ${result.errors.length} row(s) had errors.` : ""}`;
    toast(`Imported ${result.imported} opportunities`); await loadAdmin();
  } catch (err) { toast(err.message); }
});

// Dialog close controls
addEventListener("click", e => {
  const close = e.target.closest("[data-close-dialog]");
  if (close) $(close.dataset.closeDialog).close();
});
$$("dialog").forEach(dialog => dialog.addEventListener("click", e => {
  const rect = dialog.getBoundingClientRect();
  if (e.clientX < rect.left || e.clientX > rect.right || e.clientY < rect.top || e.clientY > rect.bottom) dialog.close();
}));

boot();
