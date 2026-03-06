const SYSTEM_PROMPTS = {
  "": "You are a helpful AI workflow assistant. Be concise and practical.",
  email:
    "You are an email drafting assistant. Help compose professional, clear emails. Ask for context like recipient, tone, and purpose if not provided.",
  report:
    "You are a report writing assistant. Help structure and write professional reports with clear sections, data-driven insights, and executive summaries.",
  analysis:
    "You are a data analysis assistant. Help interpret data, suggest analyses, and explain findings in plain language.",
  code: "You are a code review assistant. Review code for bugs, performance issues, security concerns, and best practices. Provide specific suggestions.",
};

let conversationHistory = [];

// DOM elements
const apiKeyModal = document.getElementById("api-key-modal");
const apiKeyInput = document.getElementById("api-key-input");
const apiKeyError = document.getElementById("api-key-error");
const saveApiKeyBtn = document.getElementById("save-api-key");
const changeApiKeyBtn = document.getElementById("change-api-key");
const appEl = document.getElementById("app");
const chatMessages = document.getElementById("chat-messages");
const typingIndicator = document.getElementById("typing-indicator");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const workflowSelect = document.getElementById("workflow-select");

// API Key handling
saveApiKeyBtn.addEventListener("click", async () => {
  const key = apiKeyInput.value.trim();
  if (!key) return;

  saveApiKeyBtn.disabled = true;
  saveApiKeyBtn.textContent = "Connecting...";
  apiKeyError.classList.add("hidden");

  const result = await window.api.setApiKey(key);

  if (result.success) {
    apiKeyModal.classList.add("hidden");
    appEl.classList.remove("hidden");
    addMessage(
      "assistant",
      "Connected! I'm your Workflow AI assistant powered by Claude. Choose a workflow mode above or just start chatting."
    );
  } else {
    apiKeyError.textContent = "Connection failed: " + result.error;
    apiKeyError.classList.remove("hidden");
  }

  saveApiKeyBtn.disabled = false;
  saveApiKeyBtn.textContent = "Connect";
});

changeApiKeyBtn.addEventListener("click", () => {
  apiKeyModal.classList.remove("hidden");
});

apiKeyInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") saveApiKeyBtn.click();
});

// Chat
function addMessage(role, text) {
  const div = document.createElement("div");
  div.className = `message ${role}`;
  div.textContent = text;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function sendMessage() {
  const text = userInput.value.trim();
  if (!text) return;

  addMessage("user", text);
  userInput.value = "";
  sendBtn.disabled = true;

  conversationHistory.push({ role: "user", content: text });

  typingIndicator.classList.remove("hidden");
  chatMessages.scrollTop = chatMessages.scrollHeight;

  const systemPrompt = SYSTEM_PROMPTS[workflowSelect.value];
  const result = await window.api.sendMessage({
    messages: conversationHistory,
    systemPrompt,
  });

  typingIndicator.classList.add("hidden");
  sendBtn.disabled = false;

  if (result.success) {
    addMessage("assistant", result.text);
    conversationHistory.push({ role: "assistant", content: result.text });
  } else {
    addMessage("assistant", "Error: " + result.error);
  }

  userInput.focus();
}

sendBtn.addEventListener("click", sendMessage);

userInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

// Reset conversation on workflow change
workflowSelect.addEventListener("change", () => {
  conversationHistory = [];
  chatMessages.innerHTML = "";
  const label =
    workflowSelect.options[workflowSelect.selectedIndex].text;
  addMessage("assistant", `Switched to ${label} mode. How can I help?`);
});
