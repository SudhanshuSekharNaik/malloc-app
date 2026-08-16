/**
 * Memora — Intelligent Career & Memory Engine
 * Client Application Logic
 */

// ============================================================================
// State Management
// ============================================================================
const state = {
  userId: localStorage.getItem("memora_user_id") || `user-${Math.random().toString(36).substring(2, 10)}`,
  conversationId: localStorage.getItem("memora_conv_id") || null,
  isRecording: false,
  mediaRecorder: null,
  audioChunks: [],
  selectedImageFile: null,
  recordingStartTime: null,
  recordingTimerInterval: null,
  memories: [],
  activeMemoryFilter: "all",
  resumes: [],
  activeResumeId: null,
  jobs: [],
  dueJobs: [],
  activeJobFilter: "all",
  activeJobSort: "newest",
  lastMatchResult: null,
  lastAtsResult: null,
  suggestedEdits: [],
  lastInsightsResult: null,
  outreachParsedJD: null,
  outreachSelectedRole: null,
  outreachDraft: null,
  gmailConnected: false
};

// Persist user ID immediately
localStorage.setItem("memora_user_id", state.userId);

// ============================================================================
// DOM Element Cache
// ============================================================================
const dom = {
  // Sidebar & Navigation
  userIdDisplay: document.getElementById("user-id-display"),
  convIdDisplay: document.getElementById("conv-id-display"),
  btnNewChat: document.getElementById("btn-new-chat"),
  btnSwitchUser: document.getElementById("btn-switch-user"),
  serverStatus: document.getElementById("server-status"),
  navItems: document.querySelectorAll(".nav-item"),
  tabPanes: document.querySelectorAll(".tab-pane"),
  currentTabTitle: document.getElementById("current-tab-title"),
  currentTabSubtitle: document.getElementById("current-tab-subtitle"),
  memoryCountBadge: document.getElementById("memory-count-badge"),
  jobsDueBadge: document.getElementById("jobs-due-badge"),
  
  // Chat
  chatMessages: document.getElementById("chat-messages"),
  chatForm: document.getElementById("chat-form"),
  chatInput: document.getElementById("chat-input"),
  chatSuggestions: document.getElementById("chat-suggestion-chips"),
  btnVoiceRecord: document.getElementById("btn-voice-record"),
  voiceRecordingBar: document.getElementById("voice-recording-bar"),
  recordingTimer: document.getElementById("recording-timer"),
  btnStopVoice: document.getElementById("btn-stop-voice"),
  btnAttachImage: document.getElementById("btn-attach-image"),
  imageFileInput: document.getElementById("image-file-input"),
  mediaPreview: document.getElementById("media-preview"),
  previewContent: document.getElementById("preview-content"),
  btnCancelMedia: document.getElementById("btn-cancel-media"),
  
  // Memory Vault
  memoriesGrid: document.getElementById("memories-grid"),
  btnRefreshMemories: document.getElementById("btn-refresh-memories"),
  memorySearchInput: document.getElementById("memory-search-input"),
  memoryFilterPills: document.getElementById("memory-filter-pills"),
  countAllMemories: document.getElementById("count-all-memories"),
  countSemanticMemories: document.getElementById("count-semantic-memories"),
  countEpisodicMemories: document.getElementById("count-episodic-memories"),
  
  // Matcher
  matcherJobUrl: document.getElementById("matcher-job-url"),
  btnFetchJob: document.getElementById("btn-fetch-job"),
  fetchBtnText: document.getElementById("fetch-btn-text"),
  matcherBotWarning: document.getElementById("matcher-bot-warning"),
  matcherCompany: document.getElementById("matcher-company"),
  matcherRole: document.getElementById("matcher-role"),
  matcherJdText: document.getElementById("matcher-jd-text"),
  resumeSelectPicker: document.getElementById("resume-select-picker"),
  btnDeleteActiveResume: document.getElementById("btn-delete-active-resume"),
  resumeDropzone: document.getElementById("resume-dropzone"),
  resumeFileInput: document.getElementById("resume-file-input"),
  resumeTitleInput: document.getElementById("resume-title-input"),
  matcherResumeText: document.getElementById("matcher-resume-text"),
  btnSaveResume: document.getElementById("btn-save-resume"),
  btnRunMatch: document.getElementById("btn-run-match"),
  matcherEmptyState: document.getElementById("matcher-empty-state"),
  matcherLoadingState: document.getElementById("matcher-loading-state"),
  matcherResultsView: document.getElementById("matcher-results-view"),
  matchScoreVal: document.getElementById("match-score-val"),
  gaugeCircle: document.getElementById("gauge-circle"),
  matchVerdictPill: document.getElementById("match-verdict-pill"),
  matchTargetRole: document.getElementById("match-target-role"),
  matchTargetCompany: document.getElementById("match-target-company"),
  matchSummaryText: document.getElementById("match-summary-text"),
  matchStrengthsList: document.getElementById("match-strengths-list"),
  matchExperienceFit: document.getElementById("match-experience-fit"),
  skillsMatchedTags: document.getElementById("skills-matched-tags"),
  skillsMissingTags: document.getElementById("skills-missing-tags"),
  matchRecommendationsList: document.getElementById("match-recommendations-list"),
  matchPitchText: document.getElementById("match-pitch-text"),
  btnCopyPitch: document.getElementById("btn-copy-pitch"),
  btnAddMatchedToTracker: document.getElementById("btn-add-matched-to-tracker"),
  
  // Suggested Resume Edits
  btnGenerateEdits: document.getElementById("btn-generate-edits"),
  btnGenerateEditsText: document.getElementById("btn-generate-edits-text"),
  editsLoadingState: document.getElementById("edits-loading-state"),
  editsEmptyState: document.getElementById("edits-empty-state"),
  editsListContainer: document.getElementById("edits-list-container"),

  // ATS Checker
  atsResumeSelectPicker: document.getElementById("ats-resume-select-picker"),
  atsResumeDropzone: document.getElementById("ats-resume-dropzone"),
  atsResumeFileInput: document.getElementById("ats-resume-file-input"),
  atsResumeText: document.getElementById("ats-resume-text"),
  btnRunAtsCheck: document.getElementById("btn-run-ats-check"),
  atsEmptyState: document.getElementById("ats-empty-state"),
  atsLoadingState: document.getElementById("ats-loading-state"),
  atsResultsView: document.getElementById("ats-results-view"),
  atsScoreVal: document.getElementById("ats-score-val"),
  atsGaugeCircle: document.getElementById("ats-gauge-circle"),
  atsVerdictPill: document.getElementById("ats-verdict-pill"),
  atsL1Val: document.getElementById("ats-l1-val"),
  atsL2Val: document.getElementById("ats-l2-val"),
  atsRuleChecksList: document.getElementById("ats-rule-checks-list"),
  atsMlChecksList: document.getElementById("ats-ml-checks-list"),
  atsRecommendationsList: document.getElementById("ats-recommendations-list"),

  // Authenticity Checker
  authJobUrl: document.getElementById("auth-job-url"),
  btnAuthFetchJob: document.getElementById("btn-auth-fetch-job"),
  authFetchBtnText: document.getElementById("auth-fetch-btn-text"),
  authBotWarning: document.getElementById("auth-bot-warning"),
  authCompanyInput: document.getElementById("auth-company-input"),
  authRoleInput: document.getElementById("auth-role-input"),
  authJobText: document.getElementById("auth-job-text"),
  btnRunAuthenticity: document.getElementById("btn-run-authenticity"),
  authBtnLabel: document.getElementById("auth-btn-label"),
  btnAuthPresetSafe: document.getElementById("btn-auth-preset-safe"),
  btnAuthPresetScam: document.getElementById("btn-auth-preset-scam"),
  btnMatcherCheckAuth: document.getElementById("btn-matcher-check-auth"),
  authEmptyState: document.getElementById("auth-empty-state"),
  authLoadingState: document.getElementById("auth-loading-state"),
  authLoadingTitle: document.getElementById("auth-loading-title"),
  authLoadingSubtitle: document.getElementById("auth-loading-subtitle"),
  authResultsView: document.getElementById("auth-results-view"),
  authRiskHero: document.getElementById("auth-risk-hero"),
  authRiskPill: document.getElementById("auth-risk-pill"),
  authRiskScore: document.getElementById("auth-risk-score"),
  authRiskSummary: document.getElementById("auth-risk-summary"),
  authL1Counts: document.getElementById("auth-l1-counts"),
  authLayer1List: document.getElementById("auth-layer1-list"),
  authLayer2Content: document.getElementById("auth-layer2-content"),
  authLayer3Content: document.getElementById("auth-layer3-content"),

  // Company Insights
  insightCompanyInput: document.getElementById("insight-company-input"),
  insightUrlInput: document.getElementById("insight-url-input"),
  insightRoleInput: document.getElementById("insight-role-input"),
  insightAboutInput: document.getElementById("insight-about-input"),
  btnRunInsights: document.getElementById("btn-run-insights"),
  insightBtnLabel: document.getElementById("insight-btn-label"),
  btnInsightPresetStripe: document.getElementById("btn-insight-preset-stripe"),
  btnInsightPresetStartup: document.getElementById("btn-insight-preset-startup"),
  btnInsightPresetConflict: document.getElementById("btn-insight-preset-conflict"),
  btnMatcherInspectInsights: document.getElementById("btn-matcher-inspect-insights"),
  insightEmptyState: document.getElementById("insight-empty-state"),
  insightLoadingState: document.getElementById("insight-loading-state"),
  insightResultsView: document.getElementById("insight-results-view"),
  insightUrlMismatchAlert: document.getElementById("insight-url-mismatch-alert"),
  insightUrlMismatchText: document.getElementById("insight-url-mismatch-text"),
  insightLowDataAlert: document.getElementById("insight-low-data-alert"),
  insightLowDataText: document.getElementById("insight-low-data-text"),
  insightCompanyTitle: document.getElementById("insight-company-title"),
  insightIndustryBadge: document.getElementById("insight-industry-badge"),
  insightSizeLabel: document.getElementById("insight-size-label"),
  insightSizeConfidence: document.getElementById("insight-size-confidence"),
  insightDisagreementAlert: document.getElementById("insight-disagreement-alert"),
  insightAllScoresList: document.getElementById("insight-all-scores-list"),
  insightEmployeesVal: document.getElementById("insight-employees-val"),
  insightFoundedVal: document.getElementById("insight-founded-val"),
  insightSentimentSummary: document.getElementById("insight-sentiment-summary"),
  insightSentimentPosBar: document.getElementById("insight-sentiment-pos-bar"),
  insightSentimentNegBar: document.getElementById("insight-sentiment-neg-bar"),
  insightSentimentBarTrack: document.getElementById("insight-sentiment-bar-track"),
  insightSignalStrengthNote: document.getElementById("insight-signal-strength-note"),
  insightPraisedList: document.getElementById("insight-praised-list"),
  insightCriticizedList: document.getElementById("insight-criticized-list"),
  insightFocusAreasTags: document.getElementById("insight-focus-areas-tags"),
  insightProcessStagesList: document.getElementById("insight-process-stages-list"),
  insightPrepTipsList: document.getElementById("insight-prep-tips-list"),

  // Jobs Tracker
  jobsAlertBanner: document.getElementById("jobs-alert-banner"),
  jobsAlertText: document.getElementById("jobs-alert-text"),
  jobsList: document.getElementById("jobs-list"),
  jobSearchInput: document.getElementById("job-search-input"),
  jobStatusFilter: document.getElementById("job-status-filter"),
  jobSortSelect: document.getElementById("job-sort-select"),
  btnOpenJobModal: document.getElementById("btn-open-job-modal"),
  jobModal: document.getElementById("job-modal"),
  btnCloseModal: document.getElementById("btn-close-modal"),
  btnCancelModal: document.getElementById("btn-cancel-modal"),
  jobForm: document.getElementById("job-form"),
  
  // Stats
  statTotalJobs: document.getElementById("stat-total-jobs"),
  statActiveJobs: document.getElementById("stat-active-jobs"),
  statOfferJobs: document.getElementById("stat-offer-jobs"),
  statRejectedJobs: document.getElementById("stat-rejected-jobs"),
  statDueJobs: document.getElementById("stat-due-jobs"),
  
  // Modals
  profileModal: document.getElementById("profile-modal"),
  btnCloseProfileModal: document.getElementById("btn-close-profile-modal"),
  profileCurrentId: document.getElementById("profile-current-id"),
  btnCopyUserId: document.getElementById("btn-copy-user-id"),
  profileSwitchId: document.getElementById("profile-switch-id"),
  btnApplySwitchUser: document.getElementById("btn-apply-switch-user"),
  btnCreateNewUser: document.getElementById("btn-create-new-user"),
  
  editMemoryModal: document.getElementById("edit-memory-modal"),
  btnCloseEditMemory: document.getElementById("btn-close-edit-memory"),
  btnCancelEditMemory: document.getElementById("btn-cancel-edit-memory"),
  editMemoryForm: document.getElementById("edit-memory-form"),
  editMemoryId: document.getElementById("edit-memory-id"),
  editMemoryContent: document.getElementById("edit-memory-content"),
  editMemoryImportance: document.getElementById("edit-memory-importance"),
  
  btnOpenSettings: document.getElementById("btn-open-settings"),
  settingsModal: document.getElementById("settings-modal"),
  btnCloseSettings: document.getElementById("btn-close-settings"),
  btnCancelSettings: document.getElementById("btn-cancel-settings"),
  settingsForm: document.getElementById("settings-form"),
  settingsLlmProvider: document.getElementById("settings-llm-provider"),
  settingsGroqKey: document.getElementById("settings-groq-key"),
  settingsAnthropicKey: document.getElementById("settings-anthropic-key"),
  groqKeyGroup: document.getElementById("groq-key-group"),
  anthropicKeyGroup: document.getElementById("anthropic-key-group"),

  // Apply via Email (Outreach)
  outreachHeaderAuthPill: document.getElementById("outreach-header-auth-pill"),
  outreachAuthIndicatorDot: document.getElementById("outreach-auth-indicator-dot"),
  outreachHeaderAuthText: document.getElementById("outreach-header-auth-text"),
  outreachStep1Indicator: document.getElementById("outreach-step1-indicator"),
  outreachStep2Indicator: document.getElementById("outreach-step2-indicator"),
  outreachStep3Indicator: document.getElementById("outreach-step3-indicator"),
  outreachStep4Indicator: document.getElementById("outreach-step4-indicator"),
  btnOutreachPresetRayo: document.getElementById("btn-outreach-preset-rayo"),
  outreachResumeSelectPicker: document.getElementById("outreach-resume-select-picker"),
  outreachUrlInput: document.getElementById("outreach-url-input"),
  btnOutreachFetchUrl: document.getElementById("btn-outreach-fetch-url"),
  outreachJdText: document.getElementById("outreach-jd-text"),
  btnParseOutreach: document.getElementById("btn-parse-outreach"),
  outreachStep2Panel: document.getElementById("outreach-step2-panel"),
  outreachStep2Empty: document.getElementById("outreach-step2-empty"),
  outreachStep2Content: document.getElementById("outreach-step2-content"),
  outreachFieldCompany: document.getElementById("outreach-field-company"),
  outreachFieldEmail: document.getElementById("outreach-field-email"),
  outreachEmailMissingNote: document.getElementById("outreach-email-missing-note"),
  outreachFieldPhone: document.getElementById("outreach-field-phone"),
  outreachFieldLocation: document.getElementById("outreach-field-location"),
  outreachFieldExp: document.getElementById("outreach-field-exp"),
  outreachFieldDays: document.getElementById("outreach-field-days"),
  outreachRoleRecommendationBox: document.getElementById("outreach-role-recommendation-box"),
  outreachRoleRecommendationText: document.getElementById("outreach-role-recommendation-text"),
  outreachRoleOptionsContainer: document.getElementById("outreach-role-options-container"),
  outreachApplicantName: document.getElementById("outreach-applicant-name"),
  outreachCustomInstructions: document.getElementById("outreach-custom-instructions"),
  btnDraftOutreach: document.getElementById("btn-draft-outreach"),
  outreachStep3Empty: document.getElementById("outreach-step3-empty"),
  outreachStep3Loading: document.getElementById("outreach-step3-loading"),
  outreachStep3Content: document.getElementById("outreach-step3-content"),
  outreachEmailSubject: document.getElementById("outreach-email-subject"),
  outreachEmailBody: document.getElementById("outreach-email-body"),
  outreachClicheStatusTag: document.getElementById("outreach-cliche-status-tag"),
  outreachFabricationAuditBox: document.getElementById("outreach-fabrication-audit-box"),
  outreachFabricationSummaryTag: document.getElementById("outreach-fabrication-summary-tag"),
  outreachFabricationFlagsList: document.getElementById("outreach-fabrication-flags-list"),
  outreachAiDetectorBox: document.getElementById("outreach-ai-detector-box"),
  outreachDetectorScoreText: document.getElementById("outreach-detector-score-text"),
  outreachEmailRecipientConfirm: document.getElementById("outreach-email-recipient-confirm"),
  outreachAuthCardDot: document.getElementById("outreach-auth-card-dot"),
  outreachAuthCardStatus: document.getElementById("outreach-auth-card-status"),
  outreachAuthCardDesc: document.getElementById("outreach-auth-card-desc"),
  btnOutreachConnectGmail: document.getElementById("btn-outreach-connect-gmail"),
  btnOutreachDisconnectGmail: document.getElementById("btn-outreach-disconnect-gmail"),
  outreachAttachResumeCheckbox: document.getElementById("outreach-attach-resume-checkbox"),
  outreachLogTrackerCheckbox: document.getElementById("outreach-log-tracker-checkbox"),
  btnSendOutreach: document.getElementById("btn-send-outreach"),
  outreachSendResultCard: document.getElementById("outreach-send-result-card"),
  outreachResultMsgId: document.getElementById("outreach-result-msg-id"),
  outreachResultTimestamp: document.getElementById("outreach-result-timestamp"),
  outreachResultRecipient: document.getElementById("outreach-result-recipient"),
  btnOutreachGotoTracker: document.getElementById("btn-outreach-goto-tracker"),
  btnMatcherApplyEmail: document.getElementById("btn-matcher-apply-email"),
  
  // Toast
  toastContainer: document.getElementById("toast-container")
};

