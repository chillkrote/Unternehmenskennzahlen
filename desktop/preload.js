const { contextBridge, ipcRenderer } = require("electron");
contextBridge.exposeInMainWorld("tokenDialog", {
  senden: t => ipcRenderer.send("token:ok", t),
  abbrechen: () => ipcRenderer.send("token:abbruch"),
});
