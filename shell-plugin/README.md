# multicam bar indicator for Omarchy

An Omarchy shell (Quickshell) bar widget for [multicam](https://github.com/mattische/multicam), the keyboard-driven
recorder for screen + up to two camera overlays + microphone.

- **Recording:** a red record icon (󰑋) blinks in the bar and shows the elapsed time. Click it to stop the recording
  (`multicam stop`); multicam then finishes the file and comes back.
- **Idle:** by default nothing is shown. Optionally the widget shows a small record icon whose click opens multicam
  in a floating terminal (`omarchy-launch-tui --app-id=TUI.float multicam`), see
  [Idle launcher icon](#idle-launcher-icon).

## Requirements

- Omarchy with Quickshell plugin support (`omarchy plugin` commands).
- **The multicam app.** This plugin is only the bar indicator; it does not record anything itself. Install multicam
  first, either from the AUR:

  ```bash
  yay -S multicam
  ```

  or per user with its install script (no root):

  ```bash
  curl -fsSL https://raw.githubusercontent.com/mattische/multicam/main/install.sh | bash
  ```

  The plugin finds `multicam` on the login `PATH` or in `~/.local/bin`. When it is missing, the idle icon (if
  enabled) is dimmed and a click opens the multicam page.

## Install

multicam installs this plugin itself: `install.sh` does it, and the AUR package does it at the first start of
multicam. By hand, with the multicam app installed:

```bash
multicam setup-bar            # copy into ~/.config/omarchy/plugins/io.github.mattische.multicam and enable
multicam setup-bar --remove   # disable and remove it (multicam will not add it again)
```

or from its own repository (git-managed, updated with `omarchy plugin update`):

```bash
omarchy plugin add https://github.com/mattische/omarchy-multicam-plugin.git --enable
```

Bar widgets land in the right section by default; move it with
`omarchy bar move io.github.mattische.multicam --section left|center|right`.

## Idle launcher icon

Off by default, so the widget only appears while recording. To keep a record icon in the bar that opens multicam:

```bash
omarchy bar set io.github.mattische.multicam showWhenIdle true --json
```

Turn it off again with `... showWhenIdle false --json`. The setting is stored inline on the widget's entry in
`~/.config/omarchy/shell.json`.

## Update and remove

```bash
omarchy plugin update io.github.mattische.multicam   # only for a git-managed copy (omarchy plugin add)
omarchy plugin remove io.github.mattische.multicam
```

A copy installed by `multicam setup-bar` is refreshed by multicam itself (on `multicam update`, or at start for the
AUR package).

## How it works

While multicam records it writes the start time (epoch seconds) to `$XDG_RUNTIME_DIR/multicam/recording` and
removes the file afterwards. The widget re-reads that tiny file twice a second; it runs nothing in the background
except a check every five minutes for whether the `multicam` command exists. The indicator can also be switched
off from multicam's own settings view (`S` -> Bar indicator): multicam then does not write the file and the widget
stays in its idle state.

Older multicam versions installed a separate indicator with the id `multicam.recording`. `multicam setup-bar`
disables and removes it automatically; by hand:

```bash
omarchy plugin remove multicam.recording
```

## Development

The source of truth is `shell-plugin/` in the multicam repository; `packaging/omarchy-plugin/` there is an identical
copy that is published as the plugin repository.

```bash
omarchy plugin validate .
/usr/lib/qt6/bin/qmllint -I "$OMARCHY_PATH/shell" BarWidget.qml
```

qmllint cannot resolve the shell's `qs.*` modules outside the running shell, so it reports import and
"inheritance cycle" warnings for `BarWidget.qml` (the file has the same name as its base type `qs.Ui.BarWidget`,
as in Omarchy's own plugin tutorial); it exits 0. Runtime errors show up in
`qs log -p "$OMARCHY_PATH/shell" --tail 100`.

## License

MIT, see [LICENSE](LICENSE).
