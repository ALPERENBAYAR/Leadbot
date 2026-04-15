const scrapeForm = document.getElementById("scrape-form");
const scrapeMessage = document.getElementById("scrape-message");
const scrapeCooldownMessage = document.getElementById("scrape-cooldown-message");
const scrapeSubmitButton = document.getElementById("scrape-submit-button");
const scrapeStopButton = document.getElementById("scrape-stop-button");
const maxResultsInput = document.getElementById("scrape-max-results");
const statTotalLeads = document.getElementById("stat-total-leads");
const statVisibleLeads = document.getElementById("stat-visible-leads");
const statTodayFollowups = document.getElementById("stat-today-followups");
const statOverdueFollowups = document.getElementById("stat-overdue-followups");
const viewNavButtons = document.querySelectorAll("[data-view-target]");
const viewSections = document.querySelectorAll("[data-view-section]");

const leadForm = document.getElementById("lead-form");
const formMessage = document.getElementById("form-message");
const submitButton = document.getElementById("submit-button");

const filterForm = document.getElementById("filter-form");
const clearFiltersButton = document.getElementById("clear-filters-button");
const filterQueryDropdown = document.getElementById("filter-query-dropdown");
const filterQueryToggle = document.getElementById("filter-query-toggle");
const filterQueryMenu = document.getElementById("filter-query-menu");

const editPanel = document.getElementById("edit-panel");
const editForm = document.getElementById("edit-form");
const editMessage = document.getElementById("edit-message");
const editCancelButton = document.getElementById("edit-cancel-button");
const activityList = document.getElementById("activity-list");
const activityMessage = document.getElementById("activity-message");
const activityNoteInput = document.getElementById("activity-note-input");
const addActivityNoteButton = document.getElementById("add-activity-note-button");

const leadsTableBody = document.getElementById("leads-table-body");
const selectAllLeadsCheckbox = document.getElementById("select-all-leads");
const prevPageButton = document.getElementById("prev-page-button");
const nextPageButton = document.getElementById("next-page-button");
const paginationButtons = document.getElementById("pagination-buttons");
const paginationInfo = document.getElementById("pagination-info");

const exportMessage = document.getElementById("export-message");
const exportAllCsvButton = document.getElementById("export-all-csv-button");
const exportAllExcelButton = document.getElementById("export-all-excel-button");
const exportSelectedCsvButton = document.getElementById("export-selected-csv-button");
const exportSelectedExcelButton = document.getElementById("export-selected-excel-button");
const clearLeadsButton = document.getElementById("clear-leads-button");
const bulkStatusSelect = document.getElementById("bulk-status-select");
const bulkStatusButton = document.getElementById("bulk-status-button");

const whatsappMessageTemplate = document.getElementById("whatsapp-message-template");
const prepareWhatsappButton = document.getElementById("prepare-whatsapp-button");
const whatsappPrepareMessage = document.getElementById("whatsapp-prepare-message");
const whatsappPreparedPanel = document.getElementById("whatsapp-prepared-panel");
const whatsappPreparedList = document.getElementById("whatsapp-prepared-list");

const emailSubjectTemplate = document.getElementById("email-subject-template");
const emailBodyTemplate = document.getElementById("email-body-template");
const prepareEmailButton = document.getElementById("prepare-email-button");
const emailPrepareMessage = document.getElementById("email-prepare-message");
const emailPreparedPanel = document.getElementById("email-prepared-panel");
const emailPreparedList = document.getElementById("email-prepared-list");
const outreachAvailableList = document.getElementById("outreach-available-list");
const outreachPrevPageButton = document.getElementById("outreach-prev-page-button");
const outreachNextPageButton = document.getElementById("outreach-next-page-button");
const outreachPaginationButtons = document.getElementById("outreach-pagination-buttons");
const outreachPaginationInfo = document.getElementById("outreach-pagination-info");
const selectedOutreachList = document.getElementById("selected-outreach-list");
const scheduleTodayButton = document.getElementById("schedule-today-button");
const followUpActionMessage = document.getElementById("follow-up-action-message");
const todayFollowUpList = document.getElementById("today-follow-up-list");
const overdueFollowUpList = document.getElementById("overdue-follow-up-list");

let activeScrapeJobId = null;
let scrapePollTimer = null;
let scrapeMetaTimer = null;
let currentLeads = [];
let currentPage = 1;
const pageSize = 10;
let totalLeadCount = 0;
let outreachCurrentPage = 1;
let outreachTotalLeadCount = 0;
let selectedQueryLabels = [];
let activeView = "overview";
const selectedLeadIds = new Set();
const selectedLeadCache = new Map();
const statusLabels = {
  new: "Yeni",
  contacted: "İletişim Kuruldu",
  quoted: "Teklif Verildi",
  follow_up: "Takip Ediliyor",
  won: "Kazanıldı",
  lost: "Kaybedildi",
};
const activityLabels = {
  called: "Arandı",
  whatsapp_opened: "WhatsApp Açıldı",
  whatsapp_prepared: "WhatsApp Hazırlandı",
  email_opened: "E-posta Açıldı",
  email_prepared: "E-posta Hazırlandı",
  email_replied: "E-posta Yanıtlandı",
  email_bounced: "E-posta Bounce Oldu",
  email_unsubscribed: "E-posta Reddi Geldi",
  quoted: "Teklif Verildi",
  note_added: "Not Eklendi",
};

function setActiveView(viewName, options = {}) {
  const normalizedView = viewName || "overview";
  const updateHash = options.updateHash !== false;

  activeView = normalizedView;

  viewNavButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.viewTarget === normalizedView);
  });

  viewSections.forEach((section) => {
    section.classList.toggle("is-active", section.dataset.viewSection === normalizedView);
  });

  if (normalizedView === "communication") {
    refreshOutreachSelectionPanels();
  }

  if (updateHash && window.location.hash !== `#${normalizedView}`) {
    history.replaceState(null, "", `#${normalizedView}`);
  }
}

function syncViewFromHash() {
  const hashView = window.location.hash.replace("#", "");
  const availableViews = new Set(Array.from(viewSections, (section) => section.dataset.viewSection));
  setActiveView(availableViews.has(hashView) ? hashView : "overview", { updateHash: false });
}