// ============================================================================
// Initialization
// ============================================================================
document.addEventListener("DOMContentLoaded", () => {
  renderUserInfo();
  setupNavigation();
  setupProfileModal();
  setupChatHandlers();
  setupVoiceAndMedia();
  setupMemoryVaultHandlers();
  setupMatcherHandlers();
  setupSuggestedEditsHandlers();
  setupAtsCheckerHandlers();
  setupAuthenticityHandlers();
  setupCompanyInsightsHandlers();
  setupOutreachHandlers();
  setupJobHandlers();
  setupSettingsHandlers();
  checkHealth();
  
  // Load initial data
  loadMemories();
  loadResumes();
  loadJobs();
  loadSettings();
  checkGmailStatus();
  
  // Poll health and due follow-ups periodically
  setInterval(checkHealth, 30000);
});

function renderUserInfo() {
  if (dom.userIdDisplay) dom.userIdDisplay.textContent = state.userId;
  if (dom.convIdDisplay) dom.convIdDisplay.textContent = state.conversationId ? state.conversationId.substring(0, 8) + '...' : "(new)";
  if (dom.profileCurrentId) dom.profileCurrentId.value = state.userId;
  const sidebarUserId = document.getElementById("sidebar-user-id");
  if (sidebarUserId) sidebarUserId.textContent = state.userId.substring(0, 10);
}

// ============================================================================
// Navigation & Tabs (Desktop Sidebar + Mobile Drawer & Bottom Bar)
// ============================================================================
function setupNavigation() {
  const sidebar = document.getElementById("main-sidebar");
  const backdrop = document.getElementById("sidebar-backdrop");
  const btnToggle = document.getElementById("btn-toggle-sidebar");
  const btnClose = document.getElementById("btn-close-sidebar");
  const mobileNavBtns = document.querySelectorAll(".mobile-nav-btn");

  function closeMobileSidebar() {
    if (sidebar) sidebar.classList.remove("mobile-open");
    if (backdrop) backdrop.classList.remove("active");
  }

  function openMobileSidebar() {
    if (sidebar) sidebar.classList.add("mobile-open");
    if (backdrop) backdrop.classList.add("active");
  }

  if (btnToggle) {
    btnToggle.addEventListener("click", () => {
      if (sidebar && sidebar.classList.contains("mobile-open")) {
        closeMobileSidebar();
      } else {
        openMobileSidebar();
      }
    });
  }

  if (btnClose) {
    btnClose.addEventListener("click", closeMobileSidebar);
  }

  if (backdrop) {
    backdrop.addEventListener("click", closeMobileSidebar);
  }

  dom.navItems.forEach(item => {
    item.addEventListener("click", () => {
      const tabId = item.getAttribute("data-tab");
      switchTab(tabId);
      closeMobileSidebar();
    });
  });

  mobileNavBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const tabId = btn.getAttribute("data-tab");
      switchTab(tabId);
      closeMobileSidebar();
    });
  });

  if (dom.btnNewChat) {
    dom.btnNewChat.addEventListener("click", () => {
      state.conversationId = null;
      localStorage.removeItem("memora_conv_id");
      renderUserInfo();
      resetChatView();
      closeMobileSidebar();
      showToast("Started new terminal session", "info");
    });
  }
}

function switchTab(tabId) {
  dom.navItems.forEach(nav => {
    const isActive = nav.getAttribute("data-tab") === tabId;
    nav.classList.toggle("active", isActive);
  });

  document.querySelectorAll(".mobile-nav-btn").forEach(btn => {
    const isActive = btn.getAttribute("data-tab") === tabId;
    btn.classList.toggle("active", isActive);
  });

  dom.tabPanes.forEach(pane => {
    pane.classList.toggle("active", pane.id === tabId);
  });

  const tabTitles = {
    "tab-chat": { title: "TERMINAL_SESSION", subtitle: "// System initialized. Active memory extraction online." },
    "tab-memory": { title: "MEMORY_VAULT_SYS", subtitle: "// Persistent structured extractions. Synthesized knowledge base." },
    "tab-matcher": { title: "RESUME_MATCHER_SYS", subtitle: "// Deep comparative technical fit & outreach composition" },
    "tab-ats": { title: "ATS_PARSEABILITY_AUDIT", subtitle: "// Rule-based structure validation + HuggingFace BERT entity signals" },
    "tab-authenticity": { title: "JOB_AUTHENTICITY_AUDIT", subtitle: "// Hybrid 3-Layer fraud risk detection & RAG reasoning engine" },
    "tab-insights": { title: "COMPANY_INSIGHTS_SYS", subtitle: "// Multi-layer size classification, industry tagging & culture sentiment" },
    "tab-outreach": { title: "APPLY_VIA_EMAIL_SYS", subtitle: "// Informal JD extraction, resume-grounded drafting, fabrication audit & Gmail sender" },
    "tab-jobs": { title: "JOB_TRACKER_SYS", subtitle: "// Monitoring active engagements & follow-up timelines" },
    "tab-docs": { title: "API_SWAGGER_EXPLORER", subtitle: "// FastAPI OpenAPI interactive documentation" }
  };

  if (tabTitles[tabId]) {
    if (dom.currentTabTitle) dom.currentTabTitle.textContent = tabTitles[tabId].title;
    if (dom.currentTabSubtitle) dom.currentTabSubtitle.textContent = tabTitles[tabId].subtitle;
  }

  if (tabId === "tab-memory") {
    loadMemories();
  } else if (tabId === "tab-jobs") {
    loadJobs();
  } else if (tabId === "tab-matcher" || tabId === "tab-ats" || tabId === "tab-outreach") {
    loadResumes();
    if (tabId === "tab-outreach") {
      checkGmailStatus();
    }
  }
}

// ============================================================================
// User Profile & Session Modal
// ============================================================================
function setupProfileModal() {
  if (dom.btnSwitchUser) {
    dom.btnSwitchUser.addEventListener("click", () => {
      dom.profileCurrentId.value = state.userId;
      dom.profileModal.classList.remove("hidden");
    });
  }

  if (dom.btnCloseProfileModal) {
    dom.btnCloseProfileModal.addEventListener("click", () => {
      dom.profileModal.classList.add("hidden");
    });
  }

  if (dom.btnCopyUserId) {
    dom.btnCopyUserId.addEventListener("click", () => {
      navigator.clipboard.writeText(state.userId);
      showToast("User ID copied to clipboard!", "success");
    });
  }

  if (dom.btnApplySwitchUser) {
    dom.btnApplySwitchUser.addEventListener("click", () => {
      const newId = dom.profileSwitchId.value.trim();
      if (!newId) {
        showToast("Please enter a valid user ID", "error");
        return;
      }
      state.userId = newId;
      state.conversationId = null;
      localStorage.setItem("memora_user_id", newId);
      localStorage.removeItem("memora_conv_id");
      dom.profileModal.classList.add("hidden");
      renderUserInfo();
      resetChatView();
      loadMemories();
      loadResumes();
      loadJobs();
      showToast(`Switched profile to ${newId}`, "success");
    });
  }

  if (dom.btnCreateNewUser) {
    dom.btnCreateNewUser.addEventListener("click", () => {
      const newId = `user-${Math.random().toString(36).substring(2, 10)}`;
      state.userId = newId;
      state.conversationId = null;
      localStorage.setItem("memora_user_id", newId);
      localStorage.removeItem("memora_conv_id");
      dom.profileModal.classList.add("hidden");
      renderUserInfo();
      resetChatView();
      loadMemories();
      loadResumes();
      loadJobs();
      showToast(`Created new profile ${newId}`, "success");
    });
  }
}

// ============================================================================
// AI Assistant & Dynamic Chips
// ============================================================================
function setupChatHandlers() {
  dom.chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = dom.chatInput.value.trim();
    if (!text && !state.selectedImageFile) return;

    let messageToSend = text;
    dom.chatInput.value = "";

    // If an image was attached, caption it first
    if (state.selectedImageFile) {
      const caption = await handleImageCaptioning(state.selectedImageFile);
      if (caption) {
        messageToSend = messageToSend
          ? `${messageToSend}\n[Attached image: "${caption}"]`
          : `[Attached image: "${caption}"]`;
      }
      clearMediaPreview();
    }

    if (!messageToSend.trim()) return;

    appendMessage("user", messageToSend);
    const typingId = showTypingIndicator();

    try {
      const resp = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_external_id: state.userId,
          conversation_id: state.conversationId,
          message: messageToSend
        })
      });

      removeTypingIndicator(typingId);

      if (!resp.ok) {
        const errorData = await resp.json().catch(() => ({}));
        if (resp.status === 404 && errorData.detail && errorData.detail.includes("Conversation not found")) {
          // If conversation ID is from a previous deployment, clear stale ID and retry immediately
          state.conversationId = null;
          localStorage.removeItem("memora_conv_id");
          const retryResp = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              user_external_id: state.userId,
              conversation_id: null,
              message: messageToSend
            })
          });
          if (retryResp.ok) {
            const data = await retryResp.json();
            state.conversationId = data.conversation_id;
            localStorage.setItem("memora_conv_id", data.conversation_id);
            renderUserInfo();
            appendMessage("assistant", data.reply);
            setTimeout(loadMemories, 2500);
            return;
          }
        }
        throw new Error(errorData.detail || `Server returned ${resp.status}`);
      }

      const data = await resp.json();
      state.conversationId = data.conversation_id;
      localStorage.setItem("memora_conv_id", data.conversation_id);
      renderUserInfo();

      appendMessage("assistant", data.reply);

      // Auto-refresh memories in background after chat turn
      setTimeout(loadMemories, 2500);

    } catch (err) {
      removeTypingIndicator(typingId);
      appendMessage("assistant", `⚠️ Error: ${err.message}. You can configure your Groq API key in Settings.`);
      showToast(err.message, "error");
    }
  });
}

function useSuggestion(text) {
  dom.chatInput.value = text;
  dom.chatInput.focus();
}
window.useSuggestion = useSuggestion;

function updateDynamicSuggestionChips(memories) {
  if (!dom.chatSuggestions) return;

  if (!memories || memories.length === 0) {
    dom.chatSuggestions.innerHTML = `
      <button class="suggestion-chip" onclick="useSuggestion('I am a Senior Software Engineer specializing in Python and FastAPI.')">💼 Set career profile</button>
      <button class="suggestion-chip" onclick="useSuggestion('My favorite language is Rust and I love building distributed systems.')">🦀 Set preferences</button>
      <button class="suggestion-chip" onclick="useSuggestion('What do you know about me so far?')">🔍 Test memory retrieval</button>
    `;
    return;
  }

  const chips = [
    `<button class="suggestion-chip" onclick="useSuggestion('Based on my background, what career paths or roles best suit me?')">🎯 Suggest matching roles</button>`,
    `<button class="suggestion-chip" onclick="useSuggestion('What specific skills and preferences do you remember about me?')">🧠 What do you know about me?</button>`,
    `<button class="suggestion-chip" onclick="useSuggestion('Help me draft a compelling intro pitch highlighting my key strengths.')">📝 Draft personal pitch</button>`
  ];

  dom.chatSuggestions.innerHTML = chips.join("");
}

function appendMessage(role, content) {
  const msgEl = document.createElement("div");
  msgEl.className = `w-full my-4 flex ${role === 'user' ? 'justify-end' : 'justify-start'}`;
  
  const now = new Date();
  const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  if (role === "user") {
    msgEl.innerHTML = `
      <div class="flex gap-3 max-w-3xl flex-row-reverse w-full">
        <div class="w-9 h-9 border border-secondary/50 bg-secondary/10 flex items-center justify-center shrink-0 shadow-[0_0_10px_rgba(125,244,255,0.2)] rounded-sm">
          <span class="material-symbols-outlined text-secondary text-[20px]">person</span>
        </div>
        <div class="flex-1 flex flex-col items-end">
          <div class="flex items-baseline gap-3 mb-1.5 flex-row-reverse">
            <span class="font-label-mono text-[11px] font-bold text-secondary uppercase">OPERATOR</span>
            <span class="font-label-mono text-[10px] text-on-surface-variant">${timeStr}</span>
          </div>
          <div class="border border-secondary/50 bg-secondary/10 text-on-surface p-4 tech-card font-body-md text-[13.5px] glow-secondary max-w-2xl leading-relaxed text-left">
            ${escapeHtml(content).replace(/\n/g, '<br>')}
          </div>
        </div>
      </div>
    `;
  } else {
    msgEl.innerHTML = `
      <div class="flex gap-3 max-w-3xl w-full">
        <div class="w-9 h-9 border border-primary/50 bg-primary/10 flex items-center justify-center shrink-0 shadow-[0_0_10px_rgba(242,175,255,0.2)] rounded-sm">
          <span class="material-symbols-outlined text-primary text-[20px]" style="font-variation-settings: 'FILL' 1;">smart_toy</span>
        </div>
        <div class="flex-1">
          <div class="flex items-baseline gap-3 mb-1.5">
            <span class="font-label-mono text-[11px] font-bold text-primary">malloc()_core</span>
            <span class="font-label-mono text-[10px] text-on-surface-variant">${timeStr}</span>
          </div>
          <div class="border border-outline-variant bg-surface-container p-4 tech-card font-body-md text-[13.5px] text-on-surface leading-relaxed">
            ${escapeHtml(content).replace(/\n/g, '<br>')}
          </div>
        </div>
      </div>
    `;
  }

  dom.chatMessages.appendChild(msgEl);
  dom.chatMessages.scrollTop = dom.chatMessages.scrollHeight;
}

function showTypingIndicator() {
  const id = `typing-${Date.now()}`;
  const el = document.createElement("div");
  el.id = id;
  el.className = "w-full my-4 flex justify-start";
  el.innerHTML = `
    <div class="flex gap-3 max-w-3xl w-full">
      <div class="w-9 h-9 border border-primary/50 bg-primary/10 flex items-center justify-center shrink-0 shadow-[0_0_10px_rgba(242,175,255,0.2)] rounded-sm">
        <span class="material-symbols-outlined text-primary text-[20px]" style="font-variation-settings: 'FILL' 1;">smart_toy</span>
      </div>
      <div class="flex-1">
        <div class="flex items-baseline gap-3 mb-1.5">
          <span class="font-label-mono text-[11px] font-bold text-primary">malloc()_core</span>
          <span class="font-label-mono text-[10px] text-primary animate-pulse uppercase">Processing...</span>
        </div>
        <div class="border border-outline-variant bg-surface-container p-3 font-label-mono text-[11px] text-primary flex items-center gap-2 w-fit tech-card">
          <span class="w-1.5 h-3.5 bg-primary shadow-[0_0_5px_#f2afff] animate-pulse inline-block"></span>
          <span>&gt; Querying Memory Vault & Processing Input...</span>
        </div>
      </div>
    </div>
  `;
  dom.chatMessages.appendChild(el);
  dom.chatMessages.scrollTop = dom.chatMessages.scrollHeight;
  return id;
}

