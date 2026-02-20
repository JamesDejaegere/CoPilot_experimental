const state = {
  session: null,
  notificationPrefs: {
    email: false,
    push: false
  }
};

const authCard = document.getElementById("auth-card");
const app = document.getElementById("app");
const loginForm = document.getElementById("login-form");
const searchForm = document.getElementById("search-form");
const notificationForm = document.getElementById("notification-form");
const sessionInfo = document.getElementById("session-info");
const shipmentSummary = document.getElementById("shipment-summary");
const eventLog = document.getElementById("event-log");
const searchMessage = document.getElementById("search-message");
const notifMessage = document.getElementById("notif-message");
const notifEmail = document.getElementById("notif-email");
const notifPush = document.getElementById("notif-push");
const logoutButton = document.getElementById("logout");

loginForm.addEventListener("submit", (event) => {
  handleLoginSubmit(event);
});

logoutButton.addEventListener("click", () => {
  handleLogout();
});

searchForm.addEventListener("submit", (event) => {
  handleSearchSubmit(event);
});

notificationForm.addEventListener("submit", (event) => {
  handleNotificationSubmit(event);
});

async function handleLoginSubmit(event) {
  event.preventDefault();

  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const role = document.getElementById("role").value;

  const response = await fetch("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, role })
  });

  const payload = await response.json();
  if (!response.ok) {
    alert(payload.error || "Login failed.");
    return;
  }

  state.session = payload.user;

  applyAuthenticatedUI();
  await loadNotificationPreferences();
}

async function handleLogout() {
  await fetch("/api/logout", { method: "POST" });
  state.session = null;
  loginForm.reset();
  authCard.classList.remove("hidden");
  app.classList.add("hidden");
  notifMessage.textContent = "";
  searchMessage.textContent = "";
}

async function handleSearchSubmit(event) {
  event.preventDefault();

  if (!state.session?.permissions.includes("track")) {
    searchMessage.textContent = "Your role is not allowed to use tracking.";
    return;
  }

  const searchType = document.getElementById("search-type").value;
  const rawValue = document.getElementById("search-value").value.trim();

  if (!rawValue) {
    searchMessage.textContent = "Please enter a valid search value.";
    return;
  }

  const params = new URLSearchParams({ type: searchType, value: rawValue });
  const response = await fetch(`/api/shipments/search?${params.toString()}`);
  const payload = await response.json();

  if (!response.ok) {
    clearResults();
    searchMessage.textContent = payload.error || "Search failed.";
    return;
  }

  if (!payload.found) {
    clearResults();
    searchMessage.textContent = `No shipment found for '${rawValue}'.`;
    return;
  }

  searchMessage.textContent = `Shipment found with status: ${payload.shipment.status}.`;
  renderShipment(payload.shipment);
}

async function handleNotificationSubmit(event) {
  event.preventDefault();

  if (!state.session?.permissions.includes("notifications")) {
    notifMessage.textContent = "Your role cannot modify notification preferences.";
    return;
  }

  const response = await fetch("/api/notifications", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: notifEmail.checked, push: notifPush.checked })
  });
  const payload = await response.json();

  if (!response.ok) {
    notifMessage.textContent = payload.error || "Saving preferences failed.";
    return;
  }

  state.notificationPrefs = payload.preferences;
  notifMessage.textContent = "Notification preferences saved.";
}

function applyAuthenticatedUI() {
  authCard.classList.add("hidden");
  app.classList.remove("hidden");
  sessionInfo.textContent = `${state.session.email} (${state.session.roleLabel})`;
  updateNotificationPermissionUI();
  clearResults();
}

async function loadNotificationPreferences() {
  const response = await fetch("/api/notifications");
  const payload = await response.json();
  if (!response.ok) {
    state.notificationPrefs = { email: false, push: false };
    notifEmail.checked = false;
    notifPush.checked = false;
    return;
  }

  state.notificationPrefs = payload.preferences;
  notifEmail.checked = !!state.notificationPrefs.email;
  notifPush.checked = !!state.notificationPrefs.push;
}

function updateNotificationPermissionUI() {
  const allowed = state.session?.permissions.includes("notifications");
  notifEmail.disabled = !allowed;
  notifPush.disabled = !allowed;
  document.getElementById("save-notif").disabled = !allowed;

  if (!allowed) {
    notifMessage.textContent = "Viewer role only has read access for tracking.";
  } else {
    notifMessage.textContent = "";
  }
}

function clearResults() {
  shipmentSummary.innerHTML = "<p>No search result yet.</p>";
  eventLog.innerHTML = "";
}

function renderShipment(shipment) {
  const summaryFields = [
    ["Container", shipment.containerNumber],
    ["B/L", shipment.blNumber],
    ["Booking", shipment.bookingNumber],
    ["Vessel", `${shipment.vesselName} (${shipment.voyage})`],
    ["Current port", shipment.currentPort],
    ["ETA", formatDate(shipment.eta)],
    ["Status", shipment.status]
  ];

  shipmentSummary.innerHTML = summaryFields
    .map(
      ([label, value]) =>
        `<div class="summary-item"><strong>${label}</strong><br/><span>${value}</span></div>`
    )
    .join("");

  eventLog.innerHTML = shipment.events
    .map(
      (evt) => `<li><strong>${evt.name}</strong><br/>${evt.timestamp} · ${evt.location}</li>`
    )
    .join("");
}

function formatDate(isoString) {
  const date = new Date(isoString);
  return date.toLocaleString("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC"
  });
}

async function bootstrapSession() {
  const response = await fetch("/api/me");
  const payload = await response.json();

  if (payload.authenticated && payload.user) {
    state.session = payload.user;
    applyAuthenticatedUI();
    await loadNotificationPreferences();
  } else {
    state.session = null;
    authCard.classList.remove("hidden");
    app.classList.add("hidden");
  }
}

clearResults();
bootstrapSession();