function escapeHtml(value) {
  if (!value) {
    return "";
  }

  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function displayValue(value) {
  if (!value) {
    return '<span class="muted-value">-</span>';
  }

  return escapeHtml(value);
}

function displayStatus(value) {
  if (!value) {
    return '<span class="muted-value">-</span>';
  }

  const label = escapeHtml(statusLabels[value] || value);
  return `<span class="status-badge status-${escapeHtml(value)}">${label}</span>`;
}

function displayTrackingStatus(value) {
  if (!value) {
    return '<span class="muted-value">Takip yok</span>';
  }

  const labels = {
    prepared: "Hazirlandi",
    opened: "Acildi",
    replied: "Yanit geldi",
    bounced: "Bounce",
    unsubscribed: "Liste disi",
  };

  return `<span class="status-badge tracking-${escapeHtml(value)}">${escapeHtml(labels[value] || value)}</span>`;
}

function displayEmailTracking(lead) {
  const parts = [displayTrackingStatus(lead.email_delivery_status)];

  if (lead.email_replied_at) {
    parts.push(`Yanit: ${escapeHtml(lead.email_replied_at)}`);
  }
  if (lead.email_bounced_at) {
    parts.push(`Bounce: ${escapeHtml(lead.email_bounced_at)}`);
  }
  if (lead.email_unsubscribed_at) {
    parts.push(`Opt-out: ${escapeHtml(lead.email_unsubscribed_at)}`);
  }
  if (lead.email_last_event_at) {
    parts.push(`Son olay: ${escapeHtml(lead.email_last_event_at)}`);
  }

  return `<div class="tracking-stack">${parts.map((item) => `<div>${item}</div>`).join("")}</div>`;
}

function displayActivityType(value) {
  if (!value) {
    return '<span class="muted-value">-</span>';
  }

  return escapeHtml(activityLabels[value] || value);
}

function formatDate(value) {
  if (!value) {
    return '<span class="muted-value">-</span>';
  }

  const date = new Date(value.replace(" ", "T"));
  if (Number.isNaN(date.getTime())) {
    return escapeHtml(value);
  }

  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

function displayWebsiteLink(value) {
  if (!value) {
    return '<span class="muted-value">-</span>';
  }

  const href = escapeHtml(value);
  const label = escapeHtml(value.replace(/^https?:\/\//, ""));
  return `<a class="lead-link" href="${href}" target="_blank" rel="noreferrer">${label}</a>`;
}

function setMessageState(element, message, type = "") {
  element.textContent = message;
  element.className = "form-message";

  if (type) {
    element.classList.add(`is-${type}`);
  }
}

function setFormMessage(message, type = "") {
  setMessageState(formMessage, message, type);
}

function setScrapeMessage(message, type = "") {
  setMessageState(scrapeMessage, message, type);
}

function setExportMessage(message, type = "") {
  setMessageState(exportMessage, message, type);
}

function setEditMessage(message, type = "") {
  setMessageState(editMessage, message, type);
}

function setWhatsappPrepareMessage(message, type = "") {
  setMessageState(whatsappPrepareMessage, message, type);
}

function setEmailPrepareMessage(message, type = "") {
  setMessageState(emailPrepareMessage, message, type);
}

function setActivityMessage(message, type = "") {
  setMessageState(activityMessage, message, type);
}

function setFollowUpActionMessage(message, type = "") {
  setMessageState(followUpActionMessage, message, type);
}

function updateDashboardStats({
  totalLeads = totalLeadCount,
  visibleLeads = currentLeads.length,
  todayFollowups = Number(statTodayFollowups?.textContent || 0),
  overdueFollowups = Number(statOverdueFollowups?.textContent || 0),
} = {}) {
  statTotalLeads.textContent = String(totalLeads);
  statVisibleLeads.textContent = String(visibleLeads);
  statTodayFollowups.textContent = String(todayFollowups);
  statOverdueFollowups.textContent = String(overdueFollowups);
}

function normalizeWhatsappPhone(phone) {
  if (!phone) {
    return null;
  }

  const digits = String(phone).replace(/\D/g, "");
  if (digits.length < 10) {
    return null;
  }

  if (digits.startsWith("90") && digits.length === 12) {
    return digits;
  }

  if (digits.startsWith("0") && digits.length === 11) {
    return `90${digits.slice(1)}`;
  }

  if (digits.length === 10 && digits.startsWith("5")) {
    return `90${digits}`;
  }

  if (digits.startsWith("90") && digits.length > 12) {
    return digits.slice(0, 12);
  }

  return null;
}

function normalizeEmailAddress(email) {
  if (!email) {
    return null;
  }

  const cleaned = String(email).trim().toLowerCase();
  if (!cleaned.includes("@")) {
    return null;
  }

  return cleaned;
}

function buildWhatsappUrl(phone, message) {
  const normalizedPhone = normalizeWhatsappPhone(phone);
  if (!normalizedPhone) {
    return null;
  }

  if (message) {
    return `https://wa.me/${normalizedPhone}?text=${encodeURIComponent(message)}`;
  }

  return `https://wa.me/${normalizedPhone}`;
}

function buildMailtoUrl(email, subject, body) {
  const normalizedEmail = normalizeEmailAddress(email);
  if (!normalizedEmail) {
    return null;
  }

  const query = new URLSearchParams();
  if (subject) {
    query.set("subject", subject);
  }
  if (body) {
    query.set("body", body);
  }

  const queryString = query.toString();
  return queryString ? `mailto:${normalizedEmail}?${queryString}` : `mailto:${normalizedEmail}`;
}

function getTemplateMessage(businessName) {
  const template = (whatsappMessageTemplate.value || "").trim();
  return template.replaceAll("{business_name}", businessName);
}

function getEmailBodyTemplate(businessName) {
  const template = (emailBodyTemplate.value || "").trim();
  return template.replaceAll("{business_name}", businessName);
}

function renderPreparedContacts(contacts) {
  if (!contacts.length) {
    whatsappPreparedPanel.classList.remove("hidden");
    whatsappPreparedList.innerHTML = '<div class="prepared-card"><p>Geçerli numara bulunamadı.</p></div>';
    return;
  }

  whatsappPreparedPanel.classList.remove("hidden");
  whatsappPreparedList.innerHTML = contacts
    .map(
      (contact) => `
        <div class="prepared-card">
          <p><strong>${escapeHtml(contact.business_name)}</strong></p>
          <p>Telefon: ${displayValue(contact.original_phone)}</p>
          <p class="prepared-preview">${escapeHtml(getTemplateMessage(contact.business_name))}</p>
          <a class="action-link whatsapp-button prepared-whatsapp-link" data-lead-id="${contact.id}" href="${escapeHtml(contact.whatsapp_url)}" target="_blank" rel="noreferrer">Bağlantıyı Aç</a>
        </div>
      `,
    )
    .join("");
}

function renderPreparedEmails(contacts) {
  if (!contacts.length) {
    emailPreparedPanel.classList.remove("hidden");
    emailPreparedList.innerHTML = '<div class="prepared-card"><p>Geçerli e-posta bulunamadı.</p></div>';
    return;
  }

  emailPreparedPanel.classList.remove("hidden");
  emailPreparedList.innerHTML = contacts
    .map(
      (contact) => `
        <div class="prepared-card">
          <p><strong>${escapeHtml(contact.business_name)}</strong></p>
          <p>E-posta: ${displayValue(contact.email)}</p>
          <p class="prepared-preview">${escapeHtml(getEmailBodyTemplate(contact.business_name))}</p>
          <a class="action-link email-button prepared-email-link" data-lead-id="${contact.id}" href="${escapeHtml(contact.mailto_url)}">Bağlantıyı Aç</a>
        </div>
      `,
    )
    .join("");
}

function renderFollowUpList(element, leads, emptyMessage) {
  if (!leads.length) {
    element.innerHTML = `<p class="muted-value">${emptyMessage}</p>`;
    return;
  }

  element.innerHTML = leads
    .map(
      (lead) => `
        <div class="follow-up-item">
          <p><strong>${escapeHtml(lead.business_name)}</strong></p>
          <p>Durum: ${displayStatus(lead.status)}</p>
          <p>Sonraki İletişim Tarihi: ${displayValue(lead.next_contact_date)}</p>
          <p>Telefon: ${displayValue(lead.phone)}</p>
          <div class="follow-up-actions">
            <button class="small-button secondary-button edit-button" type="button" data-lead-id="${lead.id}">Düzenle</button>
            <button class="small-button danger-button delete-lead-button" type="button" data-lead-id="${lead.id}" data-business-name="${escapeHtml(lead.business_name)}">Kaldır</button>
          </div>
        </div>
      `,
    )
    .join("");
}

async function deleteLead(leadId, businessName = "") {
  const label = businessName || `#${leadId}`;
  const confirmed = window.confirm(`"${label}" kaydını kaldırmak istediğinize emin misiniz?`);
  if (!confirmed) {
    return false;
  }

  const response = await fetch(`/api/leads/${leadId}`, {
    method: "DELETE",
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Lead kaldırılamadı.");
  }

  selectedLeadIds.delete(leadId);
  selectedLeadCache.delete(leadId);

  const editingLeadId = Number(document.getElementById("edit-id").value);
  if (editingLeadId === leadId) {
    closeEditPanel();
  }

  if (!selectedLeadIds.size) {
    whatsappPreparedPanel.classList.add("hidden");
    emailPreparedPanel.classList.add("hidden");
  }

  await loadFollowUpSummary();
  await loadLeads();
  refreshOutreachSelectionPanels();

  return true;
}

async function fetchSelectedLeadDetails(ids) {
  if (!ids.length) {
    return [];
  }

  const missingIds = ids.filter((id) => !selectedLeadCache.has(id));
  if (missingIds.length) {
    const response = await fetch("/api/leads/by-ids", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ lead_ids: missingIds }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Secili kayitlar yuklenemedi.");
    }

    data.forEach((lead) => {
      selectedLeadCache.set(lead.id, lead);
    });
  }

  return ids
    .map((id) => selectedLeadCache.get(id))
    .filter(Boolean);
}

function renderSelectedOutreachLeads(leads) {
  if (!selectedOutreachList) {
    return;
  }

  if (!leads.length) {
    selectedOutreachList.innerHTML = '<p class="muted-value">Secili kayit yok.</p>';
    return;
  }

  selectedOutreachList.innerHTML = leads
    .map(
      (lead) => `
        <label class="selected-outreach-card">
          <input
            class="selected-outreach-checkbox"
            type="checkbox"
            data-lead-id="${lead.id}"
            ${selectedLeadIds.has(lead.id) ? "checked" : ""}
          />
          <div>
            <p><strong>${escapeHtml(lead.business_name)}</strong></p>
            <p>Telefon: ${displayValue(lead.phone)}</p>
            <p>E-posta: ${displayValue(lead.email)}</p>
            <p>Durum: ${displayStatus(lead.status)}</p>
          </div>
        </label>
      `,
    )
    .join("");
}

function renderAvailableOutreachLeads(leads) {
  if (!outreachAvailableList) {
    return;
  }

  if (!leads.length) {
    outreachAvailableList.innerHTML = '<p class="muted-value">Bu filtrede gorunen kayit yok.</p>';
    return;
  }

  outreachAvailableList.innerHTML = leads
    .map(
      (lead) => `
        <label class="selected-outreach-card">
          <input
            class="outreach-available-checkbox"
            type="checkbox"
            data-lead-id="${lead.id}"
            ${selectedLeadIds.has(lead.id) ? "checked" : ""}
          />
          <div>
            <p><strong>${escapeHtml(lead.business_name)}</strong></p>
            <p>Telefon: ${displayValue(lead.phone)}</p>
            <p>E-posta: ${displayValue(lead.email)}</p>
            <p>Durum: ${displayStatus(lead.status)}</p>
          </div>
        </label>
      `,
    )
    .join("");
}

function updateOutreachPaginationControls() {
  if (!outreachPaginationInfo || !outreachPrevPageButton || !outreachNextPageButton || !outreachPaginationButtons) {
    return;
  }

  const totalPages = Math.max(1, Math.ceil(outreachTotalLeadCount / pageSize));
  outreachPaginationInfo.textContent = `Sayfa ${outreachCurrentPage} / ${totalPages} - Toplam ${outreachTotalLeadCount} kayit`;
  outreachPrevPageButton.disabled = outreachCurrentPage <= 1;
  outreachNextPageButton.disabled = outreachCurrentPage >= totalPages;

  const pages = buildVisiblePages(totalPages, outreachCurrentPage);
  outreachPaginationButtons.innerHTML = pages
    .map((page) => {
      if (page === "...") {
        return '<span class="pagination-ellipsis">...</span>';
      }

      const activeClass = page === outreachCurrentPage ? " is-active" : "";
      return `
        <button
          type="button"
          class="secondary-button pagination-button outreach-page-button${activeClass}"
          data-page="${page}"
        >
          ${page}
        </button>
      `;
    })
    .join("");
}

async function loadOutreachAvailableLeads() {
  if (!outreachAvailableList) {
    return;
  }

  outreachAvailableList.innerHTML = '<p class="muted-value">Leadler yukleniyor...</p>';

  const params = getLeadListParams(outreachCurrentPage);
  const response = await fetch(`/api/leads?${params.toString()}`);
  if (!response.ok) {
    throw new Error("Outreach leadleri yuklenemedi.");
  }

  const data = await response.json();
  outreachTotalLeadCount = data.total ?? 0;

  const totalPages = Math.max(1, Math.ceil(outreachTotalLeadCount / pageSize));
  if (outreachCurrentPage > totalPages) {
    outreachCurrentPage = totalPages;
    return loadOutreachAvailableLeads();
  }

  const leads = data.items ?? [];
  leads.forEach((lead) => {
    selectedLeadCache.set(lead.id, lead);
  });

  renderAvailableOutreachLeads(leads);
  updateOutreachPaginationControls();
}

async function refreshSelectedOutreachList() {
  if (!selectedOutreachList) {
    return;
  }

  const ids = getSelectedLeadIds();
  if (!ids.length) {
    renderSelectedOutreachLeads([]);
    return;
  }

  try {
    const leads = await fetchSelectedLeadDetails(ids);
    renderSelectedOutreachLeads(leads);
  } catch (error) {
    selectedOutreachList.innerHTML = `<p class="muted-value">${escapeHtml(error.message)}</p>`;
  }
}

function refreshOutreachSelectionPanels() {
  if (activeView === "communication") {
    void loadOutreachAvailableLeads().catch((error) => {
      if (outreachAvailableList) {
        outreachAvailableList.innerHTML = `<p class="muted-value">${escapeHtml(error.message)}</p>`;
      }
    });
  }
  void refreshSelectedOutreachList();
}

function renderActivityList(items) {
  if (!items.length) {
    activityList.innerHTML = '<p class="muted-value">Henüz iletişim geçmişi yok.</p>';
    return;
  }

  activityList.innerHTML = items
    .map(
      (item) => `
        <div class="activity-item">
          <p><strong>${displayActivityType(item.activity_type)}</strong></p>
          <p>${displayValue(item.activity_note)}</p>
          <p class="activity-meta">${formatDate(item.created_at)}</p>
        </div>
      `,
    )
    .join("");
}

async function loadLeadActivities(leadId) {
  activityList.innerHTML = '<p class="muted-value">Geçmiş yükleniyor...</p>';

  const response = await fetch(`/api/leads/${leadId}/activities`);
  if (!response.ok) {
    throw new Error("İletişim geçmişi yüklenemedi.");
  }

  const items = await response.json();
  renderActivityList(items);
}

async function createLeadActivity(leadId, activityType, activityNote = "") {
  const response = await fetch(`/api/leads/${leadId}/activities`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      activity_type: activityType,
      activity_note: activityNote,
    }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Aktivite kaydedilemedi.");
  }

  return data;
}

function createLeadActivitySilently(leadId, activityType) {
  fetch(`/api/leads/${leadId}/activities`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      activity_type: activityType,
    }),
    keepalive: true,
  }).catch(() => {});
}