function removeTypingIndicator(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function resetChatView() {
  dom.chatMessages.innerHTML = `
    <div class="w-full max-w-3xl my-2">
      <div class="assistant-bubble space-y-3">
        <div class="flex items-center gap-2.5">
          <div class="w-7 h-7 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <span class="material-symbols-outlined text-[16px]" style="font-variation-settings: 'FILL' 1;">smart_toy</span>
          </div>
          <span class="text-[13px] font-semibold text-white">malloc() Assistant</span>
          <span class="text-[10px] font-mono text-indigo-400/80 px-2 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/20">Continuous Memory</span>
        </div>
        
        <p class="text-[13.5px] text-slate-300 leading-relaxed">
          Hello! I'm your AI career partner with persistent long-term memory. Talk with me, record voice messages, or upload documents. Everything you share is securely retained and indexed.
        </p>

        <div class="pt-2 border-t border-white/[0.06]">
          <p class="text-[11px] font-medium text-slate-400 mb-2 uppercase tracking-wide font-mono">Suggested Quick Prompts</p>
          <div class="flex flex-wrap gap-2" id="chat-suggestion-chips">
            <button class="suggestion-chip" onclick="useSuggestion('I am a Senior Software Engineer specializing in Python and FastAPI.')">💼 Set career profile</button>
            <button class="suggestion-chip" onclick="useSuggestion('My favorite language is Rust and I love building distributed systems.')">🦀 Set preferences</button>
            <button class="suggestion-chip" onclick="useSuggestion('What do you know about me so far?')">🔍 Test memory retrieval</button>
          </div>
        </div>
      </div>
    </div>
  `;
}

// ============================================================================
// Voice & Media Handlers
// ============================================================================
function setupVoiceAndMedia() {
  dom.btnVoiceRecord.addEventListener("click", toggleVoiceRecording);
  dom.btnStopVoice.addEventListener("click", toggleVoiceRecording);

  dom.btnAttachImage.addEventListener("click", () => dom.imageFileInput.click());
  dom.imageFileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      handleImageSelected(e.target.files[0]);
    }
  });

  dom.btnCancelMedia.addEventListener("click", clearMediaPreview);
}

async function toggleVoiceRecording() {
  if (state.isRecording) {
    // Stop recording
    state.isRecording = false;
    dom.btnVoiceRecord.classList.remove("recording");
    dom.voiceRecordingBar.classList.add("hidden");
    clearInterval(state.recordingTimerInterval);

    if (state.mediaRecorder && state.mediaRecorder.state !== "inactive") {
      state.mediaRecorder.stop();
    }
  } else {
    // Start recording
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      state.audioChunks = [];
      state.mediaRecorder = new MediaRecorder(stream);

      state.mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) state.audioChunks.push(e.data);
      };

      state.mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(state.audioChunks, { type: "audio/wav" });
        stream.getTracks().forEach(t => t.stop());
        await processAudioTranscription(audioBlob);
      };

      state.mediaRecorder.start();
      state.isRecording = true;
      dom.btnVoiceRecord.classList.add("recording");
      dom.voiceRecordingBar.classList.remove("hidden");

      state.recordingStartTime = Date.now();
      dom.recordingTimer.textContent = "0:00";
      state.recordingTimerInterval = setInterval(() => {
        const sec = Math.floor((Date.now() - state.recordingStartTime) / 1000);
        const mins = Math.floor(sec / 60);
        const remSec = sec % 60;
        dom.recordingTimer.textContent = `${mins}:${remSec < 10 ? '0' : ''}${remSec}`;
      }, 1000);

      showToast("Recording audio... Speak now!", "info");
    } catch (err) {
      showToast(`Microphone access error: ${err.message}`, "error");
    }
  }
}

async function processAudioTranscription(blob) {
  showToast("Transcribing voice with Whisper...", "info");
  const formData = new FormData();
  formData.append("file", blob, "recording.wav");

  try {
    const resp = await fetch("/media/transcribe", { method: "POST", body: formData });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || "Transcription failed");
    }
    const data = await resp.json();
    if (data.text) {
      dom.chatInput.value = data.text;
      dom.chatInput.focus();
      showToast("Voice transcribed successfully!", "success");
    }
  } catch (err) {
    showToast(`Whisper transcription error: ${err.message}`, "error");
  }
}

function handleImageSelected(file) {
  state.selectedImageFile = file;
  dom.previewContent.innerHTML = `
    <span class="preview-tag">🖼️ Image: <strong>${escapeHtml(file.name)}</strong> (${(file.size / 1024).toFixed(1)} KB)</span>
  `;
  dom.mediaPreview.classList.remove("hidden");
}

function clearMediaPreview() {
  state.selectedImageFile = null;
  dom.imageFileInput.value = "";
  dom.mediaPreview.classList.add("hidden");
  dom.previewContent.innerHTML = "";
}

async function handleImageCaptioning(file) {
  showToast("Analyzing image with BLIP...", "info");
  const formData = new FormData();
  formData.append("file", file);

  try {
    const resp = await fetch("/media/caption", { method: "POST", body: formData });
    if (!resp.ok) {
      return `Image file: ${file.name}`;
    }
    const data = await resp.json();
    return data.caption || `Image file: ${file.name}`;
  } catch {
    return `Image file: ${file.name}`;
  }
}

