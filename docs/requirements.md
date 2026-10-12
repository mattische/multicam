# multicam – requirements specification (v1, draft)

Status: proposal, nothing is built yet. Basis: tests on the user's computer (Omarchy, Hyprland 0.56.2, quickshell bar).
Every requirement has an ID. Every requirement has a test (T-ID) that can be run and reported as PASS / FAIL.

## 1. Purpose
A small add-on for Omarchy that records the screen + up to two cameras + a chosen microphone to a regular MP4 file,
with the cameras as floating images (rectangle or circle) that can be moved and scaled with the keyboard.
Builds on `omarchy-capture-screenrecording` (replaces only `...-with-webcam`). Changes nothing in /usr or in Omarchy's files.

## 2. Requirements

### A. Installation and removal
- A1. Installation with one command: `./install.sh`. No root privileges. No packages are installed (it only checks dependencies and says what is missing).
- A2. Everything installed lives in known places: `~/.local/bin/multicam`, `~/.local/share/multicam/`, `~/.config/multicam/`, `~/.local/share/applications/multicam.desktop`. Nothing else.
- A3. Removal with one command: `multicam uninstall` (or `./uninstall.sh`). Removes everything in A2 after confirmation. Recordings in Videos are never touched.
- A4. An optional keybind is added only if the user chooses it, in `~/.config/hypr/` via a clearly marked line that uninstall removes.
- A5. No systemd service, no changes to `shell.json`, no changes to Omarchy's files.
- A6. Background removal (see F) is installed separately with `multicam install-bgremove` and removed with `multicam uninstall-bgremove` (one folder).

### B. Start and use
- B1. Start from the app menu ("Multicam") or `multicam`. Opens as a TUI in a floating terminal window (`omarchy-launch-tui`).
- B2. The TUI can be controlled entirely with the keyboard. No function requires a mouse.
- B3. Form: camera A, camera B (each "off" or a device; the same device cannot be chosen twice), microphone (list or "none"), desktop audio on/off, shape (rectangle/circle) per camera, ring on/off, background removal on/off per camera (if the add-on is installed), screen to record (the focused one by default).
- B4. The latest choices are saved in `~/.config/multicam/config` and prefilled next time.
- B6. What is recorded: the form row `Record` chooses `full screen`, `area` or `window` (saved as CAPTURE). In area/window mode Omarchy's picker (`omarchy-capture-region region|windows`) runs when the preview starts; if the selection is cancelled the user goes back to the form without anything starting. The selected rectangle becomes the cameras' bounds (the cameras are kept within the recorded area) and is recorded via Omarchy's own recording script. Key `o` picks again. A window is recorded as the rectangle it had at the start.
- B5. Camera and microphone lists are read at start. If a saved device is missing it is clearly marked and never silently replaced.

### C. Recording
- C1. The cameras are started before the recording and are present from the first frame.
- C2. The recording is started with `omarchy-capture-screenrecording --fullscreen` (plus `--with-microphone-audio`, `--with-desktop-audio` as chosen). No `--with-webcam`.
- C3. The chosen microphone is set as the system's default microphone before the start. The original value is always restored at the end, on crash and on abort.
- C4. The result is an MP4 (h264 + AAC) in `~/Videos`. File name: `screenrecording-YYYY-MM-DD-HH_MM_SS.mp4` (example `screenrecording-2026-10-11-15_01_17.mp4`). Omarchy writes its own name (`YYYY-MM-DD_HH-MM-SS`); multicam renames the file only once Omarchy's post-processing (trimming, loudness normalisation, preview image) is done. The rename must not collide with an existing file (on collision `-2` is appended). Omarchy's preview image (`-preview.png`) is left as it is.
- C5. After recording the file name is shown, and the user is offered to open it in **omacut** (preinstalled video editor).