function markLeadContactedSilently(leadId) {
  fetch(`/api/leads/${leadId}/mark-contacted`, {
    method: "POST",
    keepalive: true,
  })
    .then(() => Promise.all([loadFollowUpSummary(), loadLeads()]))
    .catch(() => {});
}

async function loadFollowUpSummary() {
  const response = await fetch("/api/leads/follow-up-summary");
  if (!response.ok) {
    throw new Error("Takip paneli yüklenemedi.");
  }

  const data = await response.json();
  renderFollowUpList(todayFollowUpList, data.today ?? [], "Bugün için planlı takip yok.");
  renderFollowUpList(overdueFollowUpList, data.overdue ?? [], "Geciken takip yok.");
  updateDashboardStats({
    todayFollowups: (data.today ?? []).length,
    overdueFollowups: (data.overdue ?? []).length,
  });
}

function getFilterParams() {
  const formData = new FormData(filterForm);
  const params = new URLSearchParams();

  for (const [key, value] of formData.entries()) {
    if (String(value).trim()) {
      params.set(key, String(value).trim());
    }
  }

  selectedQueryLabels.forEach((label) => {
    params.append("query_label", label);
  });

  return params;
}

function getLeadListParams(page) {
  const params = getFilterParams();
  params.set("limit", String(pageSize));
  params.set("offset", String((page - 1) * pageSize));
  return params;
}