// ============================================================================
// Memory Vault & Management
// ============================================================================
function setupMemoryVaultHandlers() {
  dom.btnRefreshMemories.addEventListener("click", () => {
    loadMemories();
    showToast("Memory Vault synced!", "info");
  });

  dom.memorySearchInput.addEventListener("input", filterAndRenderMemories);

  if (dom.memoryFilterPills) {
    dom.memoryFilterPills.addEventListener("click", (e) => {
      const pill = e.target.closest(".pill");
      if (!pill) return;
      dom.memoryFilterPills.querySelectorAll(".pill").forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      state.activeMemoryFilter = pill.getAttribute("data-filter");
      filterAndRenderMemories();
    });
  }

  // Edit Memory Modal Handlers
  if (dom.btnCloseEditMemory) {
    dom.btnCloseEditMemory.addEventListener("click", () => dom.editMemoryModal.classList.add("hidden"));
  }
  if (dom.btnCancelEditMemory) {
    dom.btnCancelEditMemory.addEventListener("click", () => dom.editMemoryModal.classList.add("hidden"));
  }
  if (dom.editMemoryForm) {
    dom.editMemoryForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const id = dom.editMemoryId.value;
      const content = dom.editMemoryContent.value.trim();
      const importance = parseFloat(dom.editMemoryImportance.value) || 0.5;

      try {
        const resp = await fetch(`/memories/${id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content, importance })
        });
        if (!resp.ok) throw new Error("Failed to update memory");
        dom.editMemoryModal.classList.add("hidden");
        showToast("Memory updated successfully!", "success");
        loadMemories();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }
}

async function loadMemories() {
  try {
    const resp = await fetch(`/memories/${state.userId}`);
    if (!resp.ok) return;

    const data = await resp.json();
    state.memories = data;
    if (dom.memoryCountBadge) dom.memoryCountBadge.textContent = data.length;
    const sidebarVaultCount = document.getElementById("sidebar-vault-count");
    if (sidebarVaultCount) sidebarVaultCount.textContent = data.length;

    const semantic = data.filter(m => m.memory_type === "semantic").length;
    const episodic = data.filter(m => m.memory_type === "episodic").length;

    if (dom.countAllMemories) dom.countAllMemories.textContent = data.length;
    if (dom.countSemanticMemories) dom.countSemanticMemories.textContent = semantic;
    if (dom.countEpisodicMemories) dom.countEpisodicMemories.textContent = episodic;

    filterAndRenderMemories();
    updateDynamicSuggestionChips(data);
  } catch (err) {
    console.error("Failed to load memories:", err);
  }
}

function filterAndRenderMemories() {
  const query = (dom.memorySearchInput ? dom.memorySearchInput.value : "").toLowerCase().trim();
  const filter = state.activeMemoryFilter;

  let list = state.memories;
  if (filter !== "all") {
    list = list.filter(m => m.memory_type === filter);
  }
  if (query) {
    list = list.filter(m => m.content.toLowerCase().includes(query));
  }

  if (!list.length) {
    dom.memoriesGrid.innerHTML = `
      <div class="col-span-full py-12 flex items-center justify-center">
        <div class="w-full max-w-5xl grid grid-cols-1 md:grid-cols-12 gap-6">
          <div class="md:col-span-8 bg-surface-container border border-outline-variant/50 p-8 md:p-12 flex flex-col items-center justify-center text-center tech-card glow-primary relative overflow-hidden group">
            <div class="w-20 h-20 mb-6 bg-background border border-primary/50 flex items-center justify-center glow-primary rounded-sm">
              <span class="material-symbols-outlined text-[42px] text-primary text-glow-primary">psychology</span>
            </div>
            <h3 class="font-headline-lg text-[22px] font-bold text-on-surface mb-3">${state.memories.length === 0 ? "NO_MEMORIES_EXTRACTED_YET" : "NO_MATCHING_RECORDS"}</h3>
            <p class="font-body-md text-body-md text-on-surface-variant max-w-md mb-6">
              ${state.memories.length === 0 ? "The Memory Vault is currently empty. As you interact with the AI Assistant or upload resumes, structured entities will be automatically indexed here." : "Try adjusting your search query or filter tags."}
            </p>
            <button onclick="switchTab('tab-chat')" class="px-6 py-2.5 bg-primary/10 border border-primary text-primary font-label-mono text-label-mono font-bold hover:bg-primary hover:text-background transition-all glow-primary flex items-center gap-2">
              <span class="material-symbols-outlined text-[18px]">terminal</span>
              <span>INITIATE_CONVERSATION</span>
            </button>
          </div>

          <div class="md:col-span-4 flex flex-col gap-4">
            <div class="bg-surface-container border border-outline-variant/50 p-5 tech-card glow-secondary flex-1">
              <div class="flex items-center gap-2 mb-3 pb-3 border-b border-outline-variant/30">
                <span class="material-symbols-outlined text-secondary text-[18px]">memory</span>
                <h4 class="font-label-mono text-label-mono text-secondary uppercase">SYSTEM_STATUS</h4>
              </div>
              <ul class="space-y-3 font-label-mono text-[11px] text-on-surface-variant">
                <li class="flex justify-between items-center">
                  <span>EXTRACTION_ENGINE</span>
                  <span class="text-secondary font-bold text-glow-secondary">ONLINE</span>
                </li>
                <li class="flex justify-between items-center">
                  <span>VECTOR_INDEX</span>
                  <span class="text-primary font-bold">${state.memories.length}_ENTITIES</span>
                </li>
                <li class="flex justify-between items-center">
                  <span>SYNC_LATENCY</span>
                  <span class="text-primary font-bold">12ms</span>
                </li>
              </ul>
            </div>

            <div class="bg-surface-container border border-outline-variant/50 p-5 tech-card glow-primary flex-1">
              <div class="flex items-center gap-2 mb-3 pb-3 border-b border-outline-variant/30">
                <span class="material-symbols-outlined text-primary text-[18px]">schema</span>
                <h4 class="font-label-mono text-label-mono text-primary uppercase text-glow-primary">EXPECTED_SCHEMA</h4>
              </div>
              <div class="bg-background border border-outline-variant/30 p-3 font-label-mono text-[10px] text-on-surface-variant rounded-sm">
                <pre class="whitespace-pre-wrap text-primary/80"><code>{
  "entity_type": "Skill",
  "value": "Python, FastAPI",
  "confidence": 0.98
}</code></pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
    return;
  }

  dom.memoriesGrid.innerHTML = list.map(m => `
    <div class="memory-card">
      <div class="memory-card-header">
        <span class="memory-type-badge memory-type-${m.memory_type}">
          <span class="material-symbols-outlined text-[14px]">${m.memory_type === 'semantic' ? 'lightbulb' : 'event'}</span>
          <span>${m.memory_type === 'semantic' ? 'Fact / Skill' : 'Experience'}</span>
        </span>
        <div class="flex items-center gap-1">
          <button class="btn-card-action" onclick="openEditMemoryModal('${m.id}')" title="Edit memory">
            <span class="material-symbols-outlined text-[14px] text-slate-300">edit</span>
          </button>
          <button class="btn-card-action danger" onclick="deleteMemory('${m.id}')" title="Delete memory">
            <span class="material-symbols-outlined text-[14px] text-rose-400">delete</span>
          </button>
        </div>
      </div>
      <div class="memory-content">${escapeHtml(m.content)}</div>
      <div class="memory-meta">
        <span>Importance: <strong class="text-indigo-300 font-mono">${Math.round((m.importance || 0.5) * 100)}%</strong></span>
        <span>${(m.created_at || '').substring(0, 10)}</span>
      </div>
    </div>
  `).join("");
}

window.openEditMemoryModal = function(id) {
  const memory = state.memories.find(m => m.id === id);
  if (!memory) return;
  dom.editMemoryId.value = memory.id;
  dom.editMemoryContent.value = memory.content;
  dom.editMemoryImportance.value = memory.importance || 0.5;
  dom.editMemoryModal.classList.remove("hidden");
};

window.deleteMemory = async function(id) {
  if (!confirm("Are you sure you want to remove this memory fact?")) return;
  try {
    const resp = await fetch(`/memories/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error("Failed to delete memory");
    showToast("Memory removed", "info");
    loadMemories();
  } catch (err) {
    showToast(err.message, "error");
  }
};

// ============================================================================
// Multi-Resume Management & Job Matcher
// ============================================================================
function setupMatcherHandlers() {
  // 1. Fetch Job from URL
  dom.btnFetchJob.addEventListener("click", async () => {
    const url = dom.matcherJobUrl.value.trim();
    if (!url) {
      showToast("Please enter a valid job posting URL", "error");
      dom.matcherJobUrl.focus();
      return;
    }

    dom.fetchBtnText.textContent = "⏳ Fetching...";
    dom.btnFetchJob.disabled = true;
    dom.matcherBotWarning.classList.add("hidden");

    try {
      const resp = await fetch("/matcher/fetch-job", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url })
      });

      if (!resp.ok) throw new Error("Failed to fetch job details");

      const data = await resp.json();
      if (data.company && !dom.matcherCompany.value) dom.matcherCompany.value = data.company;
      if (data.role_title && !dom.matcherRole.value) dom.matcherRole.value = data.role_title;
      
      if (data.description) {
        dom.matcherJdText.value = data.description;
      }

      if (!data.success) {
        dom.matcherBotWarning.classList.remove("hidden");
        showToast("Job page requires login. Please paste description text below.", "warning");
      } else {
        showToast("Job extracted successfully!", "success");
      }
    } catch (err) {
      dom.matcherBotWarning.classList.remove("hidden");
      showToast(`Fetch notice: ${err.message}. Please paste job description manually.`, "warning");
    } finally {
      dom.fetchBtnText.textContent = "⚡ Fetch Job";
      dom.btnFetchJob.disabled = false;
    }
  });

  // 2. Multi-Resume Selector & Drag and Drop
  dom.resumeSelectPicker.addEventListener("change", () => {
    const selectedId = dom.resumeSelectPicker.value;
    if (selectedId === "new") {
      state.activeResumeId = null;
      dom.matcherResumeText.value = "";
      dom.resumeTitleInput.value = "";
      dom.btnDeleteActiveResume.classList.add("hidden");
    } else {
      const resume = state.resumes.find(r => r.id === selectedId);
      if (resume) {
        state.activeResumeId = resume.id;
        dom.matcherResumeText.value = resume.resume_text;
        dom.resumeTitleInput.value = resume.title;
        dom.btnDeleteActiveResume.classList.remove("hidden");
      }
    }
  });

  dom.btnDeleteActiveResume.addEventListener("click", async () => {
    if (!state.activeResumeId) return;
    if (!confirm("Are you sure you want to delete this saved resume profile?")) return;

    try {
      const resp = await fetch(`/matcher/resumes/${state.activeResumeId}`, { method: "DELETE" });
      if (!resp.ok) throw new Error("Failed to delete resume");
      showToast("Resume profile deleted", "info");
      loadResumes();
    } catch (err) {
      showToast(err.message, "error");
    }
  });

  dom.resumeDropzone.addEventListener("click", () => dom.resumeFileInput.click());

  dom.resumeDropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dom.resumeDropzone.style.borderColor = "var(--accent-primary)";
  });

  dom.resumeDropzone.addEventListener("dragleave", () => {
    dom.resumeDropzone.style.borderColor = "var(--border-color)";
  });

  dom.resumeDropzone.addEventListener("drop", async (e) => {
    e.preventDefault();
    dom.resumeDropzone.style.borderColor = "var(--border-color)";
    if (e.dataTransfer.files.length > 0) {
      await handleResumeFileUpload(e.dataTransfer.files[0]);
    }
  });

  dom.resumeFileInput.addEventListener("change", async (e) => {
    if (e.target.files.length > 0) {
      await handleResumeFileUpload(e.target.files[0]);
    }
  });

  // 3. Save Resume Button
  dom.btnSaveResume.addEventListener("click", async () => {
    const text = dom.matcherResumeText.value.trim();
    const title = dom.resumeTitleInput.value.trim() || "Master Resume";

    if (!text) {
      showToast("Resume text is empty", "error");
      return;
    }

    try {
      const resp = await fetch("/matcher/save-resume", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_external_id: state.userId,
          title: title,
          resume_text: text,
          file_name: "manual_entry.txt"
        })
      });

      if (!resp.ok) throw new Error("Failed to save resume");
      showToast(`Saved resume profile "${title}"!`, "success");
      loadResumes();
    } catch (err) {
      showToast(err.message, "error");
    }
  });

  // 4. Run Match & Score Analysis
  dom.btnRunMatch.addEventListener("click", async () => {
    const jdText = dom.matcherJdText.value.trim();
    const resumeText = dom.matcherResumeText.value.trim();

    if (!jdText) {
      showToast("Please provide a job posting URL or description", "error");
      dom.matcherJdText.focus();
      return;
    }

    if (!resumeText) {
      showToast("Please upload your resume or paste resume text", "error");
      dom.matcherResumeText.focus();
      return;
    }

    // Show loading state
    dom.matcherEmptyState.classList.add("hidden");
    dom.matcherResultsView.classList.add("hidden");
    dom.matcherLoadingState.classList.remove("hidden");
    dom.btnRunMatch.disabled = true;

    try {
      const resp = await fetch("/matcher/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_external_id: state.userId,
          resume_text: resumeText,
          job_description: jdText,
          job_url: dom.matcherJobUrl.value.trim() || null,
          company: dom.matcherCompany.value.trim() || null,
          role_title: dom.matcherRole.value.trim() || null
        })
      });

      if (!resp.ok) {
        const errorData = await resp.json().catch(() => ({}));
        throw new Error(errorData.detail || "Analysis failed");
      }

      const result = await resp.json();
      state.lastMatchResult = result;
      renderMatchResults(result);
      showToast(`Match analysis complete: ${result.match_score}% fit!`, "success");

      // Also trigger Suggested Edits generation in the edits panel
      fetchSuggestedEdits(false);

    } catch (err) {
      showToast(`Matching notice: ${err.message}`, "error");
      dom.matcherLoadingState.classList.add("hidden");
      dom.matcherEmptyState.classList.remove("hidden");
    } finally {
      dom.btnRunMatch.disabled = false;
    }
  });

  // 5. Copy Pitch Button
  dom.btnCopyPitch.addEventListener("click", () => {
    if (state.lastMatchResult && state.lastMatchResult.tailored_pitch) {
      navigator.clipboard.writeText(state.lastMatchResult.tailored_pitch);
      showToast("Outreach pitch copied to clipboard!", "success");
    }
  });

  // 6. Add Matched Job to Tracker
  dom.btnAddMatchedToTracker.addEventListener("click", async () => {
    if (!state.lastMatchResult) return;

    const res = state.lastMatchResult;
    const company = res.company || dom.matcherCompany.value.trim() || "Target Company";
    const role = res.role_title || dom.matcherRole.value.trim() || "Target Role";
    const notes = `Key Strengths:\n- ${(res.key_strengths || []).join('\n- ')}`;

    try {
      const resp = await fetch("/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_external_id: state.userId,
          company: company,
          role_title: role,
          job_url: dom.matcherJobUrl.value.trim() || null,
          match_score: res.match_score,
          tailored_pitch: res.tailored_pitch,
          follow_up_days: 7,
          notes: notes
        })
      });

      if (!resp.ok) throw new Error("Failed to add to Job Tracker");
      showToast(`Added ${company} — ${role} to Job Tracker!`, "success");
      loadJobs();
      switchTab("tab-jobs");
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

// ============================================================================
// Suggested Resume Edits Handlers
// ============================================================================
function setupSuggestedEditsHandlers() {
  if (dom.btnGenerateEdits) {
    dom.btnGenerateEdits.addEventListener("click", () => {
      fetchSuggestedEdits(true);
    });
  }
}

async function fetchSuggestedEdits(showToastNotification = true) {
  const resumeText = dom.matcherResumeText.value.trim();
  const jdText = dom.matcherJdText.value.trim();

  if (!jdText) {
    if (showToastNotification) showToast("Please fetch or paste a target job description", "error");
    dom.matcherJdText.focus();
    return;
  }

  if (!resumeText) {
    if (showToastNotification) showToast("Please provide or upload your resume text", "error");
    dom.matcherResumeText.focus();
    return;
  }

  if (dom.editsEmptyState) dom.editsEmptyState.classList.add("hidden");
  if (dom.editsListContainer) dom.editsListContainer.classList.add("hidden");
  if (dom.editsLoadingState) dom.editsLoadingState.classList.remove("hidden");
  if (dom.btnGenerateEdits) dom.btnGenerateEdits.disabled = true;
  if (dom.btnGenerateEditsText) dom.btnGenerateEditsText.textContent = "SYNTHESIZING...";

  try {
    const resp = await fetch("/matcher/suggest-edits", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_external_id: state.userId,
        resume_text: resumeText,
        job_description: jdText,
        company: dom.matcherCompany.value.trim() || null,
        role_title: dom.matcherRole.value.trim() || null
      })
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to generate edit suggestions");
    }

    const data = await resp.json();
    state.suggestedEdits = data.suggestions || [];
    renderSuggestedEdits(state.suggestedEdits);

    if (showToastNotification) {
      if (state.suggestedEdits.length > 0) {
        showToast(`Generated ${state.suggestedEdits.length} tailored edit suggestions!`, "success");
      } else {
        showToast("Resume is already well aligned with the job description!", "info");
      }
    }
  } catch (err) {
    showToast(err.message, "error");
    if (dom.editsLoadingState) dom.editsLoadingState.classList.add("hidden");
    if (dom.editsEmptyState) dom.editsEmptyState.classList.remove("hidden");
  } finally {
    if (dom.btnGenerateEdits) dom.btnGenerateEdits.disabled = false;
    if (dom.btnGenerateEditsText) dom.btnGenerateEditsText.textContent = "GENERATE EDITS";
  }
}

function renderSuggestedEdits(suggestions) {
  if (!dom.editsListContainer) return;

  if (dom.editsLoadingState) dom.editsLoadingState.classList.add("hidden");

  if (!suggestions || suggestions.length === 0) {
    if (dom.editsEmptyState) {
      dom.editsEmptyState.innerHTML = `
        <span class="material-symbols-outlined text-secondary text-[24px]">task_alt</span>
        <p class="font-label-mono text-[11.5px] text-on-surface">No pending edits! All relevant skills and experience bullets are well framed.</p>
      `;
      dom.editsEmptyState.classList.remove("hidden");
    }
    dom.editsListContainer.classList.add("hidden");
    return;
  }

  if (dom.editsEmptyState) dom.editsEmptyState.classList.add("hidden");
  dom.editsListContainer.classList.remove("hidden");

  dom.editsListContainer.innerHTML = suggestions.map((s, idx) => {
    const isRewrite = s.type === "bullet_rewrite";
    const typeLabel = isRewrite ? "BULLET REWRITE" : "KEYWORD GAP";
    const badgeClass = isRewrite ? "edit-type-rewrite" : "edit-type-keyword";

    return `
      <div class="edit-suggestion-card ${s.flagged_for_review ? 'flagged' : ''}" id="edit-card-${idx}">
        <div class="edit-card-header">
          <div class="flex items-center gap-2">
            <span class="edit-type-badge ${badgeClass}">${typeLabel}</span>
            <span class="font-label-mono text-[11px] text-on-surface font-bold">// ${escapeHtml(s.section)}</span>
          </div>
          ${s.flagged_for_review ? `
            <span class="font-label-mono text-[10px] text-warning flex items-center gap-1 font-bold">
              <span class="material-symbols-outlined text-[14px]">warning</span>
              <span>VERIFY DETAILS</span>
            </span>
          ` : ''}
        </div>

        <div class="diff-box">
          ${s.original ? `
            <div class="diff-original">
              ${escapeHtml(s.original)}
            </div>
          ` : ''}
          <div class="diff-suggested ${!isRewrite ? 'keyword-suggestion' : ''}">
            ${escapeHtml(s.suggested)}
          </div>
        </div>

        <div class="diff-reason">
          💡 ${escapeHtml(s.reason)}
        </div>

        ${s.flagged_for_review && s.warning_message ? `
          <div class="edit-guardrail-warning">
            <span class="material-symbols-outlined text-[15px]">info</span>
            <span>⚠️ ${escapeHtml(s.warning_message)}</span>
          </div>
        ` : ''}

        <div class="edit-actions-row">
          <button type="button" class="btn-dismiss-edit" onclick="dismissSuggestion(${idx})">Dismiss</button>
          <button type="button" class="btn-accept-edit" onclick="acceptSuggestion(${idx})">
            <span class="material-symbols-outlined text-[14px]">check</span>
            <span>Accept Edit</span>
          </button>
        </div>
      </div>
    `;
  }).join("");
}

window.acceptSuggestion = function(index) {
  const s = state.suggestedEdits[index];
  if (!s) return;

  const currentResume = dom.matcherResumeText.value;

  if (s.type === "bullet_rewrite" && s.original) {
    if (currentResume.includes(s.original)) {
      dom.matcherResumeText.value = currentResume.replace(s.original, s.suggested);
      showToast("Applied rewrite to resume editor!", "success");
    } else {
      dom.matcherResumeText.value += `\n- ${s.suggested}`;
      showToast("Appended optimized bullet to resume editor!", "info");
    }
  } else if (s.type === "missing_keyword") {
    const skillMatch = s.suggested.match(/Add '([^']+)'/i);
    const skillToAdd = skillMatch ? skillMatch[1] : s.suggested;

    const skillsHeaderRegex = /(SKILLS[\s\S]*?:)/i;
    if (skillsHeaderRegex.test(currentResume)) {
      dom.matcherResumeText.value = currentResume.replace(skillsHeaderRegex, `$1\n- ${skillToAdd}`);
      showToast(`Added '${skillToAdd}' to Skills section!`, "success");
    } else {
      dom.matcherResumeText.value = `SKILLS:\n- ${skillToAdd}\n\n` + currentResume;
      showToast(`Added '${skillToAdd}' to resume!`, "success");
    }
  } else {
    dom.matcherResumeText.value += `\n- ${s.suggested}`;
    showToast("Applied edit suggestion to resume!", "success");
  }

  // Remove accepted suggestion from list
  state.suggestedEdits.splice(index, 1);
  renderSuggestedEdits(state.suggestedEdits);
};

window.dismissSuggestion = function(index) {
  state.suggestedEdits.splice(index, 1);
  renderSuggestedEdits(state.suggestedEdits);
  showToast("Dismissed suggestion", "info");
};

// ============================================================================
// ATS Checker Handlers
// ============================================================================
function setupAtsCheckerHandlers() {
  if (!dom.btnRunAtsCheck) return;

  // Picker selection sync
  if (dom.atsResumeSelectPicker) {
    dom.atsResumeSelectPicker.addEventListener("change", () => {
      const selectedId = dom.atsResumeSelectPicker.value;
      if (selectedId === "new") {
        dom.atsResumeText.value = "";
      } else {
        const resume = state.resumes.find(r => r.id === selectedId);
        if (resume) {
          dom.atsResumeText.value = resume.resume_text;
        }
      }
    });
  }

  // Dropzone drag-and-drop
  if (dom.atsResumeDropzone) {
    dom.atsResumeDropzone.addEventListener("click", () => dom.atsResumeFileInput.click());

    dom.atsResumeDropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dom.atsResumeDropzone.style.borderColor = "var(--accent-primary)";
    });

    dom.atsResumeDropzone.addEventListener("dragleave", () => {
      dom.atsResumeDropzone.style.borderColor = "var(--border-color)";
    });

    dom.atsResumeDropzone.addEventListener("drop", async (e) => {
      e.preventDefault();
      dom.atsResumeDropzone.style.borderColor = "var(--border-color)";
      if (e.dataTransfer.files.length > 0) {
        await handleAtsFileUpload(e.dataTransfer.files[0]);
      }
    });
  }

  if (dom.atsResumeFileInput) {
    dom.atsResumeFileInput.addEventListener("change", async (e) => {
      if (e.target.files.length > 0) {
        await handleAtsFileUpload(e.target.files[0]);
      }
    });
  }

  // Run ATS Check Button
  dom.btnRunAtsCheck.addEventListener("click", async () => {
    const text = dom.atsResumeText.value.trim();
    if (!text) {
      showToast("Please select a resume profile or upload a resume file", "error");
      dom.atsResumeText.focus();
      return;
    }

    // Show loading state
    dom.atsEmptyState.classList.add("hidden");
    dom.atsResultsView.classList.add("hidden");
    dom.atsLoadingState.classList.remove("hidden");
    dom.btnRunAtsCheck.disabled = true;

    try {
      const resp = await fetch("/ats/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_external_id: state.userId,
          resume_text: text,
          file_name: "resume.pdf"
        })
      });

      if (!resp.ok) {
        const errorData = await resp.json().catch(() => ({}));
        throw new Error(errorData.detail || "ATS check failed");
      }

      const result = await resp.json();
      state.lastAtsResult = result;
      renderAtsResults(result);
      showToast(`ATS audit complete: ${result.overall_score}% (${result.label})`, "success");

    } catch (err) {
      showToast(`ATS audit notice: ${err.message}`, "error");
      dom.atsLoadingState.classList.add("hidden");
      dom.atsEmptyState.classList.remove("hidden");
    } finally {
      dom.btnRunAtsCheck.disabled = false;
    }
  });
}

async function handleAtsFileUpload(file) {
  showToast(`Parsing resume (${file.name})...`, "info");
  const formData = new FormData();
  formData.append("user_external_id", state.userId);
  formData.append("title", file.name.replace(/\.[^/.]+$/, ""));
  formData.append("file", file);

  try {
    const resp = await fetch("/matcher/upload-resume", {
      method: "POST",
      body: formData
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to parse resume");
    }

    const data = await resp.json();
    dom.atsResumeText.value = data.resume_text;
    showToast(`Extracted ${data.char_count} characters from resume!`, "success");
    loadResumes();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    dom.atsResumeFileInput.value = "";
  }
}

function renderAtsResults(res) {
  dom.atsLoadingState.classList.add("hidden");
  dom.atsEmptyState.classList.add("hidden");
  dom.atsResultsView.classList.remove("hidden");

  // Overall Score & Gauge
  dom.atsScoreVal.innerHTML = `${res.overall_score}<span class="text-[32px] text-primary/70">%</span>`;
  if (dom.atsGaugeCircle) {
    dom.atsGaugeCircle.className = "gauge-circle";
    if (res.overall_score >= 80) dom.atsGaugeCircle.classList.add("score-strong");
    else if (res.overall_score >= 65) dom.atsGaugeCircle.classList.add("score-good");
    else if (res.overall_score >= 50) dom.atsGaugeCircle.classList.add("score-moderate");
    else dom.atsGaugeCircle.classList.add("score-low");
  }

  // Verdict Pill
  dom.atsVerdictPill.textContent = res.label.toUpperCase();
  dom.atsVerdictPill.className = "px-4 py-1.5 border border-secondary text-secondary font-label-mono text-[11px] uppercase tracking-widest glow-secondary bg-secondary/10";
  if (res.overall_score < 50) {
    dom.atsVerdictPill.className = "px-4 py-1.5 border border-error text-error font-label-mono text-[11px] uppercase tracking-widest glow-error bg-error/10";
  }

  // Sub-scores
  dom.atsL1Val.textContent = `${res.layer1_score}%`;
  dom.atsL2Val.textContent = res.layer2_score != null ? `${res.layer2_score}%` : "Rule-Based Active";

  // Layer 1: Rule-Based Checks List
  dom.atsRuleChecksList.innerHTML = (res.rule_based_checks || []).map(c => {
    const badgeCls = c.status === "pass" ? "status-pass" : c.status === "warn" ? "status-warn" : "status-fail";
    const badgeText = c.status === "pass" ? "✓ PASS" : c.status === "warn" ? "⚠️ WARN" : "✗ FAIL";
    const title = formatCheckTitle(c.name);

    return `
      <div class="ats-check-row">
        <div class="ats-check-main">
          <span class="ats-check-title">${escapeHtml(title)}</span>
          <span class="ats-check-detail">${escapeHtml(c.detail)}</span>
        </div>
        <span class="ats-status-badge ${badgeCls}">${badgeText}</span>
      </div>
    `;
  }).join("");

  // Layer 2: ML Signals List
  dom.atsMlChecksList.innerHTML = (res.ml_checks || []).map(c => {
    const badgeCls = c.status === "pass" ? "status-pass" : c.status === "warn" ? "status-warn" : c.status === "fail" ? "status-fail" : "status-unavailable";
    const badgeText = c.status === "pass" ? "✓ PASS" : c.status === "warn" ? "⚠️ WARN" : c.status === "fail" ? "✗ FAIL" : "⚙️ UNAVAILABLE";
    const title = formatCheckTitle(c.name);

    return `
      <div class="ats-check-row">
        <div class="ats-check-main">
          <span class="ats-check-title">${escapeHtml(title)} ${c.model ? `<small class="text-muted" style="font-size:11px;font-weight:normal;">(${escapeHtml(c.model)})</small>` : ''}</span>
          <span class="ats-check-detail">${escapeHtml(c.detail)}</span>
        </div>
        <span class="ats-status-badge ${badgeCls}">${badgeText}</span>
      </div>
    `;
  }).join("");

  // Recommendations Checklist
  dom.atsRecommendationsList.innerHTML = (res.recommendations || []).map(r => `
    <li>${escapeHtml(r)}</li>
  `).join("");
}

function formatCheckTitle(name) {
  const map = {
    "file_format": "File Format Compatibility",
    "filename_conventions": "Filename Hygiene & Conventions",
    "standard_sections": "Standard ATS Section Headers",
    "contact_info": "Contact Information Detectability",
    "multi_column_tables": "Single-Column Layout & Tables",
    "resume_length": "Resume Length & Word Count",
    "bullet_point_density": "Bullet Point Formatting & Scannability",
    "skills_extractable": "BERT Technical Skills Extraction",
    "designation_extractable": "BERT Job Designation Extraction",
    "role_coherence": "Role Classification & Domain Coherence",
    "contact_email_domain": "Contact Email & Domain Verification",
    "messaging_channel_screening": "Recruitment & Messaging Channels",
    "upfront_fees_and_equipment": "Upfront Fees & Equipment Demands",
    "unrealistic_pay_and_urgency": "Compensation & Pressure Phrasing",
    "url_security_and_domain": "URL Protocol & Shortener Hygiene",
    "posting_structural_quality": "Structural Hygiene & Formatting"
  };
  return map[name] || name.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
}

// ============================================================================
// Job Authenticity Checker
// ============================================================================
const AUTH_PRESET_SAFE = {
  company: "Stripe",
  role_title: "Senior Backend Engineer - Platform",
  url: "https://stripe.com/jobs/senior-backend-engineer",
  text: `Senior Backend Engineer - Core Payments Platform\nStripe (careers@stripe.com)\nLocation: San Francisco, CA (Hybrid)\n\nAbout the Role:\nWe are seeking an experienced Backend Engineer to scale our distributed core transaction systems. You will build highly available APIs, design resilient PostgreSQL architectures, and collaborate across global engineering teams.\n\nQualifications:\n- 5+ years of experience with Python, Go, or Ruby in production systems.\n- Deep understanding of distributed transactions, event-driven architectures, and database scalability.\n- Strong communication skills and a passion for engineering craft.\n\nCompensation & Benefits:\nBase Salary: $175,000 - $215,000 + Equity + Full Health/Dental/Vision + 401(k) Matching.`
};

const AUTH_PRESET_SCAM = {
  company: "Apex Global Remote",
  role_title: "Work From Home Data Entry Specialist",
  url: "http://bit.ly/urgent-remote-entry-392",
  text: `URGENT WORK FROM HOME DATA ENTRY ASSISTANT - EARN $4500 A WEEK NO EXPERIENCE NEEDED!!!!\n\nWe are urgently hiring 20 remote data assistants immediately today. No interview or background required.\n\nTo apply, you MUST message our HR Manager on Telegram: @hiring_officer_apex or email apex-hiring-desk@gmail.com.\n\nWe will mail you a $3200 equipment check upfront to purchase certified home office hardware from our approved vendor. You must send your bank account routing details for initial direct deposit setup.\n\nA $45 administrative onboarding processing fee is required upfront before starting.`
};

function setupAuthenticityHandlers() {
  if (!dom.btnRunAuthenticity) return;

  // Preset buttons
  if (dom.btnAuthPresetSafe) {
    dom.btnAuthPresetSafe.addEventListener("click", () => {
      dom.authCompanyInput.value = AUTH_PRESET_SAFE.company;
      dom.authRoleInput.value = AUTH_PRESET_SAFE.role_title;
      dom.authJobUrl.value = AUTH_PRESET_SAFE.url;
      dom.authJobText.value = AUTH_PRESET_SAFE.text;
      showToast("Loaded Legitimate Tech Role preset", "info");
    });
  }

  if (dom.btnAuthPresetScam) {
    dom.btnAuthPresetScam.addEventListener("click", () => {
      dom.authCompanyInput.value = AUTH_PRESET_SCAM.company;
      dom.authRoleInput.value = AUTH_PRESET_SCAM.role_title;
      dom.authJobUrl.value = AUTH_PRESET_SCAM.url;
      dom.authJobText.value = AUTH_PRESET_SCAM.text;
      showToast("Loaded Known Scam Pattern preset", "info");
    });
  }

  // Cross-tab button from Resume Matcher
  if (dom.btnMatcherCheckAuth) {
    dom.btnMatcherCheckAuth.addEventListener("click", () => {
      const url = dom.matcherJobUrl.value.trim();
      const text = dom.matcherJobText.value.trim();
      const comp = dom.matcherCompany.value.trim();
      const role = dom.matcherRole.value.trim();

      if (!url && !text) {
        showToast("Please enter a Job URL or paste description text first", "warning");
        return;
      }

      dom.authJobUrl.value = url;
      dom.authJobText.value = text;
      if (comp) dom.authCompanyInput.value = comp;
      if (role) dom.authRoleInput.value = role;

      switchTab("tab-authenticity");
      runAuthenticityAudit();
    });
  }

  // URL Fetching
  if (dom.btnAuthFetchJob) {
    dom.btnAuthFetchJob.addEventListener("click", async () => {
      const url = (dom.authJobUrl.value || "").trim();
      if (!url) {
        showToast("Please enter a valid Job URL", "warning");
        return;
      }

      dom.authFetchBtnText.textContent = "⌛ FETCHING...";
      dom.btnAuthFetchJob.disabled = true;
      if (dom.authBotWarning) dom.authBotWarning.classList.add("hidden");

      try {
        const resp = await fetch("/matcher/fetch-job", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: url })
        });

        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}));
          throw new Error(err.detail || "Failed to fetch job posting");
        }

        const data = await resp.json();
        if (data.company && !dom.authCompanyInput.value) dom.authCompanyInput.value = data.company;
        if (data.role_title && !dom.authRoleInput.value) dom.authRoleInput.value = data.role_title;
        if (data.description) dom.authJobText.value = data.description;

        if (!data.success && dom.authBotWarning) {
          dom.authBotWarning.classList.remove("hidden");
          dom.authBotWarning.textContent = `⚠️ ${data.message}`;
          showToast("Protected site. Please verify or paste description manually.", "warning");
        } else {
          showToast(`Extracted ${data.description ? data.description.length : 0} characters!`, "success");
        }
      } catch (err) {
        showToast(err.message, "error");
        if (dom.authBotWarning) {
          dom.authBotWarning.classList.remove("hidden");
          dom.authBotWarning.textContent = `⚠️ ${err.message}`;
        }
      } finally {
        dom.authFetchBtnText.textContent = "⚡ FETCH";
        dom.btnAuthFetchJob.disabled = false;
      }
    });
  }

  // Run Audit
  dom.btnRunAuthenticity.addEventListener("click", runAuthenticityAudit);
}

async function runAuthenticityAudit() {
  const url = (dom.authJobUrl.value || "").trim();
  const jobText = (dom.authJobText.value || "").trim();
  const company = (dom.authCompanyInput.value || "").trim();
  const roleTitle = (dom.authRoleInput.value || "").trim();

  if (!url && !jobText) {
    showToast("Please enter a Job URL or paste the job description text", "warning");
    return;
  }

  dom.authEmptyState.classList.add("hidden");
  dom.authResultsView.classList.add("hidden");
  dom.authLoadingState.classList.remove("hidden");
  dom.btnRunAuthenticity.disabled = true;
  dom.authBtnLabel.textContent = "AUDITING_LEGITIMACY...";

  try {
    const payload = {
      url: url || null,
      job_text: jobText || null,
      company: company || null,
      role_title: roleTitle || null
    };

    const resp = await fetch("/authenticity/check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || "Authenticity audit failed");
    }

    const data = await resp.json();
    renderAuthenticityReport(data);
    showToast(`Authenticity assessment complete: ${data.verdict_label}`, data.risk_level === "high" ? "error" : data.risk_level === "medium" ? "warning" : "success");
  } catch (err) {
    showToast(err.message, "error");
    dom.authLoadingState.classList.add("hidden");
    dom.authEmptyState.classList.remove("hidden");
  } finally {
    dom.btnRunAuthenticity.disabled = false;
    dom.authBtnLabel.textContent = "RUN AUTHENTICITY AUDIT";
  }
}

function renderAuthenticityReport(res) {
  dom.authLoadingState.classList.add("hidden");
  dom.authEmptyState.classList.add("hidden");
  dom.authResultsView.classList.remove("hidden");

  // Hero Card Styling
  dom.authRiskHero.className = "bg-surface-container border p-6 tech-card flex flex-col items-center justify-center text-center gap-3";
  if (res.risk_level === "high") {
    dom.authRiskHero.classList.add("risk-high-hero", "glow-error");
  } else if (res.risk_level === "medium") {
    dom.authRiskHero.classList.add("risk-medium-hero");
  } else {
    dom.authRiskHero.classList.add("risk-low-hero", "glow-secondary");
  }

  dom.authRiskPill.textContent = res.verdict_label.toUpperCase();
  dom.authRiskScore.innerHTML = `${res.risk_score}<span class="text-[20px] text-on-surface-variant font-label-mono ml-1">/ 100 RISK INDEX</span>`;
  dom.authRiskSummary.textContent = res.summary;

  // Layer 1: Rule Heuristics
  const l1Checks = res.layer1_heuristics || [];
  dom.authL1Counts.textContent = `${l1Checks.length} checks evaluated (${res.red_flags_count} flags, ${res.warnings_count} warnings)`;
  dom.authLayer1List.innerHTML = l1Checks.map(c => {
    const badgeCls = c.status === "pass" ? "status-pass" : c.status === "warn" ? "status-warn" : c.status === "fail" ? "status-fail" : "status-unavailable";
    const badgeText = c.status === "pass" ? "✓ PASS" : c.status === "warn" ? "⚠️ WARN" : c.status === "fail" ? "✗ FAIL" : "⚙️ UNAVAILABLE";
    const title = formatCheckTitle(c.name);

    return `
      <div class="auth-check-row">
        <div class="auth-check-main">
          <span class="auth-check-title">${escapeHtml(title)}</span>
          <span class="auth-check-detail">${escapeHtml(c.detail)}</span>
          ${c.evidence ? `<span class="auth-evidence-quote">Matched Evidence: "${escapeHtml(c.evidence)}"</span>` : ''}
        </div>
        <span class="ats-status-badge ${badgeCls}">${badgeText}</span>
      </div>
    `;
  }).join("");

  // Layer 2: BERT ML Classifier
  const l2 = res.layer2_classifier || {};
  if (l2.status === "completed") {
    const isFake = l2.predicted_label === "Fake Job";
    const badgeCls = isFake ? "status-fail" : "status-pass";
    const confPct = Math.round((l2.confidence || 0) * 100);

    dom.authLayer2Content.innerHTML = `
      <div class="auth-check-row">
        <div class="auth-check-main">
          <span class="auth-check-title">Model: ${escapeHtml(l2.model_name)}</span>
          <span class="auth-check-detail">${escapeHtml(l2.detail)}</span>
          <div class="w-full h-1.5 bg-surface-container-highest mt-2 rounded-full overflow-hidden">
            <div class="h-full ${isFake ? 'bg-error' : 'bg-secondary'}" style="width: ${confPct}%"></div>
          </div>
        </div>
        <div class="flex flex-col items-end gap-1">
          <span class="ats-status-badge ${badgeCls}">${escapeHtml(l2.predicted_label)}</span>
          <span class="font-label-mono text-[10px] text-on-surface-variant">${confPct}% conf</span>
        </div>
      </div>
      <div class="auth-limitations-box">
        <strong>Documented Model Caveats:</strong> ${escapeHtml(l2.limitations_note || '')}
      </div>
    `;
  } else {
    dom.authLayer2Content.innerHTML = `
      <div class="auth-check-row">
        <div class="auth-check-main">
          <span class="auth-check-title">ML Classifier Signal</span>
          <span class="auth-check-detail">${escapeHtml(l2.detail || 'Model evaluation unavailable. Fallback to Layer 1 & 3.')}</span>
        </div>
        <span class="ats-status-badge status-unavailable">⚙️ UNAVAILABLE</span>
      </div>
    `;
  }

  // Layer 3: RAG Reasoning
  const l3 = res.layer3_llm_reasoning || {};
  if (l3.status === "completed") {
    const patterns = l3.matched_patterns || [];
    const patternCards = patterns.length > 0
      ? patterns.map(p => `
          <div class="auth-pattern-card">
            <div class="flex justify-between items-center">
              <span class="font-label-mono text-[11px] text-primary font-bold">⚠️ ${escapeHtml(p.pattern)}</span>
            </div>
            <div class="font-label-mono text-[11px] text-error bg-error/10 p-2 border border-error/20">
              Evidence Quote: "${escapeHtml(p.evidence)}"
            </div>
            <p class="font-label-mono text-[11px] text-on-surface-variant">${escapeHtml(p.explanation)}</p>
          </div>
        `).join("")
      : `<div class="p-3 bg-secondary/5 border border-secondary/20 text-secondary font-label-mono text-[11px]">
          ✓ No known fraud patterns matched in knowledge base retrieval. Posting text appears consistent with standard hiring.
        </div>`;

    dom.authLayer3Content.innerHTML = `
      <div class="space-y-2.5">
        <div class="font-label-mono text-[11px] text-on-surface-variant flex justify-between">
          <span>Retrieved Fraud Knowledge Patterns: <strong>${l3.retrieved_patterns_count} categories evaluated</strong></span>
          <span class="text-primary font-bold">LLM Risk: ${(l3.risk_level || 'low').toUpperCase()}</span>
        </div>
        <p class="font-label-mono text-[12px] text-on-surface bg-surface-container-low p-3 border border-outline-variant/40">
          ${escapeHtml(l3.reasoning_summary)}
        </p>
        <div class="space-y-2 mt-2">
          ${patternCards}
        </div>
      </div>
    `;
  } else {
    dom.authLayer3Content.innerHTML = `
      <div class="auth-check-row">
        <div class="auth-check-main">
          <span class="auth-check-title">RAG LLM Reasoning Layer</span>
          <span class="auth-check-detail">${escapeHtml(l3.reasoning_summary || 'LLM reasoning layer unavailable. Decision based on Layer 1 & 2 signals.')}</span>
        </div>
        <span class="ats-status-badge status-unavailable">⚙️ UNAVAILABLE</span>
      </div>
    `;
  }
}

// ============================================================================
// Company Insights Handlers & Rendering
// ============================================================================
const INSIGHT_PRESET_STRIPE = {
  company: "Stripe",
  url: "https://stripe.com",
  role: "Staff Backend Engineer",
  about: "Stripe is a financial infrastructure platform for businesses. Millions of companies—from the world’s largest enterprises to the most ambitious startups—use Stripe to accept payments, grow their revenue, and accelerate new business opportunities. Founded in 2010 with over 7,000 employees globally."
};

const INSIGHT_PRESET_STARTUP = {
  company: "Venture Stealth Robotics",
  url: "https://stealthrobotics.ai",
  role: "Senior Motion Planning Engineer",
  about: "Venture Stealth Robotics is an early stage seed funded robotics startup developing autonomous manipulation software. Founded in 2023 by ex-DeepMind researchers, we are a fast-moving team of 14 engineers based in San Francisco building next-generation warehouse logistics robots."
};

const INSIGHT_PRESET_CONFLICT = {
  company: "MegaGlobal Enterprises",
  url: "https://megaglobal.com",
  role: "Lead Platform Architect",
  about: "MegaGlobal is an early stage stealth startup. Founded in 1994, MegaGlobal employs over 50,000 engineers and operations staff across 40 countries, processing billions in enterprise commerce annually."
};

function setupCompanyInsightsHandlers() {
  if (!dom.btnRunInsights) return;

  // Preset buttons
  if (dom.btnInsightPresetStripe) {
    dom.btnInsightPresetStripe.addEventListener("click", () => {
      dom.insightCompanyInput.value = INSIGHT_PRESET_STRIPE.company;
      dom.insightUrlInput.value = INSIGHT_PRESET_STRIPE.url;
      dom.insightRoleInput.value = INSIGHT_PRESET_STRIPE.role;
      dom.insightAboutInput.value = INSIGHT_PRESET_STRIPE.about;
      fetchCompanyInsights();
    });
  }

  if (dom.btnInsightPresetStartup) {
    dom.btnInsightPresetStartup.addEventListener("click", () => {
      dom.insightCompanyInput.value = INSIGHT_PRESET_STARTUP.company;
      dom.insightUrlInput.value = INSIGHT_PRESET_STARTUP.url;
      dom.insightRoleInput.value = INSIGHT_PRESET_STARTUP.role;
      dom.insightAboutInput.value = INSIGHT_PRESET_STARTUP.about;
      fetchCompanyInsights();
    });
  }

  if (dom.btnInsightPresetConflict) {
    dom.btnInsightPresetConflict.addEventListener("click", () => {
      dom.insightCompanyInput.value = INSIGHT_PRESET_CONFLICT.company;
      dom.insightUrlInput.value = INSIGHT_PRESET_CONFLICT.url;
      dom.insightRoleInput.value = INSIGHT_PRESET_CONFLICT.role;
      dom.insightAboutInput.value = INSIGHT_PRESET_CONFLICT.about;
      fetchCompanyInsights();
    });
  }

  // If user edits company name manually, clear stale preset URLs that do not match
  if (dom.insightCompanyInput) {
    dom.insightCompanyInput.addEventListener("input", () => {
      const comp = dom.insightCompanyInput.value.toLowerCase().trim();
      const currUrl = (dom.insightUrlInput.value || "").toLowerCase().trim();
      if (currUrl && !currUrl.includes(comp) && (currUrl.includes("stripe.com") || currUrl.includes("stealthrobotics.ai") || currUrl.includes("megaglobal.com"))) {
        dom.insightUrlInput.value = "";
      }
    });
  }

  // Inspect insights from matcher result card
  if (dom.btnMatcherInspectInsights) {
    dom.btnMatcherInspectInsights.addEventListener("click", () => {
      const comp = dom.matcherCompany.value.trim() || (state.lastMatchResult && state.lastMatchResult.company) || "Target Company";
      const role = dom.matcherRole.value.trim() || (state.lastMatchResult && state.lastMatchResult.role_title) || "";
      const jd = dom.matcherJdText.value.trim() || "";
      const url = dom.matcherJobUrl.value.trim() || "";

      dom.insightCompanyInput.value = comp;
      dom.insightRoleInput.value = role;
      dom.insightAboutInput.value = jd;
      dom.insightUrlInput.value = url;

      switchTab("tab-insights");
      fetchCompanyInsights();
    });
  }

  // Run Insights Button
  dom.btnRunInsights.addEventListener("click", () => {
    fetchCompanyInsights();
  });
}

async function fetchCompanyInsights() {
  const company = (dom.insightCompanyInput.value || "").trim();
  const url = (dom.insightUrlInput.value || "").trim();
  const role = (dom.insightRoleInput.value || "").trim();
  const about = (dom.insightAboutInput.value || "").trim();

  if (!company) {
    showToast("Please enter a company name to analyze", "warning");
    dom.insightCompanyInput.focus();
    return;
  }

  dom.insightEmptyState.classList.add("hidden");
  dom.insightResultsView.classList.add("hidden");
  dom.insightLoadingState.classList.remove("hidden");
  dom.btnRunInsights.disabled = true;
  dom.insightBtnLabel.textContent = "SYNTHESIZING_INTELLIGENCE...";

  try {
    const payload = {
      company: company,
      company_url: url || null,
      role_title: role || null,
      about_text: about || null,
      user_external_id: state.userId
    };

    const resp = await fetch("/insights/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to generate company insights");
    }

    const data = await resp.json();
    state.lastInsightsResult = data;
    renderCompanyInsights(data);
    showToast(`Company profile generated for ${data.company}!`, "success");
  } catch (err) {
    showToast(err.message, "error");
    dom.insightLoadingState.classList.add("hidden");
    dom.insightEmptyState.classList.remove("hidden");
  } finally {
    dom.btnRunInsights.disabled = false;
    dom.insightBtnLabel.textContent = "GENERATE COMPANY INTELLIGENCE";
  }
}

function renderCompanyInsights(data) {
  dom.insightLoadingState.classList.add("hidden");
  dom.insightEmptyState.classList.add("hidden");
  dom.insightResultsView.classList.remove("hidden");

  // URL Mismatch Alert Banner
  const mismatchWarn = data.url_mismatch_warning || (data.classification && data.classification.url_mismatch_warning);
  if (mismatchWarn && dom.insightUrlMismatchAlert) {
    dom.insightUrlMismatchText.textContent = mismatchWarn;
    dom.insightUrlMismatchAlert.classList.remove("hidden");
  } else if (dom.insightUrlMismatchAlert) {
    dom.insightUrlMismatchAlert.classList.add("hidden");
  }

  // Classification Card
  dom.insightCompanyTitle.textContent = data.company;
  const cls = data.classification || {};
  dom.insightSizeLabel.textContent = cls.label || "Company";
  const confPct = Math.round((cls.confidence || 0) * 100);
  dom.insightSizeConfidence.textContent = `Confidence: ${confPct}%`;

  if (cls.industry) {
    const indConfPct = cls.industry_confidence ? ` (${Math.round(cls.industry_confidence * 100)}%)` : '';
    dom.insightIndustryBadge.textContent = `${cls.industry}${indConfPct}`;
    dom.insightIndustryBadge.classList.remove("hidden");
  } else {
    dom.insightIndustryBadge.classList.add("hidden");
  }

  // Low Confidence Data Quality Alert
  if (cls.low_confidence_data && dom.insightLowDataAlert) {
    dom.insightLowDataText.textContent = cls.data_quality_note || "Limited grounding data available — workforce headcount and founding year could not be verified.";
    dom.insightLowDataAlert.classList.remove("hidden");
  } else if (dom.insightLowDataAlert) {
    dom.insightLowDataAlert.classList.add("hidden");
  }

  // Disagreement Alert
  if (cls.disagreement_flag && dom.insightDisagreementAlert) {
    dom.insightDisagreementAlert.classList.remove("hidden");
  } else if (dom.insightDisagreementAlert) {
    dom.insightDisagreementAlert.classList.add("hidden");
  }

  // Zero-Shot Score Breakdown
  const scores = cls.all_scores || {};
  const scoreEntries = Object.entries(scores);
  if (scoreEntries.length > 0) {
    dom.insightAllScoresList.innerHTML = scoreEntries.map(([label, score]) => {
      const pct = Math.round(score * 100);
      const isTop = Math.abs(score - (cls.confidence || 0)) < 0.05;
      return `
        <div class="space-y-1">
          <div class="flex justify-between items-center text-[10.5px]">
            <span class="${isTop ? 'text-primary font-bold' : 'text-on-surface-variant'}">${escapeHtml(label)}</span>
            <span class="${isTop ? 'text-primary font-bold' : 'text-on-surface-variant'}">${pct}%</span>
          </div>
          <div class="w-full h-1 bg-surface-container-low overflow-hidden">
            <div class="h-full ${isTop ? 'bg-primary' : 'bg-primary/30'}" style="width: ${pct}%"></div>
          </div>
        </div>
      `;
    }).join("");
  } else {
    dom.insightAllScoresList.innerHTML = `<span class="text-on-surface-variant">Deterministic heuristic classification active.</span>`;
  }

  // Extracted Facts
  const facts = cls.facts || {};
  dom.insightEmployeesVal.textContent = facts.employee_count_estimate || "unknown";
  dom.insightFoundedVal.textContent = facts.founded_year ? facts.founded_year.toString() : "unknown";

  // Culture & Sentiment
  const culture = data.culture_synthesis || {};
  const sent = culture.sentiment_breakdown || { positive_count: 0, negative_count: 0, total: 0 };
  const totalSent = sent.total || (sent.positive_count + sent.negative_count) || 1;
  const posPct = Math.round((sent.positive_count / totalSent) * 100);
  const negPct = 100 - posPct;

  dom.insightSentimentSummary.textContent = `${sent.positive_count} POSITIVE / ${sent.negative_count} NEGATIVE (${posPct}% POSITIVE)`;
  dom.insightSentimentPosBar.style.width = `${posPct}%`;
  dom.insightSentimentNegBar.style.width = `${negPct}%`;

  // Signal Strength & Note
  if (dom.insightSignalStrengthNote) {
    if (sent.signal_strength_note) {
      dom.insightSignalStrengthNote.textContent = sent.signal_strength_note;
      dom.insightSignalStrengthNote.classList.remove("hidden");
    } else {
      dom.insightSignalStrengthNote.classList.add("hidden");
    }
  }

  if (dom.insightSentimentBarTrack) {
    if (sent.signal_strength === "low") {
      dom.insightSentimentBarTrack.classList.add("opacity-60");
    } else {
      dom.insightSentimentBarTrack.classList.remove("opacity-60");
    }
  }

  // Praised Aspects
  const praised = culture.praised_aspects || [];
  dom.insightPraisedList.innerHTML = praised.map(p => `
    <li class="flex items-start gap-1.5">
      <span class="text-primary mt-0.5">•</span>
      <span>${escapeHtml(p)}</span>
    </li>
  `).join("");

  // Criticized Aspects
  const criticized = culture.criticized_aspects || [];
  dom.insightCriticizedList.innerHTML = criticized.map(c => `
    <li class="flex items-start gap-1.5">
      <span class="text-warning mt-0.5">•</span>
      <span>${escapeHtml(c)}</span>
    </li>
  `).join("");

  // Interview Intelligence
  const interview = data.interview_insights || {};
  const focusAreas = interview.focus_areas || [];
  dom.insightFocusAreasTags.innerHTML = focusAreas.map(f => `
    <span class="px-2.5 py-1 bg-secondary/10 border border-secondary/40 text-secondary font-label-mono text-[11px] uppercase">
      ${escapeHtml(f)}
    </span>
  `).join("");

  const stages = interview.process_stages || [];
  dom.insightProcessStagesList.innerHTML = stages.map(s => `
    <li>${escapeHtml(s)}</li>
  `).join("");

  const tips = interview.prep_tips || [];
  dom.insightPrepTipsList.innerHTML = tips.map(t => `
    <li>${escapeHtml(t)}</li>
  `).join("");
}

// ============================================================================
// Apply via Email (Outreach) Handlers & Rendering
// ============================================================================
const OUTREACH_RAYO_EXAMPLE = `🏢 Company: Rayo Innovations Pvt. Ltd.
💼 Open Positions:
* Web Designer
* Graphic Designer
* Android Developer
* iOS Developer
🎯 Experience: 0–1 Year / Freshers
📍 Location: Shyamal, Ahmedabad
🗓️ Working Days: 5 Days a Week
📧 Apply Via: hr@rayoinnovations.com
📞 Contact: +91 8799493952`;

function setOutreachStep(stepNum) {
  const steps = [
    dom.outreachStep1Indicator,
    dom.outreachStep2Indicator,
    dom.outreachStep3Indicator,
    dom.outreachStep4Indicator
  ];
  steps.forEach((el, idx) => {
    if (!el) return;
    const currentStep = idx + 1;
    el.classList.remove("step-indicator-active", "step-indicator-done");
    if (currentStep === stepNum) {
      el.classList.add("step-indicator-active");
    } else if (currentStep < stepNum) {
      el.classList.add("step-indicator-done");
    }
  });
}

function setupOutreachHandlers() {
  if (!dom.btnParseOutreach) return;

  // Preset example button
  if (dom.btnOutreachPresetRayo) {
    dom.btnOutreachPresetRayo.addEventListener("click", () => {
      dom.outreachJdText.value = OUTREACH_RAYO_EXAMPLE;
      showToast("Loaded Rayo Innovations example posting", "info");
      parseOutreachJD();
    });
  }

  // Fetch URL button
  if (dom.btnOutreachFetchUrl) {
    dom.btnOutreachFetchUrl.addEventListener("click", async () => {
      const url = (dom.outreachUrlInput.value || "").trim();
      if (!url) {
        showToast("Please enter a valid job URL to fetch", "warning");
        return;
      }
      showToast("Fetching job description from URL...", "info");
      parseOutreachJD(url);
    });
  }

  // Parse button
  dom.btnParseOutreach.addEventListener("click", () => {
    parseOutreachJD();
  });

  // Draft button
  if (dom.btnDraftOutreach) {
    dom.btnDraftOutreach.addEventListener("click", () => {
      draftOutreachEmail();
    });
  }

  // Connect Gmail button
  if (dom.btnOutreachConnectGmail) {
    dom.btnOutreachConnectGmail.addEventListener("click", async () => {
      try {
        const resp = await fetch(`/api/outreach/gmail/connect?user_external_id=${encodeURIComponent(state.userId)}`);
        const data = await resp.json();
        if (data.configured && data.auth_url) {
          const authWin = window.open(data.auth_url, "Google OAuth", "width=550,height=650");
          if (!authWin) {
            window.location.href = data.auth_url;
          }
        } else {
          showToast(
            "Google OAuth is running in local mode. Please configure GOOGLE_CLIENT_ID in .env or settings for live OAuth consent.",
            "warning"
          );
        }
      } catch (err) {
        showToast(`OAuth connection error: ${err.message}`, "error");
      }
    });
  }

  // Disconnect Gmail button
  if (dom.btnOutreachDisconnectGmail) {
    dom.btnOutreachDisconnectGmail.addEventListener("click", async () => {
      try {
        const resp = await fetch(`/api/outreach/gmail/disconnect?user_external_id=${encodeURIComponent(state.userId)}`, {
          method: "POST"
        });
        if (resp.ok) {
          showToast("Gmail access disconnected successfully", "info");
          checkGmailStatus();
        }
      } catch (err) {
        showToast(`Disconnect error: ${err.message}`, "error");
      }
    });
  }

  // Explicit Send button
  if (dom.btnSendOutreach) {
    dom.btnSendOutreach.addEventListener("click", () => {
      sendOutreachApplication();
    });
  }

  // View in Job Tracker shortcut
  if (dom.btnOutreachGotoTracker) {
    dom.btnOutreachGotoTracker.addEventListener("click", () => {
      switchTab("tab-jobs");
    });
  }

  // Matcher shortcut
  if (dom.btnMatcherApplyEmail) {
    dom.btnMatcherApplyEmail.addEventListener("click", () => {
      const comp = dom.matcherCompany.value.trim() || (state.lastMatchResult && state.lastMatchResult.company) || "";
      const role = dom.matcherRole.value.trim() || (state.lastMatchResult && state.lastMatchResult.role_title) || "";
      const jd = dom.matcherJdText.value.trim() || "";
      const url = dom.matcherJobUrl.value.trim() || "";

      let formattedText = jd;
      if (comp || role) {
        formattedText = `🏢 Company: ${comp || 'Company'}\n💼 Open Positions:\n* ${role || 'Role'}\n\n${jd}`.trim();
      }

      dom.outreachJdText.value = formattedText;
      dom.outreachUrlInput.value = url;

      switchTab("tab-outreach");
      showToast("Transferred matched JD to Apply via Email", "info");
      parseOutreachJD();
    });
  }

  // Listen for OAuth completion popup message
  window.addEventListener("message", (event) => {
    if (event.data && event.data.type === "GMAIL_CONNECTED") {
      checkGmailStatus();
      showToast(`Gmail account connected: ${event.data.email || ''}`, "success");
    }
  });
}

async function parseOutreachJD(urlParam = null) {
  const text = (dom.outreachJdText.value || "").trim();
  const url = (urlParam || dom.outreachUrlInput.value || "").trim();
  const resumeSelectVal = dom.outreachResumeSelectPicker ? dom.outreachResumeSelectPicker.value : "active";
  const resumeId = resumeSelectVal !== "active" ? resumeSelectVal : (state.activeResumeId || null);

  if (!text && !url) {
    showToast("Please paste job posting text or provide a JD URL", "warning");
    return;
  }

  dom.btnParseOutreach.disabled = true;
  dom.btnParseOutreach.innerHTML = `<span class="spinner" style="width:18px;height:18px;border-width:2px;margin:0;"></span> <span>PARSING JOB DETAILS...</span>`;

  try {
    const resp = await fetch("/api/outreach/parse-jd", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: text || null,
        url: url || null,
        user_external_id: state.userId,
        resume_id: resumeId
      })
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to parse job posting");
    }

    const data = await resp.json();
    const parsed = data.parsed || {};
    state.outreachParsedJD = parsed;

    // Populate Step 2 Fields
    dom.outreachFieldCompany.value = parsed.company_name || "";
    dom.outreachFieldEmail.value = parsed.hr_email || "";
    dom.outreachFieldPhone.value = parsed.contact_phone || "";
    dom.outreachFieldLocation.value = parsed.location || "";
    dom.outreachFieldExp.value = parsed.experience_required || "";
    dom.outreachFieldDays.value = parsed.working_days || "";

    // Missing email warning indicator
    if (!parsed.hr_email) {
      dom.outreachEmailMissingNote.classList.remove("hidden");
    } else {
      dom.outreachEmailMissingNote.classList.add("hidden");
    }

    // Role fit recommendation banner
    if (parsed.recommended_role) {
      dom.outreachRoleRecommendationBox.classList.remove("hidden");
      dom.outreachRoleRecommendationText.textContent = parsed.recommendation_reason || `Closest match based on your resume: ${parsed.recommended_role}`;
    } else {
      dom.outreachRoleRecommendationBox.classList.add("hidden");
    }

    // Render positions radio list
    const positions = parsed.open_positions && parsed.open_positions.length > 0
      ? parsed.open_positions
      : [(parsed.company_name ? `${parsed.company_name} Role` : "Software Engineer")];

    state.outreachSelectedRole = parsed.recommended_role || positions[0];

    dom.outreachRoleOptionsContainer.innerHTML = positions.map((pos, idx) => {
      const isSelected = pos === state.outreachSelectedRole;
      const isRecommended = pos === parsed.recommended_role;
      return `
        <div class="role-option-card ${isSelected ? 'selected' : ''}" data-role="${escapeHtml(pos)}">
          <label class="flex items-center gap-3 cursor-pointer w-full">
            <input type="radio" name="outreach_role_selection" value="${escapeHtml(pos)}" ${isSelected ? 'checked' : ''}/>
            <span class="font-label-mono text-[12px] font-bold text-on-surface flex-1">${escapeHtml(pos)}</span>
            ${isRecommended ? '<span class="cyber-badge cyber-badge-cyan text-[9.5px]">RECOMMENDED FIT</span>' : ''}
          </label>
        </div>
      `;
    }).join("");

    // Attach click listeners to role cards
    const roleCards = dom.outreachRoleOptionsContainer.querySelectorAll(".role-option-card");
    roleCards.forEach(card => {
      card.addEventListener("click", () => {
        const radio = card.querySelector("input[type='radio']");
        if (radio) radio.checked = true;
        roleCards.forEach(c => c.classList.remove("selected"));
        card.classList.add("selected");
        state.outreachSelectedRole = card.getAttribute("data-role");
      });
    });

    // Reveal Step 2
    dom.outreachStep2Empty.classList.add("hidden");
    dom.outreachStep2Content.classList.remove("hidden");
    setOutreachStep(2);
    showToast(`Extracted ${positions.length} position(s) from posting`, "success");

  } catch (err) {
    showToast(err.message, "error");
  } finally {
    dom.btnParseOutreach.disabled = false;
    dom.btnParseOutreach.innerHTML = `<span class="material-symbols-outlined text-[18px]">document_scanner</span> <span>PARSE JOB POSTING DETAILS</span>`;
  }
}

async function draftOutreachEmail() {
  const role = state.outreachSelectedRole || dom.outreachFieldCompany.value || "Role";
  const resumeSelectVal = dom.outreachResumeSelectPicker ? dom.outreachResumeSelectPicker.value : "active";
  const resumeId = resumeSelectVal !== "active" ? resumeSelectVal : (state.activeResumeId || null);

  const parsed_jd = {
    company_name: (dom.outreachFieldCompany.value || "").trim(),
    hr_email: (dom.outreachFieldEmail.value || "").trim() || null,
    contact_phone: (dom.outreachFieldPhone.value || "").trim() || null,
    location: (dom.outreachFieldLocation.value || "").trim() || null,
    experience_required: (dom.outreachFieldExp.value || "").trim() || null,
    working_days: (dom.outreachFieldDays.value || "").trim() || null,
    open_positions: state.outreachParsedJD?.open_positions || [role],
    raw_text: dom.outreachJdText.value || ""
  };

  dom.btnDraftOutreach.disabled = true;
  dom.outreachStep3Empty.classList.add("hidden");
  dom.outreachStep3Content.classList.add("hidden");
  dom.outreachStep3Loading.classList.remove("hidden");

  try {
    const resp = await fetch("/api/outreach/draft-email", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_external_id: state.userId,
        resume_id: resumeId,
        selected_role: role,
        parsed_jd: parsed_jd,
        applicant_name: dom.outreachApplicantName.value.trim() || undefined,
        custom_instructions: dom.outreachCustomInstructions.value.trim() || undefined
      })
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to draft application email");
    }

    const data = await resp.json();
    state.outreachDraft = data;

    // Populate Step 3 inputs
    dom.outreachEmailSubject.value = data.subject || `Application for ${role}`;
    dom.outreachEmailBody.value = data.body || "";
    dom.outreachEmailRecipientConfirm.value = data.recipient || dom.outreachFieldEmail.value || "";

    // Cliché check banner
    if (data.cliches_detected && data.cliches_detected.length > 0) {
      dom.outreachClicheStatusTag.textContent = `⚠️ ${data.cliches_detected.length} CLICHÉ(S) REVIEWED`;
      dom.outreachClicheStatusTag.className = "cyber-badge cyber-badge-alert text-[10px]";
    } else {
      dom.outreachClicheStatusTag.textContent = "✓ ZERO CLICHÉS DETECTED";
      dom.outreachClicheStatusTag.className = "cyber-badge cyber-badge-cyan text-[10px]";
    }

    // Fabrication Flags
    const flags = data.flagged_fabrications || [];
    if (flags.length > 0) {
      dom.outreachFabricationSummaryTag.textContent = `⚠️ ${flags.length} UNGROUNDED TERM(S) FLAGGED`;
      dom.outreachFabricationSummaryTag.className = "text-[10px] text-error font-bold";
      dom.outreachFabricationFlagsList.innerHTML = flags.map(f => `
        <div class="fabrication-flag-item">
          <div class="flex items-center justify-between font-bold text-error">
            <span>⚠️ '${escapeHtml(f.term)}'</span>
            <span class="text-[9.5px] uppercase">UNGROUNDED IN RESUME</span>
          </div>
          <p class="text-[10.5px] text-on-surface/90 mt-0.5">${escapeHtml(f.reason)}</p>
          <div class="text-[10px] text-on-surface-variant italic mt-1">"${escapeHtml(f.snippet)}"</div>
        </div>
      `).join("");
    } else {
      dom.outreachFabricationSummaryTag.textContent = "✓ 100% GROUNDED IN RESUME";
      dom.outreachFabricationSummaryTag.className = "text-[10px] text-success font-bold";
      dom.outreachFabricationFlagsList.innerHTML = `
        <div class="text-on-surface-variant text-[10.5px] italic">
          All technical tools, skills, and qualifications cited are verified against your uploaded resume.
        </div>
      `;
    }

    // Secondary AI Detector Signal
    if (data.ai_detector_score !== null && data.ai_detector_score !== undefined) {
      dom.outreachDetectorScoreText.textContent = `Secondary AI Signal: ${Math.round(data.ai_detector_score * 100)}%`;
    } else {
      dom.outreachDetectorScoreText.textContent = "Secondary AI Signal: Offline Heuristic Active";
    }

    // Reveal Step 3 & activate Step 4
    dom.outreachStep3Loading.classList.add("hidden");
    dom.outreachStep3Content.classList.remove("hidden");
    setOutreachStep(3);
    showToast("Application email drafted successfully!", "success");

  } catch (err) {
    dom.outreachStep3Loading.classList.add("hidden");
    dom.outreachStep3Empty.classList.remove("hidden");
    showToast(err.message, "error");
  } finally {
    dom.btnDraftOutreach.disabled = false;
  }
}

async function checkGmailStatus() {
  try {
    const resp = await fetch(`/api/outreach/gmail/status?user_external_id=${encodeURIComponent(state.userId)}`);
    if (!resp.ok) return;

    const data = await resp.json();
    state.gmailConnected = data.connected;

    if (data.connected) {
      if (dom.outreachAuthCardDot) dom.outreachAuthCardDot.className = "w-2.5 h-2.5 rounded-full bg-success";
      if (dom.outreachAuthCardStatus) dom.outreachAuthCardStatus.textContent = `Connected as ${data.email || 'Authenticated User'}`;
      if (dom.outreachAuthCardDesc) dom.outreachAuthCardDesc.textContent = "Scope: https://www.googleapis.com/auth/gmail.send (Send-only access active).";
      if (dom.btnOutreachConnectGmail) dom.btnOutreachConnectGmail.classList.add("hidden");
      if (dom.btnOutreachDisconnectGmail) dom.btnOutreachDisconnectGmail.classList.remove("hidden");

      if (dom.outreachAuthIndicatorDot) dom.outreachAuthIndicatorDot.className = "w-2 h-2 rounded-full bg-success";
      if (dom.outreachHeaderAuthText) {
        dom.outreachHeaderAuthText.textContent = `GMAIL_ONLINE (${(data.email || '').split('@')[0] || 'ACTIVE'})`;
        dom.outreachHeaderAuthText.className = "text-success font-bold";
      }
    } else {
      if (dom.outreachAuthCardDot) dom.outreachAuthCardDot.className = "w-2.5 h-2.5 rounded-full bg-warning";
      if (dom.outreachAuthCardStatus) dom.outreachAuthCardStatus.textContent = "Gmail Not Connected";
      if (dom.outreachAuthCardDesc) dom.outreachAuthCardDesc.textContent = "Requires one-time OAuth authorization (https://www.googleapis.com/auth/gmail.send).";
      if (dom.btnOutreachConnectGmail) dom.btnOutreachConnectGmail.classList.remove("hidden");
      if (dom.btnOutreachDisconnectGmail) dom.btnOutreachDisconnectGmail.classList.add("hidden");

      if (dom.outreachAuthIndicatorDot) dom.outreachAuthIndicatorDot.className = "w-2 h-2 rounded-full bg-on-surface-variant";
      if (dom.outreachHeaderAuthText) {
        dom.outreachHeaderAuthText.textContent = "GMAIL_OFFLINE";
        dom.outreachHeaderAuthText.className = "text-on-surface-variant";
      }
    }
  } catch (err) {
    console.error("Failed to check Gmail status:", err);
  }
}

async function sendOutreachApplication() {
  const recipient = (dom.outreachEmailRecipientConfirm.value || "").trim();
  const subject = (dom.outreachEmailSubject.value || "").trim();
  const body = (dom.outreachEmailBody.value || "").trim();

  if (!recipient || !recipient.includes("@")) {
    showToast("Please enter a valid recipient HR email address", "warning");
    dom.outreachEmailRecipientConfirm.focus();
    return;
  }
  if (!subject) {
    showToast("Email subject cannot be empty", "warning");
    dom.outreachEmailSubject.focus();
    return;
  }
  if (!body) {
    showToast("Email body cannot be empty", "warning");
    dom.outreachEmailBody.focus();
    return;
  }

  if (!state.gmailConnected) {
    showToast("Please click 'CONNECT GMAIL' to authorize your Gmail account before sending", "warning");
    return;
  }

  dom.btnSendOutreach.disabled = true;
  dom.btnSendOutreach.innerHTML = `<span class="spinner" style="width:18px;height:18px;border-width:2px;margin:0;"></span> <span>TRANSMITTING VIA GMAIL API...</span>`;

  try {
    const resp = await fetch("/api/outreach/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_external_id: state.userId,
        to_email: recipient,
        subject: subject,
        body: body,
        company_name: (dom.outreachFieldCompany.value || "").trim() || undefined,
        role_title: state.outreachSelectedRole || undefined,
        attach_resume_id: dom.outreachAttachResumeCheckbox.checked ? (state.activeResumeId || null) : null,
        log_to_tracker: dom.outreachLogTrackerCheckbox.checked
      })
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to send email via Gmail API");
    }

    const data = await resp.json();

    // Show success card
    dom.outreachSendResultCard.classList.remove("hidden");
    dom.outreachResultMsgId.textContent = data.message_id || `msg-${Date.now()}`;
    dom.outreachResultTimestamp.textContent = new Date(data.timestamp).toLocaleString();
    dom.outreachResultRecipient.textContent = data.recipient;

    setOutreachStep(4);
    showToast("Application email sent successfully via Gmail!", "success");

    if (data.job_application_id) {
      loadJobs();
    }
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    dom.btnSendOutreach.disabled = false;
    dom.btnSendOutreach.innerHTML = `<span class="material-symbols-outlined text-[20px]">send</span> <span>SEND APPLICATION VIA GMAIL</span>`;
  }
}


async function handleResumeFileUpload(file) {
  showToast(`Parsing resume (${file.name})...`, "info");
  const formData = new FormData();
  formData.append("user_external_id", state.userId);
  formData.append("title", file.name.replace(/\.[^/.]+$/, ""));
  formData.append("file", file);

  try {
    const resp = await fetch("/matcher/upload-resume", {
      method: "POST",
      body: formData
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to parse resume");
    }

    const data = await resp.json();
    dom.matcherResumeText.value = data.resume_text;
    dom.resumeTitleInput.value = data.title || file.name;
    if (dom.atsResumeText) dom.atsResumeText.value = data.resume_text;
    showToast(`Parsed ${data.char_count} characters from resume!`, "success");
    loadResumes();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    dom.resumeFileInput.value = "";
  }
}

async function loadResumes() {
  try {
    const resp = await fetch(`/matcher/resumes/${state.userId}`);
    if (!resp.ok) return;

    const resumes = await resp.json();
    state.resumes = resumes;

    const optionsHtml = `<option value="new">+ Upload / Enter New Resume</option>` +
      resumes.map(r => `
        <option value="${r.id}" ${state.activeResumeId === r.id ? 'selected' : ''}>
          ${escapeHtml(r.title)} (${(r.resume_text || '').length} chars)
        </option>
      `).join("");

    dom.resumeSelectPicker.innerHTML = optionsHtml;
    if (dom.atsResumeSelectPicker) {
      dom.atsResumeSelectPicker.innerHTML = optionsHtml;
    }
    if (dom.outreachResumeSelectPicker) {
      dom.outreachResumeSelectPicker.innerHTML = `<option value="active">Active Selected Resume</option>` +
        resumes.map(r => `
          <option value="${r.id}" ${state.activeResumeId === r.id ? 'selected' : ''}>
            ${escapeHtml(r.title)} (${(r.resume_text || '').length} chars)
          </option>
        `).join("");
    }

    if (resumes.length > 0 && !state.activeResumeId) {
      state.activeResumeId = resumes[0].id;
      dom.resumeSelectPicker.value = resumes[0].id;
      dom.matcherResumeText.value = resumes[0].resume_text;
      dom.resumeTitleInput.value = resumes[0].title;
      if (dom.atsResumeText && !dom.atsResumeText.value) {
        dom.atsResumeText.value = resumes[0].resume_text;
      }
      dom.btnDeleteActiveResume.classList.remove("hidden");
    } else if (!resumes.length) {
      dom.btnDeleteActiveResume.classList.add("hidden");
    }
  } catch (err) {
    console.error("Failed to load resumes:", err);
  }
}

function renderMatchResults(res) {
  dom.matcherLoadingState.classList.add("hidden");
  dom.matcherEmptyState.classList.add("hidden");
  dom.matcherResultsView.classList.remove("hidden");

  // Score Number & Class
  dom.matchScoreVal.innerHTML = `${res.match_score}<span class="text-[32px] text-primary/70">%</span>`;
  if (dom.gaugeCircle) {
    dom.gaugeCircle.className = "gauge-circle";
    if (res.match_score >= 80) dom.gaugeCircle.classList.add("score-strong");
    else if (res.match_score >= 65) dom.gaugeCircle.classList.add("score-good");
    else if (res.match_score >= 50) dom.gaugeCircle.classList.add("score-moderate");
    else dom.gaugeCircle.classList.add("score-low");
  }

  // Verdict Pill
  dom.matchVerdictPill.textContent = res.verdict.toUpperCase();
  dom.matchVerdictPill.className = "px-4 py-1.5 border border-secondary text-secondary font-label-mono text-[11px] uppercase tracking-widest glow-secondary bg-secondary/10";
  if (res.match_score < 50) {
    dom.matchVerdictPill.className = "px-4 py-1.5 border border-error text-error font-label-mono text-[11px] uppercase tracking-widest glow-error bg-error/10";
  }

  // Meta & Summary
  dom.matchTargetRole.textContent = res.role_title || "Job Position";
  dom.matchTargetCompany.textContent = res.company || "Target Company";
  dom.matchSummaryText.textContent = res.summary;

  // Strengths
  dom.matchStrengthsList.innerHTML = (res.key_strengths || [])
    .map(s => `<li>${escapeHtml(s)}</li>`)
    .join("");

  // Experience fit
  dom.matchExperienceFit.innerHTML = `<strong>Experience Fit:</strong> ${escapeHtml(res.experience_fit || 'Matches criteria')}`;

  // Matched Skills Tags
  dom.skillsMatchedTags.innerHTML = (res.skills_matched || []).length > 0
    ? res.skills_matched.map(s => `<span class="skill-tag skill-tag-matched">✓ ${escapeHtml(s)}</span>`).join("")
    : '<span class="text-muted" style="font-size:12px;">No direct skill matches identified</span>';

  // Missing Skills Tags
  dom.skillsMissingTags.innerHTML = (res.missing_skills || []).length > 0
    ? res.missing_skills.map(s => `<span class="skill-tag skill-tag-missing">✗ ${escapeHtml(s)}</span>`).join("")
    : '<span class="text-muted" style="font-size:12px;">No critical skill gaps detected!</span>';

  // Recommendations
  dom.matchRecommendationsList.innerHTML = (res.recommendations || [])
    .map(r => `<li>${escapeHtml(r)}</li>`)
    .join("");

  // Tailored Pitch
  dom.matchPitchText.textContent = `"${res.tailored_pitch || 'I am excited to apply for this role...'}"`;
}

// ============================================================================
// Job Application Tracker
// ============================================================================
function setupJobHandlers() {
  dom.btnOpenJobModal.addEventListener("click", () => dom.jobModal.classList.remove("hidden"));
  dom.btnCloseModal.addEventListener("click", () => dom.jobModal.classList.add("hidden"));
  dom.btnCancelModal.addEventListener("click", () => dom.jobModal.classList.add("hidden"));

  dom.jobSearchInput.addEventListener("input", filterAndRenderJobs);
  dom.jobStatusFilter.addEventListener("change", (e) => {
    state.activeJobFilter = e.target.value;
    filterAndRenderJobs();
  });
  dom.jobSortSelect.addEventListener("change", (e) => {
    state.activeJobSort = e.target.value;
    filterAndRenderJobs();
  });

  dom.jobForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const company = document.getElementById("job-company").value.trim();
    const role = document.getElementById("job-role").value.trim();
    const url = document.getElementById("job-url").value.trim();
    const followup = parseInt(document.getElementById("job-followup").value, 10) || 7;
    const notes = document.getElementById("job-notes").value.trim();

    try {
      const resp = await fetch("/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_external_id: state.userId,
          company: company,
          role_title: role,
          job_url: url || null,
          follow_up_days: followup,
          notes: notes || null
        })
      });

      if (!resp.ok) throw new Error("Failed to create job application");

      dom.jobModal.classList.add("hidden");
      dom.jobForm.reset();
      showToast(`Logged application for ${company}`, "success");
      loadJobs();
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

async function loadJobs() {
  try {
    const [jobsResp, dueResp] = await Promise.all([
      fetch(`/jobs/${state.userId}`),
      fetch(`/jobs/${state.userId}/due-followups`)
    ]);

    const jobs = jobsResp.ok ? await jobsResp.json() : [];
    const dueJobs = dueResp.ok ? await dueResp.json() : [];

    state.jobs = jobs;
    state.dueJobs = dueJobs;

    dom.statTotalJobs.textContent = jobs.length;
    dom.statActiveJobs.textContent = jobs.filter(j => ["applied", "interview", "no_response"].includes(j.status)).length;
    dom.statOfferJobs.textContent = jobs.filter(j => j.status === "offer").length;
    if (dom.statRejectedJobs) dom.statRejectedJobs.textContent = jobs.filter(j => j.status === "rejected").length;
    dom.statDueJobs.textContent = dueJobs.length;

    if (dueJobs.length > 0) {
      dom.jobsDueBadge.textContent = dueJobs.length;
      dom.jobsDueBadge.classList.remove("hidden");
      dom.jobsAlertBanner.classList.remove("hidden");
      dom.jobsAlertText.innerHTML = `<strong>${dueJobs.length} application(s) due for follow-up:</strong> ` +
        dueJobs.map(j => `${escapeHtml(j.company)} (${escapeHtml(j.role_title)})`).join(", ");
    } else {
      dom.jobsDueBadge.classList.add("hidden");
      dom.jobsAlertBanner.classList.add("hidden");
    }

    filterAndRenderJobs();
  } catch (err) {
    console.error("Failed to load jobs:", err);
  }
}

function filterAndRenderJobs() {
  const query = (dom.jobSearchInput.value || "").toLowerCase().trim();
  const filter = state.activeJobFilter;
  const sort = state.activeJobSort;

  let list = [...state.jobs];

  // 1. Filter by Status
  if (filter === "due") {
    const dueIds = new Set(state.dueJobs.map(d => d.id));
    list = list.filter(j => dueIds.has(j.id));
  } else if (filter !== "all") {
    list = list.filter(j => j.status === filter);
  }

  // 2. Search query
  if (query) {
    list = list.filter(j =>
      (j.company || "").toLowerCase().includes(query) ||
      (j.role_title || "").toLowerCase().includes(query) ||
      (j.notes || "").toLowerCase().includes(query)
    );
  }

  // 3. Sorting
  if (sort === "newest") {
    list.sort((a, b) => new Date(b.applied_date || 0) - new Date(a.applied_date || 0));
  } else if (sort === "oldest") {
    list.sort((a, b) => new Date(a.applied_date || 0) - new Date(b.applied_date || 0));
  } else if (sort === "followup") {
    list.sort((a, b) => new Date(a.follow_up_date || 0) - new Date(b.follow_up_date || 0));
  } else if (sort === "score") {
    list.sort((a, b) => (b.match_score || 0) - (a.match_score || 0));
  } else if (sort === "company") {
    list.sort((a, b) => (a.company || "").localeCompare(b.company || ""));
  }

  if (!list.length) {
    dom.jobsList.innerHTML = `
      <div class="bg-surface-container border border-outline-variant p-8 tech-card flex flex-col items-center justify-center text-center gap-3">
        <span class="material-symbols-outlined text-[36px] text-primary">work_off</span>
        <h4 class="font-headline-lg text-[16px] text-on-surface">${state.jobs.length === 0 ? "NO_APPLICATIONS_LOGGED_YET" : "NO_MATCHING_APPLICATIONS"}</h4>
        <p class="font-label-mono text-[12px] text-on-surface-variant max-w-sm">${state.jobs.length === 0 ? "Click 'LOG_NEW_APPLICATION' above or use the Resume Matcher to track your first job." : "Try adjusting your search query or status filter."}</p>
      </div>
    `;
    return;
  }

  const statuses = [
    { key: "applied", label: "APPLIED" },
    { key: "interview", label: "INTERVIEWING" },
    { key: "offer", label: "OFFER" },
    { key: "rejected", label: "REJECTED" },
    { key: "no_response", label: "NO RESPONSE" }
  ];

  dom.jobsList.innerHTML = list.map((j, idx) => {
    let scoreBadge = '';
    if (j.match_score != null && j.match_score > 0) {
      const cls = j.match_score >= 80 ? 'job-score-strong' : j.match_score >= 65 ? 'job-score-good' : j.match_score >= 50 ? 'job-score-moderate' : 'job-score-low';
      scoreBadge = `<span class="job-score-pill ${cls}">🎯 ${Math.round(j.match_score)}% FIT</span>`;
    }

    let statusPill = '';
    if (j.status === 'offer') {
      statusPill = `<span class="status-pill-cyber status-badge-offer"><span class="dot"></span>OFFER_RECEIVED</span>`;
    } else if (j.status === 'interview') {
      statusPill = `<span class="status-pill-cyber status-badge-interview"><span class="dot"></span>INTERVIEW_ACTIVE</span>`;
    } else if (j.status === 'applied') {
      statusPill = `<span class="status-pill-cyber status-badge-applied"><span class="dot"></span>APPLIED</span>`;
    } else if (j.status === 'rejected') {
      statusPill = `<span class="status-pill-cyber status-badge-rejected"><span class="dot"></span>REJECTED</span>`;
    } else {
      statusPill = `<span class="status-pill-cyber status-badge-applied"><span class="dot"></span>AWAITING</span>`;
    }

    const entityCode = `01${(idx + 1).toString().padStart(3, '0')}`;

    return `
      <div class="job-card-structured tech-card job-card-${j.status}" id="job-card-${j.id}">
        <div class="job-header-row">
          <div class="job-title-group">
            <div class="job-company-badge-wrap">
              <span class="job-entity-tag">${entityCode}</span>
              <span class="job-company-name">${escapeHtml(j.company)}</span>
              ${statusPill}
              ${scoreBadge}
              ${j.job_url ? `<a href="${escapeHtml(j.job_url)}" target="_blank" class="font-label-mono text-[11px] text-secondary hover:underline inline-flex items-center gap-1"><span>🔗 Post</span></a>` : ''}
            </div>
            <span class="job-role-text">${escapeHtml(j.role_title)}</span>
          </div>
          <div class="flex items-center gap-2">
            <select class="status-select" onchange="updateJobStatus('${j.id}', this.value)">
              ${statuses.map(s => `<option value="${s.key}" ${j.status === s.key ? 'selected' : ''}>${s.label}</option>`).join("")}
            </select>
            <button class="btn-card-action danger" onclick="deleteJob('${j.id}')" title="Delete job">
              <span class="material-symbols-outlined text-[16px]">delete</span>
            </button>
          </div>
        </div>

        ${j.tailored_pitch ? `
          <div class="job-pitch-box">
            <div class="job-pitch-header">
              <span>✉️ TAILORED OUTREACH PITCH:</span>
              <button class="btn-card-action" onclick="copyJobPitch('${j.id}')">📋 Copy</button>
            </div>
            <div class="job-pitch-text" id="pitch-text-${j.id}">${escapeHtml(j.tailored_pitch)}</div>
          </div>
        ` : ''}

        ${j.notes ? `
          <div class="p-2.5 bg-surface-container-low border-l-2 border-primary font-label-mono text-[11.5px] text-on-surface">${escapeHtml(j.notes).replace(/\n/g, '<br>')}</div>
        ` : ''}

        <div class="job-meta-footer">
          <div class="flex items-center gap-4 font-label-mono text-[11px] text-on-surface-variant">
            <span>📅 ${(j.applied_date || '').substring(0, 10)}</span>
            <span>⏰ FOLLOW-UP: <strong class="text-secondary">${(j.follow_up_date || 'N/A').substring(0, 10)}</strong></span>
          </div>
          <span class="font-label-mono text-[10px] text-on-surface-variant">ID: ${j.id ? j.id.substring(0, 8) : '0000'}</span>
        </div>
      </div>
    `;
  }).join("");
}

window.copyJobPitch = function(jobId) {
  const el = document.getElementById(`pitch-text-${jobId}`);
  if (el) {
    navigator.clipboard.writeText(el.innerText);
    showToast("Pitch copied to clipboard!", "success");
  }
};

window.updateJobStatus = async function(jobId, newStatus) {
  const cardEl = document.getElementById(`job-card-${jobId}`);
  if (cardEl) {
    cardEl.classList.remove("animate-flash-red", "animate-flash-green", "animate-flash-magenta", "job-card-offer", "job-card-interview", "job-card-rejected", "job-card-applied");
    void cardEl.offsetWidth; // Trigger DOM reflow for restart

    if (newStatus === "rejected") {
      cardEl.classList.add("job-card-rejected");
      showToast("Status updated to Rejected", "error");
    } else if (newStatus === "offer") {
      cardEl.classList.add("job-card-offer");
      showToast("🎉 Status updated to Offer!", "success");
    } else if (newStatus === "interview") {
      cardEl.classList.add("job-card-interview");
      showToast("Status updated to Interviewing", "info");
    } else {
      cardEl.classList.add("job-card-applied");
      showToast(`Status updated to ${newStatus.replace('_', ' ')}`, "info");
    }
  }

  try {
    const resp = await fetch(`/jobs/${jobId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus })
    });

    if (!resp.ok) throw new Error("Failed to update status");
    setTimeout(loadJobs, 400);
  } catch (err) {
    showToast(err.message, "error");
  }
};

