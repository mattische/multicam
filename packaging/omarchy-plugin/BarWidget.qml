import QtQuick
import Quickshell
import Quickshell.Io
import qs.Ui

// multicam bar button.
//   Idle:      hidden by default; with the setting showWhenIdle=true a small record icon whose click
//              opens the multicam TUI in a floating terminal.
//   Recording: a blinking red record icon with the elapsed time; click stops the recording.
// multicam writes the start time (epoch seconds) to $XDG_RUNTIME_DIR/multicam/recording while it
// records and removes the file afterwards; this widget only reads that file.
// The multicam app itself is not part of this plugin (install it from the AUR or with its install.sh).
BarWidget {
  id: root
  moduleName: "io.github.mattische.multicam"

  readonly property string stateFile: Quickshell.env("XDG_RUNTIME_DIR") + "/multicam/recording"
  // off by default: the widget only appears while recording (accepts true or "true")
  readonly property bool showWhenIdle: String(setting("showWhenIdle", false)) === "true"
  // bash -lc (bar.run) gives a login PATH; ~/.local/bin is appended for per-user installs of multicam
  readonly property string cmdPrefix: "PATH=\"$PATH:$HOME/.local/bin\" "
  property bool installed: true
  property bool recording: false
  property real startedAt: 0
  property real now: Date.now() / 1000
  property bool blinkOn: true
  readonly property string elapsed: {
    var s = Math.max(0, Math.floor(now - startedAt))
    var m = Math.floor(s / 60)
    return (m < 10 ? "0" : "") + m + ":" + (s % 60 < 10 ? "0" : "") + (s % 60)
  }

  visible: recording || showWhenIdle
  implicitWidth: recording ? recButton.implicitWidth : (showWhenIdle ? idleButton.implicitWidth : 0)
  implicitHeight: recording ? recButton.implicitHeight : idleButton.implicitHeight

  function openApp() {
    if (!root.bar) return
    if (root.installed)
      root.bar.run(root.cmdPrefix + "omarchy-launch-tui --app-id=TUI.float multicam")
    else
      root.bar.run("xdg-open https://github.com/mattische/multicam")
  }

  function stopRecording() {
    if (root.bar) root.bar.run(root.cmdPrefix + "multicam stop")
  }

  FileView {
    id: state
    path: root.stateFile
    printErrors: false
    onLoaded: {
      var t = parseFloat(String(state.text()).trim())
      root.startedAt = isNaN(t) ? root.now : t
      root.recording = true
    }
    onLoadFailed: root.recording = false
  }

  // Is the multicam command available? Checked at start and every few minutes.
  Process {
    id: installedProc
    command: ["bash", "-lc", "PATH=\"$PATH:$HOME/.local/bin\" command -v multicam >/dev/null"]
    onExited: function(exitCode) { root.installed = exitCode === 0 }
  }

  Timer {
    interval: 300000
    running: true
    repeat: true
    triggeredOnStart: true
    onTriggered: if (!installedProc.running) installedProc.running = true
  }

  Timer {   // the file is tiny: re-read it every half second (also notices removal)
    interval: 500
    running: true
    repeat: true
    onTriggered: {
      state.reload()
      root.now = Date.now() / 1000
      root.blinkOn = root.recording ? !root.blinkOn : true
    }
  }

  BarIconButton {
    id: idleButton
    anchors.fill: parent
    visible: !root.recording && root.showWhenIdle
    bar: root.bar
    text: "󰑋"
    dimmed: !root.installed
    tooltipText: root.installed ? "multicam - record screen and cameras" : "multicam is not installed - click for instructions"
    onPressed: function(b) { root.openApp() }
  }

  WidgetButton {
    id: recButton
    anchors.fill: parent
    visible: root.recording
    bar: root.bar
    text: "󰑋 " + root.elapsed
    foreground: root.blinkOn ? "#ff3b3b" : "#5a1414"
    useActiveColor: false
    tooltipText: "multicam is recording - click to stop"
    onPressed: function(b) { root.stopRecording() }
  }
}