async function loadQueryOptions() {
  const selectedValues = [...selectedQueryLabels];
  const response = await fetch("/api/leads/query-options");
  if (!response.ok) {
    throw new Error("Tarama sorguları yüklenemedi.");
  }

  const data = await response.json();
  const options = data.items ?? [];
  selectedQueryLabels = selectedValues.filter((item) => options.includes(item));

  filterQueryMenu.innerHTML = options
    .map((item) => {
      const checked = selectedQueryLabels.includes(item) ? "checked" : "";
      return `
        <label class="multi-select-option">
          <input type="checkbox" value="${escapeHtml(item)}" ${checked} />
          <span>${escapeHtml(item)}</span>
        </label>
      `;
    })
    .join("");

  updateQueryToggleLabel();
}

function updateQueryToggleLabel() {
  if (!selectedQueryLabels.length) {
    filterQueryToggle.textContent = "Tüm sorgular";
    return;
  }

  if (selectedQueryLabels.length === 1) {
    filterQueryToggle.textContent = selectedQueryLabels[0];
    return;
  }

  filterQueryToggle.textContent = `${selectedQueryLabels.length} sorgu seçildi`;
}

function syncQueryMenuSelection() {
  filterQueryMenu.querySelectorAll('input[type="checkbox"]').forEach((input) => {
    input.checked = selectedQueryLabels.includes(input.value);
  });
}

function renderLeads(leads) {
  currentLeads = leads;
  leads.forEach((lead) => {
    selectedLeadCache.set(lead.id, lead);
  });

  if (!leads.length) {
    leadsTableBody.innerHTML =
      '<tr><td colspan="14" class="empty-state">Henüz kayıt yok</td></tr>';
    updateDashboardStats({
      visibleLeads: 0,
    });
    return;
  }

  leadsTableBody.innerHTML = leads
    .map((lead) => {
      const whatsappPhone = normalizeWhatsappPhone(lead.phone);
      const emailAddress = normalizeEmailAddress(lead.email);
      const whatsappButton = whatsappPhone
        ? `<button class="small-button whatsapp-button row-whatsapp-button" type="button" data-lead-id="${lead.id}" data-phone="${escapeHtml(lead.phone || "")}" data-name="${escapeHtml(lead.business_name)}">WhatsApp</button>`
        : '<button class="small-button whatsapp-button disabled-button" type="button" title="Telefon numarası uygun değil">WhatsApp</button>';
      const emailButton = emailAddress
        ? `<button class="small-button email-button row-email-button" type="button" data-lead-id="${lead.id}" data-email="${escapeHtml(lead.email || "")}" data-name="${escapeHtml(lead.business_name)}">E-posta</button>`
        : '<button class="small-button email-button disabled-button" type="button" title="E-posta adresi uygun değil">E-posta</button>';

      return `
        <tr>
          <td class="checkbox-cell">
            <input class="row-checkbox" type="checkbox" data-lead-id="${lead.id}" aria-label="Lead seç" ${selectedLeadIds.has(lead.id) ? "checked" : ""} />
          </td>
          <td>${lead.id}</td>
          <td><div class="lead-name">${escapeHtml(lead.business_name)}</div></td>
          <td><div class="lead-contact">${displayValue(lead.phone)}</div></td>
          <td><div class="lead-contact">${displayValue(lead.email)}</div></td>
          <td>${displayWebsiteLink(lead.website)}</td>
          <td><div class="lead-contact">${displayValue(lead.address)}</div></td>
          <td>${displayValue(lead.category)}</td>
          <td>${displayStatus(lead.status)}</td>
          <td>${displayEmailTracking(lead)}</td>
          <td>${displayValue(lead.note)}</td>
          <td>${displayValue(lead.next_contact_date)}</td>
          <td><div class="lead-date">${formatDate(lead.created_at)}</div></td>
          <td class="actions-cell">
            <div class="actions-group">
              ${whatsappButton}
              ${emailButton}
              <button class="small-button secondary-button edit-button" type="button" data-lead-id="${lead.id}">Düzenle</button>
              <button class="small-button danger-button delete-lead-button" type="button" data-lead-id="${lead.id}" data-business-name="${escapeHtml(lead.business_name)}">Kaldır</button>
            </div>
          </td>
        </tr>
      `;
    })
    .join("");

  updateDashboardStats({
    visibleLeads: leads.length,
  });
  updateSelectAllState();
}