window.deleteJob = async function(jobId) {
  if (!confirm("Are you sure you want to delete this job application?")) return;
  try {
    const resp = await fetch(`/jobs/${jobId}`, { method: "DELETE" });
    if (!resp.ok) throw new Error("Failed to delete job application");
    showToast("Application deleted", "info");
    loadJobs();
  } catch (err) {
    showToast(err.message, "error");
  }
};

// ============================================================================
// AI Model & API Key Settings Handlers
// ============================================================================
function setupSettingsHandlers() {
  if (dom.btnOpenSettings) {
    dom.btnOpenSettings.addEventListener("click", () => {
      loadSettings();
      dom.settingsModal.classList.remove("hidden");
    });
  }

  if (dom.btnCloseSettings) {
    dom.btnCloseSettings.addEventListener("click", () => dom.settingsModal.classList.add("hidden"));
  }

  if (dom.btnCancelSettings) {
    dom.btnCancelSettings.addEventListener("click", () => dom.settingsModal.classList.add("hidden"));
  }

  if (dom.settingsLlmProvider) {
    dom.settingsLlmProvider.addEventListener("change", () => {
      const provider = dom.settingsLlmProvider.value;
      if (provider === "groq") {
        dom.groqKeyGroup.classList.remove("hidden");
        dom.anthropicKeyGroup.classList.add("hidden");
      } else {
        dom.groqKeyGroup.classList.add("hidden");
        dom.anthropicKeyGroup.classList.remove("hidden");
      }
    });
  }

  if (dom.settingsForm) {
    dom.settingsForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const provider = dom.settingsLlmProvider.value;
      const groqKey = dom.settingsGroqKey.value.trim();
      const anthropicKey = dom.settingsAnthropicKey.value.trim();

      try {
        const resp = await fetch("/api/settings", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            llm_provider: provider,
            groq_api_key: groqKey || undefined,
            anthropic_api_key: anthropicKey || undefined
          })
        });

        if (!resp.ok) throw new Error("Failed to save settings");

        dom.settingsModal.classList.add("hidden");
        showToast("AI API Key saved successfully!", "success");
      } catch (err) {
        showToast(`Settings error: ${err.message}`, "error");
      }
    });
  }
}

