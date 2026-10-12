# multicam

A small keyboard-driven TUI for [Omarchy](https://omarchy.org) (Hyprland, Arch Linux) that records
the screen, up to two camera overlays and a chosen microphone into a plain MP4.
Cameras are floating windows (rectangle or circle, optional coloured ring) that you move and
resize with the keyboard. Recording is done by Omarchy's own `omarchy-capture-screenrecording`;
multicam only replaces its `--with-webcam` part. It takes its colours from the active Omarchy theme,
remembers all settings between runs, hides itself while recording and shows a blinking red icon in the bar.

![multicam preview: code editor with a round and a rectangular camera overlay and the multicam TUI](docs/images/overview.svg)

<sub>Illustrations, not screenshots.</sub>

## Requirements

Required: `hyprctl`, `jq`, `mpv`, `pactl`, `gpu-screen-recorder`, `omarchy-capture-screenrecording`,
`omarchy-launch-tui` (all part of a normal Omarchy install).
Optional: `v4l2-ctl` (picks camera resolution), `hyprpicker` (colour picker), `omacut` (open result),
`python3` + `curl` (background-removal add-on).
Nothing is ever installed with root or through the package manager.

## Install

The repository is private; you need `gh`/ssh access to `mattische/multicam`:

```
git clone git@github.com:mattische/multicam.git && cd multicam && ./install.sh
```

Options:

```
./install.sh                  # asks about the optional keybind
./install.sh --yes            # no questions, no keybind
./install.sh --keybind        # also add SUPER + ALT + M to ~/.config/hypr/bindings.lua
./install.sh --no-bgremove    # skip the background-removal add-on (~300 MB)
./install.sh --no-bar-indicator  # skip the bar plugin (blinking red icon while recording)
```
The background-removal add-on (transparent camera background) is installed by default; `--no-bgremove` skips it.
If it cannot be installed (e.g. offline), the installation still completes and the add-on can be installed later, see
[Background-removal add-on](#background-removal-add-on). `--no-keybind` answers "no" without asking. The installer remembers the git revision and the
repository it came from, so the app can find updates (see [Updating](#updating)).

Files created (and nothing else):
`~/.local/bin/multicam`, `~/.local/share/multicam/`, `~/.config/multicam/`,
`~/.local/share/applications/multicam.desktop` and the bar plugin `~/.config/omarchy/plugins/multicam.recording/`
(enabled with `omarchy plugin enable multicam.recording`). The keybind is one line ending in `-- multicam`.
Start it from the app menu ("Multicam"), with the keybind, or run `multicam`
(it opens in a floating terminal when launched through `omarchy-launch-tui --app-id=TUI.float multicam`).

## Uninstall

```
multicam uninstall      # or ./uninstall.sh ; asks first, --yes skips the question
```
Removes everything above, the keybind line, the bar plugin and the add-on. Your recordings are never touched.

## Updating

```
multicam update         # compares with origin/main, asks, then installs the new version [--yes]
multicam check-update   # exit 0 if an update is available (for scripts)
```
At startup the app checks in the background (`git ls-remote`, nothing else is sent) whether `origin/main` is newer than
the installed revision. If so the form shows a green line and you can press `U` to update, or ignore it. `U` also
checks on demand. The update clones the repository into a temporary folder and runs its `install.sh --yes`;
your settings, the keybind, the bar plugin and the add-on are kept (an update never re-adds what you removed). After updating, restart multicam.
Turn the startup check off with `UPDATE_CHECK=off` in `~/.config/multicam/config` or `MULTICAM_NO_UPDATE_CHECK=1`.
The update source is the `origin` URL of the clone you installed from (a private repo needs working git credentials).

## Usage

![The multicam form](docs/images/form.svg)

1. Form: choose camera A / B (each "off" or a device; the same device cannot be used twice), shape, ring,
   ring colour and thickness, microphone, desktop audio and screen. Press `F5` (or Enter on the last row).
2. Preview: the cameras appear and are placed, nothing is recorded yet. Arrange them, then press `Enter` to start recording.
3. Recording: multicam's window disappears (it moves to a hidden workspace, `special:multicam`) so it is not in the
   recording, and a blinking red record icon with the elapsed time appears in the bar. The camera windows stay.
4. Stop: click the red icon in the bar, press the keybind (`SUPER + ALT + M`) again, run `multicam stop`, or use
   Omarchy's own stop (Alt+Print). multicam comes back on the workspace you are on, shows the file name and (by
   default) offers to open it in omacut.

![While recording: multicam is hidden, the bar shows a blinking red icon](docs/images/recording.svg)

The result is `~/Videos/screenrecording-YYYY-MM-DD-HH_MM_SS.mp4` (h264 + AAC). Omarchy first writes
`screenrecording-YYYY-MM-DD_HH-MM-SS.mp4`; multicam renames it once Omarchy's post-processing is done
(`-2`, `-3`, ... on name collision). Choose another folder in the settings (`S`), or set `MULTICAM_OUTPUT_DIR`.
The selected microphone is set as default source only while recording and always restored afterwards.
"Screen" defaults to the focused monitor.

### Settings view

![The settings view](docs/images/settings.svg)

Press `S` in the form. Every change is saved at once to `~/.config/multicam/config`; `Esc` goes back.

| Setting | Values (default first) |
|---|---|
| Save recordings to | Omarchy's folder (`~/Videos`) or any folder you type (Enter edits, empty = default; created when needed) |
| After recording | ask to open in omacut, open in omacut, just show the file |
| Hide while recording | on, off |
| Bar indicator | on, off (the plugin stays installed; off means multicam does not show the icon) |
| Arrow step | 20 px (5-100) |
| Shift + arrow step | 100 px (25-400) |
| Check for updates | on, off |

### Settings are remembered

Everything you set is written to `~/.config/multicam/config` as soon as it changes (and again on exit), so the next
start opens with the same cameras, shapes, ring colours and thickness, background removal, microphone, desktop audio,
capture mode and screen. Camera positions and sizes are remembered separately for full screen and for area/window
recording (the latter relative to the area). In area mode the last area is remembered too: the form then shows an
`Area` row where you choose `last: WxH @ X,Y` (reused at `F5` without the picker, as long as it is on a connected screen)
or `pick a new one`. `o` in the preview always opens the picker. Saved devices that are not connected are shown as
missing and kept, never silently replaced.

### Look

The TUI follows the active Omarchy theme: accent, selection and text colours are read from
`~/.local/state/omarchy/current/theme/colors.toml` when it starts (without it, the terminal palette is used, which
Omarchy also themes). `NO_COLOR=1` turns colours off. The icon in the header needs a Nerd Font (Omarchy's default).

### What to record: full screen, area or window

The form row `Record` selects `full screen` (default), `area` (free rectangle) or
`window`. When you press `F5` in area/window mode, multicam first runs Omarchy's own picker
(`omarchy-capture-region region` / `windows`): drag a rectangle with the mouse, or for windows use
Tab / arrow keys and Enter (Esc cancels and returns to the form with a message; nothing is started).
The picked rectangle becomes the camera bounds, so cameras, snapping (1-9) and clamping always stay
inside the recorded area. The preview header shows `Area WxH @ X,Y` / `Window: class - title`.
Press `o` in the preview to pick again (cameras are re-clamped). The `Screen` row only applies to full screen.

How it works: the recording is still started by `omarchy-capture-screenrecording` (without `--fullscreen`);
multicam puts a tiny shim `omarchy-capture-region` first in `PATH` for that single start call, which answers with
the stored rectangle, so Omarchy records `-w region:WxH+X+Y` and does its normal finalize/stop. The shim is removed
right after start. The video has the physical size of the area (logical size x monitor scale, e.g. 1200x800 on
a 1.6 scale monitor gives 1920x1280).

Limitations: a window is recorded as the rectangle it had at start; if you move the window the recording does
not follow. Free-drag area selection needs the mouse (like the colour picker); window selection works with the keyboard.

### Keys

![Move mode, size mode and numpad snapping](docs/images/controls.svg)

Form screen

| Key | Action |
|---|---|
| ↑ ↓ (k j) | previous / next row |
| ← → (h l), Enter | change value / toggle |
| `C` (or Enter on the colour row) | type a hex colour |
| `c` | colour picker (`hyprpicker`, needs a mouse click) |
| ← → on the colour row | cycle the 8 preset colours |
| `F5` | preview cameras |
| `S` | settings view |
| `U` | check for / install an update |
| ←/→ or Enter on `Area` | reuse the last area / pick a new one (area mode) |
| Enter on `Remove background` | install the background-removal add-on (when not installed) |
| `q`, `Esc` | quit |

Preview / recording screen

| Key | Action |
|---|---|
| `Tab` | select camera A / B |
| ↑ ↓ ← → | move 20 px (`[MOVE]`, set in settings) or grow/shrink ±10 % (`[SIZE]`: ↑ → bigger, ↓ ← smaller) |
| Shift + arrows | move 100 px (settings), or ±25 % in size mode |
| `m` | toggle move / size mode (shown in the status line) |
| `o` | pick the area / window again (area and window modes, not while recording) |
| `+` `-` / `PgUp` `PgDn` | size ±10 % around the centre (both modes) |
| `1`-`9` | snap to corner / edge / centre (numpad layout) |
| `s` | circle / rectangle |
| `r` | ring on / off |
| `p` / `P` | next / previous preset ring colour |
| `c` / `C` | colour picker / hex input |
| `[` `]` | ring thickness 1-12 px (default 4) |
| `b` | background removal on / off (add-on) |
| `Enter` | start recording (from preview; F5 does not start it); multicam then hides until the recording stops |
| `q`, `Esc` | quit the preview (while recording, if the window is shown: stop, asks first) |

Deviation from the spec: the spec uses ← / → for the preset colours, but on the recording screen the
arrows move/resize. There the presets are on `p` / `P`; on the form screen ← / → work as specified.

Sizes: a circle is a square of the given size; a rectangle is 16:9 where the size is the height. Minimum
120 px, maximum the screen height. Cameras are always kept inside the screen.

Runtime files (PIDs, FIFOs, state) live in `$XDG_RUNTIME_DIR/multicam/` and vanish on logout.
Camera windows use 1280x720 (MJPEG when the device supports it at 30 fps), or 640x360/640x480 as fallback;
with background removal 640x360 is preferred to save CPU. Note that webcams with dynamic frame rate drop
to 15 fps in dim light regardless of format.

Cleanup: closing the terminal, Ctrl+C, `q`, stopping from outside (Alt+Print, click on the bar icon,
`omarchy-capture-screenrecording --stop-recording`) or killing `gpu-screen-recorder` all close the camera
windows, disable window rules and restore the microphone (a small watcher process handles the outside cases).
multicam only touches windows with class `MulticamA` / `MulticamB` and processes it started itself.

## Background-removal add-on

```
./install.sh                   # installed by default (skip with --no-bgremove) ...
multicam install-bgremove      # ... or any time later (also: select the "Remove background" row in the form and press Enter)
                               # ~300 MB Python venv + 14 MB model, all in ~/.local/share/multicam/bg/
multicam uninstall-bgremove    # removes that one folder
multicam check-bgremove        # verifies the model's SHA256
```
Camera -> ONNX Robust Video Matting (mobilenetv3) -> RGBA -> `mpv` with transparent background, 2 CPU
threads. The model (GPL-3.0, <https://github.com/PeterL1n/RobustVideoMatting>) is downloaded from the
project's release and checked against a fixed SHA256; on mismatch it is deleted and installation stops.
Quality: soft edges, dark clothes can become partly transparent (expected, not a bug). The per-camera
option appears in the form once the add-on is installed (until then the form shows an install row). Toggling it while running restarts that
camera window briefly.

## Known limitations

- Hyprland 0.56.2 with Lua config: only Lua dispatches are used; the window rule `rounding` is capped at 20,
  so circles are made with `set_prop rounding = size/2` after the window is mapped. Rounding cannot be read back.
- Omarchy's own stop (its bar icon / Alt+Print) only knows about `WebcamOverlay`; multicam's watcher
  cleans up the rest within about a second. Omarchy's stop also refuses to run when its `~/Videos` folder is
  missing; `multicam stop` and multicam's bar icon do not have that problem.
- While recording, multicam's window waits on the hidden workspace `special:multicam`; showing that workspace by
  hand would put it in the recording.
- Omarchy's "recording saved" notification points to the original file name, which multicam renames.
- A recording managed by Omarchy and one by multicam cannot run at the same time (multicam refuses to start).
- `--fullscreen` records the focused monitor; choosing another screen briefly focuses it when recording starts.
- `hyprpicker` needs a mouse click (keyboard alternatives: hex code, preset colours).
- A camera device can be opened by one process only; the same device cannot be used for both cameras.
- Screens that are blanked or locked deliver no frames: the recording then contains the lock screen.
- Tested on foot-based Omarchy only; the TUI needs about 100x30 terminal cells.

## Tests

`tests/run.py [T-ID ...]` runs the automatic tests (pty driving, `hyprctl clients -j`, `ffprobe`); results and
evidence are summarised in `docs/TEST-REPORT.md`. Tests record into a scratch directory via `MULTICAM_OUTPUT_DIR`
and run with no update check. Install tests use `--no-bgremove --no-bar-indicator` so they never download the
add-on or touch the running Omarchy shell. A quick subset after UI changes:
`tests/run.py T-L1 T-S1 T-H1 T-B2 T-B4 T-B5 T-B6c T-B6d T-B7` (about 2 minutes).
Devices are autodetected (first two cameras, first two non-monitor microphones); override with `MC_CAM_A_DEV`,
`MC_CAM_A_NAME`, `MC_CAM_B_DEV`, `MC_CAM_B_NAME`, `MC_MIC`, `MC_MIC2` (T-C3v needs two mics), `MC_SCRATCH`.
