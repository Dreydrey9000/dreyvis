// Dreyvis desktop app: its own window, a menu-bar switch, and a talk hotkey.
// The brain, voice and ears run in the Dreyvis server (launchd job com.drey.dreyvis);
// this app turns that service on and off and shows the orb.
const { app, BrowserWindow, Tray, Menu, globalShortcut, session, systemPreferences, nativeImage, shell, ipcMain } = require("electron");
const { execFile } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");

app.setName("Dreyvis");
const URL = "http://127.0.0.1:8340/";
const LABEL = "com.drey.dreyvis";
const PLIST = path.join(app.getPath("home"), "Library/LaunchAgents", LABEL + ".plist");
const UID = process.getuid();
const TALK_KEY = "Alt+Space";

let win = null;
let tray = null;
let muted = false;
let serverOn = false;

if (!app.requestSingleInstanceLock()) app.quit();
app.on("second-instance", () => showWindow());

function launchctl(args) {
  return new Promise((resolve) => execFile("/bin/launchctl", args, (err, out) => resolve({ ok: !err, out: String(out || "") })));
}

async function isServerUp() {
  try {
    const r = await fetch(URL + "api/health", { signal: AbortSignal.timeout(1500) });
    return r.ok;
  } catch {
    return false;
  }
}

async function setServer(on) {
  if (on) {
    await launchctl(["enable", `gui/${UID}/${LABEL}`]);
    await launchctl(["bootstrap", `gui/${UID}`, PLIST]);       // errors harmlessly if already loaded
    await launchctl(["kickstart", `gui/${UID}/${LABEL}`]);
  } else {
    await launchctl(["bootout", `gui/${UID}/${LABEL}`]);
    await launchctl(["disable", `gui/${UID}/${LABEL}`]);       // stays off after a restart too
  }
  serverOn = on;
  if (on) await waitForServer();
  if (win) on ? win.loadURL(URL) : win.loadFile(path.join(__dirname, "off.html"));
  refreshTray();
}

async function waitForServer() {
  for (let i = 0; i < 60; i++) {
    if (await isServerUp()) return true;
    await new Promise((r) => setTimeout(r, 1000));
  }
  return false;
}

function setMuted(value) {
  muted = value;
  if (win) win.webContents.send("dreyvis:muted", muted);
  refreshTray();
}

function refreshTray() {
  if (!tray) return;
  tray.setTitle(!serverOn ? " Dreyvis off" : muted ? " Dreyvis muted" : " Dreyvis");
  tray.setToolTip("Dreyvis");
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: "Open Dreyvis", click: showWindow },
    { type: "separator" },
    { label: serverOn ? "Dreyvis is on" : "Dreyvis is off", enabled: false },
    { label: serverOn ? "Turn off" : "Turn on", click: () => setServer(!serverOn) },
    { type: "separator" },
    { label: muted ? "Unmute mic" : "Mute mic", accelerator: TALK_KEY, enabled: serverOn, click: () => setMuted(!muted) },
    { label: "Open dashboard", enabled: serverOn, click: () => showPage("dashboard") },
    { type: "separator" },
    { label: "Open app at login", type: "checkbox", checked: app.getLoginItemSettings().openAtLogin,
      click: (item) => app.setLoginItemSettings({ openAtLogin: item.checked }) },
    { label: "Quit Dreyvis app", click: () => app.quit() },
  ]));
}

// The orb ("") and Ethan's dashboard ("dashboard": runs, sessions, memory, specs, projects, usage)
// both open inside the Dreyvis window.
function showPage(page) {
  showWindow();
  if (serverOn) win.loadURL(URL + page);
}

function buildAppMenu() {
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    { role: "appMenu" },
    { role: "editMenu" },
    { label: "View", submenu: [
      { label: "Orb", accelerator: "CmdOrCtrl+1", click: () => showPage("") },
      { label: "Dashboard", accelerator: "CmdOrCtrl+2", click: () => showPage("dashboard") },
      { type: "separator" },
      { role: "reload" },
      { role: "togglefullscreen" },
    ] },
    { role: "windowMenu" },
  ]));
}

function showWindow() {
  if (!win) createWindow();
  win.show();
  win.focus();
}

function createWindow() {
  win = new BrowserWindow({
    width: 560,
    height: 760,
    title: "Dreyvis",
    backgroundColor: "#050508",
    titleBarStyle: "hiddenInset",
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: false,          // the ears replace window.SpeechRecognition in the page itself
      nodeIntegration: false,
      sandbox: false,
      autoplayPolicy: "no-user-gesture-required",
    },
  });
  win.on("page-title-updated", (e) => e.preventDefault());
  win.on("close", (e) => {                // closing the window keeps Dreyvis in the menu bar
    if (!app.isQuitting) { e.preventDefault(); win.hide(); }
  });
  win.webContents.on("did-finish-load", () => win.webContents.send("dreyvis:muted", muted));
  win.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: "deny" }; });
  win.webContents.on("will-navigate", (e, url) => {
    if (!url.startsWith(URL) && !url.startsWith("file://")) { e.preventDefault(); shell.openExternal(url); }
  });
  serverOn ? win.loadURL(URL) : win.loadFile(path.join(__dirname, "off.html"));
  win.once("ready-to-show", () => win.show());
}

app.on("before-quit", () => { app.isQuitting = true; });
app.on("activate", showWindow);
app.on("window-all-closed", (e) => e.preventDefault());
app.on("will-quit", () => globalShortcut.unregisterAll());

app.whenReady().then(async () => {
  // Only Dreyvis's own page gets the mic.
  session.defaultSession.setPermissionRequestHandler((wc, permission, cb) =>
    cb(permission === "media" && wc.getURL().startsWith(URL)));
  session.defaultSession.setPermissionCheckHandler((wc, permission, origin) =>
    permission === "media" && String(origin).startsWith(URL.slice(0, -1)));
  await systemPreferences.askForMediaAccess("microphone");

  buildAppMenu();
  ipcMain.on("dreyvis:show", (_e, page) => showPage(page === "dashboard" ? "dashboard" : ""));
  const icon = path.join(__dirname, "trayTemplate.png");
  tray = new Tray(fs.existsSync(icon) ? nativeImage.createFromPath(icon) : nativeImage.createEmpty());
  serverOn = await isServerUp();
  refreshTray();
  globalShortcut.register(TALK_KEY, () => setMuted(!muted));
  if (!serverOn) await setServer(true);
  showWindow();
});
