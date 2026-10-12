import QtQuick
import Quickshell
import Quickshell.Io
import qs.Ui

// Shown only while multicam records: a blinking red record icon and the elapsed time.
// multicam writes the start time (epoch seconds) to $XDG_RUNTIME_DIR/multicam/recording
// while recording and removes it afterwards. Click stops the recording.
BarWidget {
  id: root
  moduleName: "multicam.recording"

  readonly property string stateFile: Quickshell.env("XDG_RUNTIME_DIR") + "/multicam/recording"
  property bool recording: false
  property real startedAt: 0
  property real now: Date.now() / 1000
  property bool blinkOn: true
  readonly property string elapsed: {
    var s = Math.max(0, Math.floor(now - startedAt))
    var m = Math.floor(s / 60)
    return (m < 10 ? "0" : "") + m + ":" + (s % 60 < 10 ? "0" : "") + (s % 60)
  }

  visible: recording
  implicitWidth: recording ? button.implicitWidth : 0
  implicitHeight: button.implicitHeight

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

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: "󰑋 " + root.elapsed
    foreground: root.blinkOn ? "#ff3b3b" : "#5a1414"
    useActiveColor: false
    tooltipText: "multicam is recording - click to stop"
    onPressed: function(b) {
      // multicam stop works even when Omarchy's default ~/Videos folder does not exist
      if (root.bar) root.bar.run(Quickshell.env("HOME") + "/.local/bin/multicam stop")
    }
  }
}
