const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("api", {
  setApiKey: (apiKey) => ipcRenderer.invoke("set-api-key", apiKey),
  sendMessage: (data) => ipcRenderer.invoke("send-message", data),
});