function updatePaginationControls() {
  const totalPages = Math.max(1, Math.ceil(totalLeadCount / pageSize));
  paginationInfo.textContent = `Sayfa ${currentPage} / ${totalPages} - Toplam ${totalLeadCount} kayıt`;
  prevPageButton.disabled = currentPage <= 1;
  nextPageButton.disabled = currentPage >= totalPages;
  renderPaginationButtons(totalPages);
}

function renderPaginationButtons(totalPages) {
  const pages = buildVisiblePages(totalPages, currentPage);
  paginationButtons.innerHTML = pages
    .map((page) => {
      if (page === "...") {
        return '<span class="pagination-ellipsis">...</span>';
      }

      const activeClass = page === currentPage ? " is-active" : "";
      return `
        <button
          type="button"
          class="secondary-button pagination-button${activeClass}"
          data-page="${page}"
        >
          ${page}
        </button>
      `;
    })
    .join("");
}

function buildVisiblePages(totalPages, activePage) {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  if (activePage <= 4) {
    return [1, 2, 3, 4, 5, "...", totalPages];
  }

  if (activePage >= totalPages - 3) {
    return [1, "...", totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
  }

  return [1, "...", activePage - 1, activePage, activePage + 1, "...", totalPages];
}

async function loadLeads() {
  const params = getLeadListParams(currentPage);
  const response = await fetch(`/api/leads?${params.toString()}`);
  if (!response.ok) {
    throw new Error("Kayıtlar yüklenemedi.");
  }

  const data = await response.json();
  totalLeadCount = data.total ?? 0;
  updateDashboardStats({
    totalLeads: totalLeadCount,
  });

  const totalPages = Math.max(1, Math.ceil(totalLeadCount / pageSize));
  if (currentPage > totalPages) {
    currentPage = totalPages;
    return loadLeads();
  }

  renderLeads(data.items ?? []);
  updatePaginationControls();
}

function goToFirstPage() {
  currentPage = 1;
}

function getSelectedLeadIds() {
  return Array.from(selectedLeadIds);
}

function updateSelectAllState() {
  const checkboxes = Array.from(document.querySelectorAll(".row-checkbox"));
  if (!checkboxes.length) {
    selectAllLeadsCheckbox.checked = false;
    return;
  }

  selectAllLeadsCheckbox.checked = checkboxes.every((checkbox) => checkbox.checked);
}

function setLeadSelection(leadId, isSelected) {
  if (!leadId) {
    return;
  }

  if (isSelected) {
    selectedLeadIds.add(leadId);
  } else {
    selectedLeadIds.delete(leadId);
  }
}

function triggerDownload(blob, filename) {
  const downloadUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = downloadUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(downloadUrl);
}

function extractFilename(response, fallbackName) {
  const disposition = response.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="([^"]+)"/);
  return match ? match[1] : fallbackName;
}

async function downloadFromGet(url, fallbackName) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error("Dosya indirilemedi.");
  }

  const blob = await response.blob();
  triggerDownload(blob, extractFilename(response, fallbackName));
}

async function downloadSelected(url, ids, fallbackName) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ lead_ids: ids }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Seçili kayıtlar indirilemedi.");
  }

  const blob = await response.blob();
  triggerDownload(blob, extractFilename(response, fallbackName));
}

function setScrapeRunningState(isRunning) {
  scrapeSubmitButton.disabled = isRunning;
  scrapeStopButton.disabled = !isRunning;
}

async function updateScrapeMeta() {
  try {
    const response = await fetch("/api/scrape/google-maps/meta");
    const data = await response.json();

    if (!response.ok) {
      return;
    }

    if (data.has_running_job) {
      scrapeCooldownMessage.textContent = "Tarama aktif. İsterseniz durdurabilirsiniz.";
      return;
    }

    if (data.cooldown_remaining_seconds > 0) {
      scrapeCooldownMessage.textContent =
        `Sonraki güvenli tarama için kalan süre: ${data.cooldown_remaining_seconds} saniye`;
      return;
    }

    scrapeCooldownMessage.textContent = "Yeni tarama başlatabilirsiniz.";
  } catch {
    scrapeCooldownMessage.textContent = "";
  }
}

function startScrapeMetaPolling() {
  if (scrapeMetaTimer) {
    clearInterval(scrapeMetaTimer);
  }

  updateScrapeMeta();
  scrapeMetaTimer = setInterval(updateScrapeMeta, 1000);
}

function stopScrapePolling() {
  if (scrapePollTimer) {
    clearTimeout(scrapePollTimer);
    scrapePollTimer = null;
  }

  activeScrapeJobId = null;
  setScrapeRunningState(false);
  updateScrapeMeta();
}

async function pollScrapeStatus() {
  if (!activeScrapeJobId) {
    return;
  }

  try {
    const response = await fetch(`/api/scrape/google-maps/${activeScrapeJobId}`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Tarama durumu alınamadı.");
    }

    await loadLeads();
    const scrapedCount = data.scraped_count ?? data.scraped_leads ?? 0;
    const savedCount = data.saved_count ?? data.saved_leads ?? 0;
    const skippedCount = data.skipped_count ?? data.skipped_duplicates ?? 0;

    if (data.status === "running") {
      setScrapeMessage(
        data.message ||
          `Tarama devam ediyor, lütfen bekleyin... ${scrapedCount} sonuç bulundu, ${savedCount} kayıt eklendi, ${skippedCount} kayıt tekrar olduğu için atlandı.`,
      );
      scrapePollTimer = setTimeout(pollScrapeStatus, 1400);
      return;
    }

    if (data.status === "stopping") {
      setScrapeMessage(data.message || "Tarama durduruluyor. Lütfen bekleyin...");
      scrapePollTimer = setTimeout(pollScrapeStatus, 900);
      return;
    }

    if (data.status === "completed") {
      goToFirstPage();
      await loadQueryOptions();
      await loadFollowUpSummary();
      await loadLeads();
      setScrapeMessage(
        data.message ||
          `Tarama tamamlandı. ${scrapedCount} sonuç bulundu, ${savedCount} kayıt eklendi, ${skippedCount} kayıt tekrar olduğu için atlandı.`,
        "success",
      );
      stopScrapePolling();
      return;
    }

    if (data.status === "cancelled") {
      setScrapeMessage(data.message || "Tarama durduruldu.", "success");
      stopScrapePolling();
      return;
    }

    throw new Error(data.error || "Tarama başarısız oldu.");
  } catch (error) {
    setScrapeMessage(error.message, "error");
    stopScrapePolling();
  }
}