### D. Camera images (during recording and preview)
- D1. The shape is rectangle or circle, selectable per camera. Circle = square image (1:1 crop) + Hyprland rounding = half the side, reapplied after every resize.
- D2. Optional border around the camera, following the shape (circle/rectangle). The colour is chosen per camera in three ways: `c` starts `hyprpicker` (click any pixel on the screen), `C` lets the user type a hex code (`#rrggbb`), and a row of eight preset colours is cycled with ←/→. Thickness 1–12 px with `[` and `]` (default 4). Colour and thickness are saved per camera in the configuration. The border is Hyprland's window border (`set_prop border_size` / `inactive_border_color`), drawn inside the window, and does not change the image size.
- D3. Size is changed with `+`/`-` and PgUp/PgDn (±10 % around the centre) in both modes, and with the arrow keys in size mode (see D4). At least 120 px, at most the screen height.
- D4. The arrow keys have two modes toggled with `m`. Move mode (default): an arrow moves the selected camera 20 px, Shift+arrow 100 px. Size mode: ↑/→ larger and ↓/← smaller (±10 %, Shift ±25 %), around the image centre. The current mode is always shown in the status line as `[MOVE]` or `[SIZE]`. The image is always kept within the screen.
- D5. Tab switches the selected camera. The digit keys 1–9 snap to corner/edge/centre (numpad layout).
- D6. `s` toggles circle/rectangle, `r` border on/off, `c`/`C` border colour, `[`/`]` border thickness, `m` move/size, `b` background removal on/off.
- D7. The windows open floating, pinned, without border, without focus (the TUI keeps keyboard focus).
- D8. The camera windows have their own class (`MulticamA`, `MulticamB`) and are not affected by Omarchy's WebcamOverlay rules.

### E. Quitting
- E1. `q` or Esc in the TUI quits: stops the recording if it is running (after confirmation), closes the camera windows, removes the window rules, restores the microphone.
- E2. The same cleanup on Ctrl+C, on a closed terminal window and when the recording is stopped from outside (Alt+Print or a click in the bar).
- E3. The icon in the middle of the bar: multicam uses Omarchy's existing recording icon (dot in a circle to the left of the clock). It is shown automatically because `gpu-screen-recorder` is running, and a click stops the recording. Multicam calls `omarchy-shell -q omarchy.indicators refresh` at start and stop. No plugin of its own and no change to `shell.json`.
- E4. A background watcher (started only once the recorder is confirmed running) cleans up everything when `gpu-screen-recorder` disappears.
- E5. Multicam closes only its own windows and processes (via class and saved PIDs), never with `pkill mpv`.

### F. Background removal (optional add-on)
- F1. One option per camera in the TUI. Shown only if the add-on is installed.
- F2. Pipeline: camera → ONNX model (Robust Video Matting mobilenetv3) → RGBA → `mpv` with a transparent background. Target ≥ 25 fps on one core (1–2 threads).
- F3. Installed in its own Python environment under `~/.local/share/multicam/bg/`. The model is downloaded from the project's official release and verified with a fixed SHA256 (88d45312…2828).
- F4. Known quality: soft edges, dark clothing partly transparent. Documented in the help text (not a bug).
- F5. A licence notice (GPL-3.0 for RVM) is shown during installation.

### G. Non-requirements
- Scene switching during recording, more than two cameras, mouse control, a clip editor of its own, an audio mixer.

## 3. Tests (to be run and reported)
All test runs must clean up after themselves. Tests marked (M) require the user to look/click.

