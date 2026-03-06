const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("path");
const Anthropic = require("@anthropic-ai/sdk");

let mainWindow;
let anthropicClient = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
    title: "Workflow AI",
  });

  mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"));
}

// Initialize the Anthropic client with the provided API key
ipcMain.handle("set-api-key", async (_event, apiKey) => {
  try {
    anthropicClient = new Anthropic({ apiKey });
    // Test the key with a minimal request
    await anthropicClient.messages.create({
      model: "claude-sonnet-4-20250514",
      max_tokens: 10,
      messages: [{ role: "user", content: "Hi" }],
    });
    return { success: true };
  } catch (error) {
    anthropicClient = null;
    return { success: false, error: error.message };
  }
});

// Send a message to Claude
ipcMain.handle("send-message", async (_event, { messages, systemPrompt }) => {
  if (!anthropicClient) {
    return { success: false, error: "API key not set. Please configure your Claude API key." };
  }

  try {
    const params = {
      model: "claude-sonnet-4-20250514",
      max_tokens: 4096,
      messages,
    };
    if (systemPrompt) {
      params.system = systemPrompt;
    }

    const response = await anthropicClient.messages.create(params);
    const text = response.content
      .filter((block) => block.type === "text")
      .map((block) => block.text)
      .join("\n");

    return { success: true, text, usage: response.usage };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