async function openEditPanel(leadId) {
  let lead =
    currentLeads.find((item) => item.id === leadId) ||
    selectedLeadCache.get(leadId);

  if (!lead) {
    const [fetchedLead] = await fetchSelectedLeadDetails([leadId]);
    lead = fetchedLead;
  }

  if (!lead) {
    setFollowUpActionMessage("Lead bulunamadı.", "error");
    return;
  }

  setActiveView("followup");
  document.getElementById("edit-id").value = lead.id;
  document.getElementById("edit-business_name").value = lead.business_name || "";
  document.getElementById("edit-phone").value = lead.phone || "";
  document.getElementById("edit-email").value = lead.email || "";
  document.getElementById("edit-website").value = lead.website || "";
  document.getElementById("edit-address").value = lead.address || "";
  document.getElementById("edit-category").value = lead.category || "";
  document.getElementById("edit-source").value = lead.source || "";
  document.getElementById("edit-status").value = lead.status || "";
  document.getElementById("edit-note").value = lead.note || "";
  document.getElementById("edit-next_contact_date").value = lead.next_contact_date || "";
  editPanel.classList.remove("hidden");
  editPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  setActivityMessage("");
  activityNoteInput.value = "";
  loadLeadActivities(leadId).catch((error) => {
    activityList.innerHTML = `<p class="muted-value">${escapeHtml(error.message)}</p>`;
  });
}

function closeEditPanel() {
  editPanel.classList.add("hidden");
  editForm.reset();
  setEditMessage("");
  setActivityMessage("");
  activityNoteInput.value = "";
  activityList.innerHTML = '<p class="muted-value">Geçmiş yükleniyor...</p>';
}

viewNavButtons.forEach((button) => {
  button.addEventListener("click", () => {
    setActiveView(button.dataset.viewTarget);
  });
});

window.addEventListener("hashchange", syncViewFromHash);
syncViewFromHash();

maxResultsInput.addEventListener("input", () => {
  const value = Number(maxResultsInput.value);
  if (value > 100) {
    maxResultsInput.value = "100";
  }
  if (value < 1 && maxResultsInput.value !== "") {
    maxResultsInput.value = "1";
  }
});

scrapeStopButton.addEventListener("click", async () => {
  if (!activeScrapeJobId) {
    return;
  }

  scrapeStopButton.disabled = true;

  try {
    const response = await fetch(`/api/scrape/google-maps/${activeScrapeJobId}/stop`, {
      method: "POST",
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Tarama durdurulamadı.");
    }

    setScrapeMessage(data.message || "Tarama durduruluyor...");
    updateScrapeMeta();
  } catch (error) {
    scrapeStopButton.disabled = false;
    setScrapeMessage(error.message, "error");
  }
});

filterForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  goToFirstPage();
  outreachCurrentPage = 1;

  try {
    await loadLeads();
    refreshOutreachSelectionPanels();
    setExportMessage("Filtre sonuçları yüklendi.", "success");
  } catch (error) {
    setExportMessage(error.message, "error");
  }
});

clearFiltersButton.addEventListener("click", async () => {
  filterForm.reset();
  selectedQueryLabels = [];
  syncQueryMenuSelection();
  updateQueryToggleLabel();
  goToFirstPage();
  outreachCurrentPage = 1;

  try {
    await loadLeads();
    refreshOutreachSelectionPanels();
    setExportMessage("Filtreler temizlendi.", "success");
  } catch (error) {
    setExportMessage(error.message, "error");
  }
});

bulkStatusButton.addEventListener("click", async () => {
  const selectedIds = getSelectedLeadIds();
  if (!selectedIds.length) {
    setExportMessage("Lütfen durum güncellemek için en az bir kayıt seçin.", "error");
    return;
  }

  try {
    const response = await fetch("/api/leads/bulk-status", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        lead_ids: selectedIds,
        status: bulkStatusSelect.value,
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Toplu durum güncellenemedi.");
    }

    await loadFollowUpSummary();
    await loadLeads();
    setExportMessage(`${data.updated_count} kayıt için durum güncellendi.`, "success");
  } catch (error) {
    setExportMessage(error.message, "error");
  }
});

scheduleTodayButton.addEventListener("click", async () => {
  const selectedIds = getSelectedLeadIds();
  if (!selectedIds.length) {
    setFollowUpActionMessage("Lütfen bugüne eklemek için en az bir kayıt seçin.", "error");
    return;
  }

  try {
    const response = await fetch("/api/leads/schedule-today", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        lead_ids: selectedIds,
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Kayıtlar bugüne eklenemedi.");
    }

    await loadFollowUpSummary();
    await loadLeads();
    setFollowUpActionMessage(
      `${data.updated_count} kayıt bugün aranacaklara eklendi.`,
      "success",
    );
  } catch (error) {
    setFollowUpActionMessage(error.message, "error");
  }
});

filterQueryToggle.addEventListener("click", () => {
  filterQueryMenu.classList.toggle("hidden");
});

filterQueryMenu.addEventListener("change", (event) => {
  const checkbox = event.target.closest('input[type="checkbox"]');
  if (!checkbox) {
    return;
  }

  selectedQueryLabels = Array.from(
    filterQueryMenu.querySelectorAll('input[type="checkbox"]:checked'),
  ).map((input) => input.value);

  updateQueryToggleLabel();
});

document.addEventListener("click", (event) => {
  if (!filterQueryDropdown.contains(event.target)) {
    filterQueryMenu.classList.add("hidden");
  }
});

prevPageButton.addEventListener("click", async () => {
  if (currentPage <= 1) {
    return;
  }

  currentPage -= 1;
  try {
    await loadLeads();
  } catch (error) {
    setExportMessage(error.message, "error");
  }
});

nextPageButton.addEventListener("click", async () => {
  const totalPages = Math.max(1, Math.ceil(totalLeadCount / pageSize));
  if (currentPage >= totalPages) {
    return;
  }

  currentPage += 1;
  try {
    await loadLeads();
  } catch (error) {
    setExportMessage(error.message, "error");
  }
});

paginationButtons.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-page]");
  if (!button) {
    return;
  }

  const targetPage = Number(button.dataset.page);
  if (!Number.isInteger(targetPage) || targetPage === currentPage) {
    return;
  }

  currentPage = targetPage;
  try {
    await loadLeads();
  } catch (error) {
    setExportMessage(error.message, "error");
  }
});

selectAllLeadsCheckbox.addEventListener("change", () => {
  document.querySelectorAll(".row-checkbox").forEach((checkbox) => {
    checkbox.checked = selectAllLeadsCheckbox.checked;
    setLeadSelection(Number(checkbox.dataset.leadId), checkbox.checked);
  });
  refreshOutreachSelectionPanels();
});

leadsTableBody.addEventListener("change", (event) => {
  if (event.target.classList.contains("row-checkbox")) {
    setLeadSelection(Number(event.target.dataset.leadId), event.target.checked);
    updateSelectAllState();
    refreshOutreachSelectionPanels();
  }
});

outreachAvailableList?.addEventListener("change", (event) => {
  const checkbox = event.target.closest(".outreach-available-checkbox");
  if (!checkbox) {
    return;
  }

  const leadId = Number(checkbox.dataset.leadId);
  setLeadSelection(leadId, checkbox.checked);

  const tableCheckbox = document.querySelector(`.row-checkbox[data-lead-id="${leadId}"]`);
  if (tableCheckbox) {
    tableCheckbox.checked = checkbox.checked;
  }

  updateSelectAllState();
  refreshOutreachSelectionPanels();
});