async function loadSettings() {
  try {
    const resp = await fetch("/api/settings");
    if (!resp.ok) return;

    const data = await resp.json();
    if (dom.settingsLlmProvider) dom.settingsLlmProvider.value = data.llm_provider || "groq";

    if (dom.settingsGroqKey) {
      dom.settingsGroqKey.placeholder = data.groq_api_key_configured
        ? "•••••••••••• (API Key Active & Configured)"
        : "Enter your Groq key (e.g. gsk_...)";
    }

    if (dom.settingsAnthropicKey) {
      dom.settingsAnthropicKey.placeholder = data.anthropic_api_key_configured
        ? "•••••••••••• (API Key Active & Configured)"
        : "Enter your Anthropic key (sk-ant-...)";
    }

    if (dom.settingsLlmProvider) {
      if (data.llm_provider === "anthropic") {
        dom.groqKeyGroup.classList.add("hidden");
        dom.anthropicKeyGroup.classList.remove("hidden");
      } else {
        dom.groqKeyGroup.classList.remove("hidden");
        dom.anthropicKeyGroup.classList.add("hidden");
      }
    }
  } catch (err) {
    console.error("Failed to load settings:", err);
  }
}

// ============================================================================
// Utilities & Health Check
// ============================================================================
async function checkHealth() {
  try {
    const resp = await fetch("/health");
    if (resp.ok) {
      dom.serverStatus.classList.add("online");
      dom.serverStatus.title = "FastAPI backend online";
    } else {
      dom.serverStatus.classList.remove("online");
      dom.serverStatus.title = "FastAPI backend error";
    }
  } catch {
    dom.serverStatus.classList.remove("online");
    dom.serverStatus.title = "Backend unreachable";
  }
}

function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  const icon = type === "success" ? "✅" : type === "error" ? "❌" : type === "warning" ? "⚠️" : "💡";
  toast.innerHTML = `<span>${icon}</span> <span>${escapeHtml(message)}</span>`;
  
  dom.toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 300);
  }, 4500);
}

function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