| ID | Requirement | Test | Expected |
|---|---|---|---|
| T-A1 | A1,A2 | Run install.sh as a clean user (or with an empty HOME copy) | Only the files in A2 are created; `diff` before/after confirms |
| T-A3 | A3 | uninstall.sh afterwards | All files gone, Videos untouched, `diff` against the before state empty |
| T-A5 | A5 | `diff -r` of `~/.config/omarchy`, `/usr`, `~/.local/share/omarchy` before/after install | No difference |
| T-A6 | A6 | install-bgremove, then uninstall-bgremove | One folder created/removed |
| T-B2 | B2 | Drive the whole TUI with `wtype`/pty without a mouse | All options reachable and changeable |
| T-B4 | B4 | Change options, quit, restart | Options prefilled |
| T-B6a | B6 | Area mode (picker replaced by a stub returning a fixed rectangle): preview, record 4 s | Cameras inside the rectangle (also after snap/grow), MP4 size = rectangle x screen scale, camera image visible in a frame |
| T-B6b | B6 | Window mode (stub returns a window's rectangle) | Header "Window: class", picker called with `windows`, MP4 = window size x scale |
| T-B6c | B6 | The picker is cancelled (exit 1) | Message, form still shown, no camera windows, no recording |
| T-B5 | B5 | Set the saved camera to a nonexistent device | Clear warning, no silent replacement |
| T-C1 | C1 | Record 8 s, extract a frame at 0.2 s | Cameras visible already in the first frames |
| T-C3 | C3 | Choose another mic, record, check `pactl get-default-source` before/during/after | Restored; volume measurement (ffmpeg) shows the chosen source |
| T-C4 | C4 | `ffprobe` on the result | MP4, h264 + AAC, duration ±0.5 s |
| T-C5 | C5 | Choose "open in omacut" | omacut starts with the file (M) |
| T-D1 | D1,D2 | Screenshot in circle, rectangle, with/without ring (grim, Read) | Round/square/ring as expected; the same in a recorded frame |
| T-D3/4 | D3,D4 | Key sequences via pty; read `hyprctl clients -j`; test both modes (`m`) | Geometry as per table (±1 px), clamped to the screen edge; the status line shows the right mode |
| T-D2 | D2 | Set the colour via hex code, via the colour row and via `hyprpicker`; screenshot (grim, Read); change thickness; restart | The border has the chosen colour and thickness, follows circle and rectangle, the values are saved per camera |
| T-C4b | C4 | Record; check the file name with the regex `^screenrecording-[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}_[0-9]{2}_[0-9]{2}\.mp4$`; check that Omarchy's name is gone; create a collision | Correct name in ~/Videos, no duplicate, collision gets `-2` |
| T-D5 | D5 | Tab + 1–9 | Right camera, right position |
| T-D7 | D7 | `hyprctl activewindow` after every action | Focus stays on the TUI |
| T-D8 | D8 | Start Omarchy's WebcamOverlay in parallel | No interference either way |
| T-E1 | E1 | q, Esc | No Multicam windows/rules/mpv processes left; mic restored |
| T-E2 | E2 | Ctrl+C, close the terminal, `--stop-recording` from outside | Same cleanup result within 1 s |
| T-E3 | E3 | Screenshot of the bar during recording; run the click command | Icon visible; stops; icon gone (M for a real mouse click) |
| T-E4 | E4 | Kill the recorder with SIGTERM | The watcher cleans up |
| T-E5 | E5 | Start another `mpv` beforehand | It is not affected |
| T-F2 | F2 | Measure fps and CPU for 15 s; screenshot | ≥ 25 fps, transparent background (desktop visible) |
| T-F3 | F3 | Modify the model file, run the installation's check | SHA256 error stops it |
| T-X1 | all | Two cameras + circle + mic + 30 s recording | Stable, no dropped frames, file playable |
| T-X2 | all | Run the whole flow twice in a row | No leftovers from the first run |

## 4. Known limitations (from the tests)
- Hyprland 0.56.2: only Lua dispatch works (`hl.dsp.window.*`); the old `movewindowpixel` does not.
- The window rule `rounding` is capped at 20, so the circle is set with `set_prop` after the window has opened.
- Rounding cannot be read back; the circle is verified with a screenshot.
- Omarchy's stop (click/Alt+Print) closes only `WebcamOverlay`; the rest is cleaned up by multicam's watcher.
- An Omarchy-managed recording and multicam cannot run at the same time.
- `hyprpicker` requires a mouse click; the keyboard alternatives are the hex code and the colour row.
- Background removal: ~300 MB Python environment (can be reduced), GPL-3.0 model, soft edges.
- Not verified yet: a real mouse click on the bar icon, terminals other than foot, the combination circle + background removal, two real cameras at the same time with background removal.

## 5. Delivery order
1. `multicam` with cameras, shape, ring, keyboard control, mic, recording, cleanup (tests A–E).
2. install/uninstall + .desktop + optional keybind.
3. Background removal as an add-on (F).
4. Private GitHub repo.