outreachPrevPageButton?.addEventListener("click", async () => {
  if (outreachCurrentPage <= 1) {
    return;
  }

  outreachCurrentPage -= 1;
  try {
    await loadOutreachAvailableLeads();
  } catch (error) {
    outreachAvailableList.innerHTML = `<p class="muted-value">${escapeHtml(error.message)}</p>`;
  }
});

outreachNextPageButton?.addEventListener("click", async () => {
  const totalPages = Math.max(1, Math.ceil(outreachTotalLeadCount / pageSize));
  if (outreachCurrentPage >= totalPages) {
    return;
  }

  outreachCurrentPage += 1;
  try {
    await loadOutreachAvailableLeads();
  } catch (error) {
    outreachAvailableList.innerHTML = `<p class="muted-value">${escapeHtml(error.message)}</p>`;
  }
});

outreachPaginationButtons?.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-page]");
  if (!button) {
    return;
  }

  const targetPage = Number(button.dataset.page);
  if (!Number.isInteger(targetPage) || targetPage === outreachCurrentPage) {
    return;
  }

  outreachCurrentPage = targetPage;
  try {
    await loadOutreachAvailableLeads();
  } catch (error) {
    outreachAvailableList.innerHTML = `<p class="muted-value">${escapeHtml(error.message)}</p>`;
  }
});

selectedOutreachList?.addEventListener("change", (event) => {
  const checkbox = event.target.closest(".selected-outreach-checkbox");
  if (!checkbox) {
    return;
  }

  const leadId = Number(checkbox.dataset.leadId);
  setLeadSelection(leadId, checkbox.checked);

  const tableCheckbox = document.querySelector(`.row-checkbox[data-lead-id="${leadId}"]`);
  if (tableCheckbox) {
    tableCheckbox.checked = checkbox.checked;
  }

  updateSelectAllState();
  refreshOutreachSelectionPanels();
});

leadsTableBody.addEventListener("click", (event) => {
  const whatsappButton = event.target.closest(".row-whatsapp-button");
  if (whatsappButton) {
    const whatsappUrl = buildWhatsappUrl(
      whatsappButton.dataset.phone,
      getTemplateMessage(whatsappButton.dataset.name),
    );
    if (whatsappUrl) {
      createLeadActivitySilently(Number(whatsappButton.dataset.leadId), "whatsapp_opened");
      markLeadContactedSilently(Number(whatsappButton.dataset.leadId));
      window.open(whatsappUrl, "_blank", "noopener,noreferrer");
    }
    return;
  }

  const emailButton = event.target.closest(".row-email-button");
  if (emailButton) {
    const mailtoUrl = buildMailtoUrl(
      emailButton.dataset.email,
      emailSubjectTemplate.value,
      getEmailBodyTemplate(emailButton.dataset.name),
    );
    if (mailtoUrl) {
      createLeadActivitySilently(Number(emailButton.dataset.leadId), "email_opened");
      markLeadContactedSilently(Number(emailButton.dataset.leadId));
      window.location.href = mailtoUrl;
    }
    return;
  }

  const editButton = event.target.closest(".edit-button");
  if (editButton) {
    openEditPanel(Number(editButton.dataset.leadId)).catch((error) => {
      setExportMessage(error.message, "error");
    });
    return;
  }

  const deleteButton = event.target.closest(".delete-lead-button");
  if (deleteButton) {
    deleteLead(Number(deleteButton.dataset.leadId), deleteButton.dataset.businessName)
      .then((deleted) => {
        if (deleted) {
          setExportMessage("Lead kaldırıldı.", "success");
        }
      })
      .catch((error) => {
        setExportMessage(error.message, "error");
      });
  }
});

todayFollowUpList?.addEventListener("click", (event) => {
  const editButton = event.target.closest(".edit-button");
  if (editButton) {
    openEditPanel(Number(editButton.dataset.leadId)).catch((error) => {
      setFollowUpActionMessage(error.message, "error");
    });
    return;
  }

  const deleteButton = event.target.closest(".delete-lead-button");
  if (deleteButton) {
    deleteLead(Number(deleteButton.dataset.leadId), deleteButton.dataset.businessName)
      .then((deleted) => {
        if (deleted) {
          setFollowUpActionMessage("Lead kaldırıldı.", "success");
        }
      })
      .catch((error) => {
        setFollowUpActionMessage(error.message, "error");
      });
  }
});

overdueFollowUpList?.addEventListener("click", (event) => {
  const editButton = event.target.closest(".edit-button");
  if (editButton) {
    openEditPanel(Number(editButton.dataset.leadId)).catch((error) => {
      setFollowUpActionMessage(error.message, "error");
    });
    return;
  }

  const deleteButton = event.target.closest(".delete-lead-button");
  if (deleteButton) {
    deleteLead(Number(deleteButton.dataset.leadId), deleteButton.dataset.businessName)
      .then((deleted) => {
        if (deleted) {
          setFollowUpActionMessage("Lead kaldırıldı.", "success");
        }
      })
      .catch((error) => {
        setFollowUpActionMessage(error.message, "error");
      });
  }
});

whatsappPreparedList.addEventListener("click", (event) => {
  const link = event.target.closest(".prepared-whatsapp-link");
  if (!link) {
    return;
  }

  const leadId = Number(link.dataset.leadId);
  if (leadId) {
    createLeadActivitySilently(leadId, "whatsapp_opened");
    markLeadContactedSilently(leadId);
  }
});

emailPreparedList.addEventListener("click", (event) => {
  const link = event.target.closest(".prepared-email-link");
  if (!link) {
    return;
  }

  const leadId = Number(link.dataset.leadId);
  if (leadId) {
    createLeadActivitySilently(leadId, "email_opened");
    markLeadContactedSilently(leadId);
  }
});

editCancelButton.addEventListener("click", () => {
  closeEditPanel();
});

editPanel.addEventListener("click", async (event) => {
  const actionButton = event.target.closest(".activity-action-button");
  if (!actionButton) {
    return;
  }

  const leadId = Number(document.getElementById("edit-id").value);
  if (!leadId) {
    return;
  }

  try {
    await createLeadActivity(leadId, actionButton.dataset.activityType);
    await loadLeadActivities(leadId);
    setActivityMessage("Aktivite kaydedildi.", "success");
  } catch (error) {
    setActivityMessage(error.message, "error");
  }
});

addActivityNoteButton.addEventListener("click", async () => {
  const leadId = Number(document.getElementById("edit-id").value);
  const activityNote = activityNoteInput.value.trim();

  if (!leadId) {
    return;
  }

  if (!activityNote) {
    setActivityMessage("Lütfen bir not girin.", "error");
    return;
  }

  try {
    await createLeadActivity(leadId, "note_added", activityNote);
    activityNoteInput.value = "";
    await loadLeadActivities(leadId);
    setActivityMessage("Not eklendi.", "success");
  } catch (error) {
    setActivityMessage(error.message, "error");
  }
});

editForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const leadId = Number(document.getElementById("edit-id").value);
  const formData = new FormData(editForm);
  const payload = Object.fromEntries(formData.entries());

  try {
    const response = await fetch(`/api/leads/${leadId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Lead güncellenemedi.");
    }

    goToFirstPage();
    await loadFollowUpSummary();
    await loadLeads();
    setEditMessage("Lead güncellendi.", "success");
  } catch (error) {
    setEditMessage(error.message, "error");
  }
});

exportAllCsvButton.addEventListener("click", async () => {
  try {
    setExportMessage("CSV indiriliyor...");
    await downloadFromGet("/api/export/csv", "tum_leadler.csv");
    setExportMessage("CSV dosyası indirildi.", "success");
  } catch (error) {
    setExportMessage(error.message, "error");
  }
});

exportAllExcelButton.addEventListener("click", async () => {
  try {
    setExportMessage("Excel dosyası indiriliyor...");
    await downloadFromGet("/api/export/excel", "tum_leadler.xlsx");
    setExportMessage("Excel dosyası indirildi.", "success");
  } catch (error) {
    setExportMessage(error.message, "error");
  }
});

exportSelectedCsvButton.addEventListener("click", async () => {
  const selectedIds = getSelectedLeadIds();
  if (!selectedIds.length) {
    setExportMessage("Lütfen dışa aktarmak için en az bir kayıt seçin.", "error");
    return;
  }

  try {
    setExportMessage("Seçili kayıtlar CSV olarak hazırlanıyor...");
    await downloadSelected("/api/export/selected/csv", selectedIds, "secilen_leadler.csv");
    setExportMessage("Seçili kayıtlar CSV olarak indirildi.", "success");
  } catch (error) {
    setExportMessage(error.message, "error");
  }
});

exportSelectedExcelButton.addEventListener("click", async () => {
  const selectedIds = getSelectedLeadIds();
  if (!selectedIds.length) {
    setExportMessage("Lütfen dışa aktarmak için en az bir kayıt seçin.", "error");
    return;
  }

  try {
    setExportMessage("Seçili kayıtlar Excel olarak hazırlanıyor...");
    await downloadSelected("/api/export/selected/excel", selectedIds, "secilen_leadler.xlsx");
    setExportMessage("Seçili kayıtlar Excel olarak indirildi.", "success");
  } catch (error) {
    setExportMessage(error.message, "error");
  }
});

prepareWhatsappButton.addEventListener("click", async () => {
  const selectedIds = getSelectedLeadIds();
  if (!selectedIds.length) {
    setWhatsappPrepareMessage("Seçili kayıt yok.", "error");
    whatsappPreparedPanel.classList.add("hidden");
    return;
  }

  try {
    const response = await fetch("/api/whatsapp/prepare-selected", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        lead_ids: selectedIds,
        message_template: whatsappMessageTemplate.value,
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "WhatsApp hazırlığı yapılamadı.");
    }

    if (!data.contacts.length) {
      setWhatsappPrepareMessage("Geçerli numara bulunamadı.", "error");
      renderPreparedContacts([]);
      return;
    }

    renderPreparedContacts(data.contacts);
    setWhatsappPrepareMessage("WhatsApp bağlantısı hazırlandı.", "success");
  } catch (error) {
    setWhatsappPrepareMessage(error.message, "error");
  }
});

prepareEmailButton.addEventListener("click", async () => {
  const selectedIds = getSelectedLeadIds();
  if (!selectedIds.length) {
    setEmailPrepareMessage("Seçili kayıt yok.", "error");
    emailPreparedPanel.classList.add("hidden");
    return;
  }

  try {
    const response = await fetch("/api/email/prepare-selected", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        lead_ids: selectedIds,
        subject: emailSubjectTemplate.value,
        body_template: emailBodyTemplate.value,
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "E-posta hazırlığı yapılamadı.");
    }

    if (!data.contacts.length) {
      setEmailPrepareMessage("Geçerli e-posta bulunamadı.", "error");
      renderPreparedEmails([]);
      return;
    }

    renderPreparedEmails(data.contacts);
    setEmailPrepareMessage("E-posta bağlantıları hazırlandı.", "success");
  } catch (error) {
    setEmailPrepareMessage(error.message, "error");
  }
});

clearLeadsButton.addEventListener("click", async () => {
  const confirmed = window.confirm("Tüm kayıtlı lead'leri silmek istediğinize emin misiniz?");
  if (!confirmed) {
    return;
  }

  try {
    const response = await fetch("/api/leads", { method: "DELETE" });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Liste temizlenemedi.");
    }

    closeEditPanel();
    whatsappPreparedPanel.classList.add("hidden");
    emailPreparedPanel.classList.add("hidden");
    selectedLeadIds.clear();
    selectedLeadCache.clear();
    renderSelectedOutreachLeads([]);
    renderAvailableOutreachLeads([]);
    goToFirstPage();
    await loadQueryOptions();
    await loadFollowUpSummary();
    await loadLeads();
    setExportMessage(`Liste temizlendi. Silinen kayıt: ${data.deleted_count}`, "success");
  } catch (error) {
    setExportMessage(error.message, "error");
  }
});

scrapeForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (activeScrapeJobId) {
    setScrapeMessage("Zaten devam eden bir tarama var.", "error");
    return;
  }

  setScrapeRunningState(true);
  setScrapeMessage("Tarama devam ediyor, lütfen bekleyin...");

  const formData = new FormData(scrapeForm);
  const maxResults = Number(formData.get("max_results"));

  if (!Number.isInteger(maxResults) || maxResults < 1 || maxResults > 100) {
    setScrapeRunningState(false);
    setScrapeMessage("Maksimum sonuç 1 ile 100 arasında olmalıdır.", "error");
    return;
  }

  const payload = {
    keyword: formData.get("keyword"),
    location: formData.get("location"),
    max_results: maxResults,
  };

  try {
    const response = await fetch("/api/scrape/google-maps", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Tarama başlatılamadı.");
    }

    activeScrapeJobId = data.job_id;
    updateScrapeMeta();
    await pollScrapeStatus();
  } catch (error) {
    setScrapeRunningState(false);
    setScrapeMessage(error.message, "error");
  }
});

leadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  submitButton.disabled = true;
  setFormMessage("Kaydediliyor...");

  const formData = new FormData(leadForm);
  const payload = Object.fromEntries(formData.entries());

  try {
    const response = await fetch("/api/leads", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Lead kaydedilemedi.");
    }

    leadForm.reset();
    goToFirstPage();
    await loadFollowUpSummary();
    await loadLeads();
    setFormMessage("Lead başarıyla kaydedildi.", "success");
  } catch (error) {
    setFormMessage(error.message, "error");
  } finally {
    submitButton.disabled = false;
  }
});

Promise.all([loadQueryOptions(), loadFollowUpSummary(), loadLeads()]).catch((error) => {
  leadsTableBody.innerHTML = `<tr><td colspan="14" class="empty-state">${escapeHtml(error.message)}</td></tr>`;
  setFormMessage("Kayıtlar yüklenemedi.", "error");
});

startScrapeMetaPolling();
