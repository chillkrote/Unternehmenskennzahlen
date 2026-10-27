const { app, BrowserWindow, Menu, dialog, ipcMain, safeStorage, shell, net } = require("electron");
const fs = require("fs");
const path = require("path");

const REPO = "chillkrote/Unternehmenskennzahlen";
const DATEI_IM_REPO = "app/dist/bankterminal.html";
const MIT = app.isPackaged ? process.resourcesPath : path.join(__dirname, "build");

let fenster = null;
const ordner = () => path.join(app.getPath("userData"), "daten");
const datenDatei = () => path.join(ordner(), "bankterminal.html");
const metaDatei = () => path.join(ordner(), "meta.json");
const tokenDatei = () => path.join(app.getPath("userData"), "token.bin");
const lies = (p, d) => { try { return JSON.parse(fs.readFileSync(p, "utf8")); } catch { return d; } };

function holeToken() {
  try { return safeStorage.decryptString(fs.readFileSync(tokenDatei())); } catch { return null; }
}

// Nimmt die zuletzt geladene Fassung (Daten-Update), sonst die mitgelieferte, und tauscht die Google-Schriften gegen lokale.
function seiteVorbereiten() {
  const quelle = fs.existsSync(datenDatei()) ? datenDatei() : path.join(MIT, "terminal.html");
  let html = fs.readFileSync(quelle, "utf8");
  const css = "file://" + path.join(MIT, "fonts/fonts.css").split(path.sep).map(encodeURIComponent).join("/").replace(/^\/\//, "/");
  html = html.replace(/<link rel="preconnect"[^>]*>\s*/g, "").replace(/<link rel="stylesheet" href="https:\/\/fonts\.googleapis\.com[^>]*>/, `<link rel="stylesheet" href="${css}">`);
  const ziel = path.join(app.getPath("userData"), "aktuell.html");
  fs.writeFileSync(ziel, html);
  return ziel;
}

function laden() {
  fenster.loadFile(seiteVorbereiten());
}

function tokenAbfragen() {
  return new Promise(resolve => {
    const w = new BrowserWindow({ width: 460, height: 290, parent: fenster, modal: true, resizable: false, minimizable: false, title: "GitHub-Token",
      webPreferences: { preload: path.join(__dirname, "preload.js"), contextIsolation: true } });
    w.setMenu(null);
    let fertig = false;
    const ende = t => { if (fertig) return; fertig = true; ipcMain.removeAllListeners("token:ok"); ipcMain.removeAllListeners("token:abbruch"); w.destroy(); resolve(t); };
    ipcMain.once("token:ok", (_e, t) => ende(t || null));
    ipcMain.once("token:abbruch", () => ende(null));
    w.on("closed", () => ende(null));
    w.loadFile(path.join(__dirname, "token.html"));
  });
}

async function datenAktualisieren() {
  const abruf = async token => net.fetch(`https://api.github.com/repos/${REPO}/contents/${DATEI_IM_REPO}`, {
    headers: { Accept: "application/vnd.github.raw+json", "User-Agent": "Terminal-Desktop", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  });
  try {
    let token = holeToken();
    let r = await abruf(token);
    if ([401, 403, 404].includes(r.status)) {
      if (!safeStorage.isEncryptionAvailable()) throw new Error("Schlüsselbund nicht verfügbar");
      token = await tokenAbfragen();
      if (!token) return;
      r = await abruf(token);
      if (r.ok) fs.writeFileSync(tokenDatei(), safeStorage.encryptString(token), { mode: 0o600 });
    }
    if (!r.ok) throw new Error(`GitHub antwortet mit ${r.status}${r.status === 404 || r.status === 401 ? " – Token ungültig oder ohne Lesezugriff auf das Repo" : ""}`);
    const html = await r.text();
    if (!/<title>Terminal<\/title>/.test(html) || html.length < 100000) throw new Error("Die geladene Datei ist kein Terminal");
    fs.mkdirSync(ordner(), { recursive: true });
    fs.writeFileSync(datenDatei(), html);
    fs.writeFileSync(metaDatei(), JSON.stringify({ geladen: new Date().toISOString(), bytes: html.length }));
    laden();
    dialog.showMessageBox(fenster, { type: "info", message: "Daten aktualisiert", detail: `Neueste Fassung aus ${REPO} geladen (${(html.length / 1e6).toFixed(1)} MB).` });
  } catch (e) {
    dialog.showMessageBox(fenster, { type: "error", message: "Daten-Update fehlgeschlagen", detail: String(e.message || e) + "\nDie bisherigen Daten bleiben erhalten." });
  }
}

function zurueckAufMitgelieferte() {
  fs.rmSync(ordner(), { recursive: true, force: true });
  laden();
}

function menue() {
  const meta = lies(metaDatei(), null);
  const stand = meta ? "Zuletzt aktualisiert: " + new Date(meta.geladen).toLocaleString("de-DE") : "Es sind die mitgelieferten Daten aktiv";
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    { label: app.name, submenu: [{ role: "about" }, { type: "separator" }, { role: "hide" }, { role: "hideOthers" }, { role: "unhide" }, { type: "separator" }, { role: "quit" }] },
    { label: "Bearbeiten", submenu: [{ role: "undo" }, { role: "redo" }, { type: "separator" }, { role: "cut" }, { role: "copy" }, { role: "paste" }, { role: "selectAll" }] },
    { label: "Daten", submenu: [
      { label: stand, enabled: false },
      { label: "Daten aktualisieren (aus GitHub)", accelerator: "CmdOrCtrl+U", click: async () => { await datenAktualisieren(); menue(); } },
      { label: "GitHub-Token entfernen", click: () => { fs.rmSync(tokenDatei(), { force: true }); } },
      { label: "Auf mitgelieferte Daten zurücksetzen", click: () => { zurueckAufMitgelieferte(); menue(); } },
      { type: "separator" },
      { label: "Repository im Browser öffnen", click: () => shell.openExternal(`https://github.com/${REPO}`) },
    ] },
    { label: "Ansicht", submenu: [{ role: "reload" }, { role: "togglefullscreen" }, { type: "separator" }, { role: "zoomIn" }, { role: "zoomOut" }, { role: "resetZoom" }, { type: "separator" }, { role: "toggleDevTools" }] },
    { label: "Fenster", submenu: [{ role: "minimize" }, { role: "zoom" }, { role: "front" }] },
  ]));
}

function start() {
  fenster = new BrowserWindow({ width: 1500, height: 950, minWidth: 900, minHeight: 600, backgroundColor: "#0b0b0c", title: "Kennzahlen-Terminal",
    webPreferences: { contextIsolation: true, sandbox: true } });
  // Links auf GitHub und Quellen im Standardbrowser öffnen, nie im Terminal-Fenster
  fenster.webContents.setWindowOpenHandler(({ url }) => { if (/^https?:/.test(url)) shell.openExternal(url); return { action: "deny" }; });
  fenster.webContents.on("will-navigate", (e, url) => { if (!url.startsWith("file://")) { e.preventDefault(); if (/^https?:/.test(url)) shell.openExternal(url); } });
  laden();
  menue();
}

app.whenReady().then(() => {
  start();
  app.on("activate", () => { if (!BrowserWindow.getAllWindows().length) start(); });
});
app.on("window-all-closed", () => app.quit());
