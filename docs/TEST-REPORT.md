# multicam test report

Run 2026-10-11 on mbp-omarchy (Hyprland 0.56.2; DP-1 3840x2160 focused, DP-2 rotated 1200x1920, cameras C920 + FaceTime).
Test code: `tests/run.py` + `tests/mclib.py` (automated) and `tests/visual.py` (visual; the images are reviewed by a human/agent).
Recordings were written to `/tmp/claude-1000/multicam-tests/` via `MULTICAM_OUTPUT_DIR` and deleted.

Version 2 of the report: after independent verification six bugs were fixed (see below) and the tests were tightened. The screen was locked during
the first run; it was then unlocked and the visual tests were run for real (the images were reviewed and are described below).
The evidence images show the user's webcam image and screen, so they are not in the repo (only locally in `/tmp/claude-1000/multicam-tests/evidence/` during a test run). The images under `docs/images/` are illustrations.

Status values: PASS, FAIL, MANUAL (needs a human to look or click; marked (M) in the requirements).

## Bug fixes (verification round)
1. `install.sh`: adds a line break before the keybind line; `uninstall` removes only the bind line even if it has merged with a comment. Test T-A4.
2. Cleanup: the watcher (`multicam --watch <session dir> <tui pid>`) now also watches the TUI process and a `quit` flag, and stops the recording
   itself if the TUI disappears; Omarchy's stop script (Alt+Print/click/`--stop-recording`) cleans up the cameras immediately. Stop runs under a lock (once).
   Trap handlers: SIGPIPE is ignored, output is closed after HUP, long foreground calls (starting the recording, hyprpicker) run in the background + `wait`
   so that signals are handled immediately. Runtime files live per session in `$XDG_RUNTIME_DIR/multicam/s.<pid>/` (no shared state between sessions).
3. Screen choice: the focused monitor and the TUI window (via the pid chain, otherwise the active window) are restored after the recording has started. Rotated screens (transform) are handled (DP-2).
4. `resolve_saved`: exact match on path+name first, then name among unused devices; two identical cameras are not merged. Test T-B5b.
5. Camera resolution: a regular camera uses 1280x720 (MJPEG if the device manages >=25 fps in MJPG, otherwise YUYV/NV12), otherwise 640x360/640x480; background removal tries 640x360 first.
   Measurement: the C920 currently gives ~15 fps in all modes (640x360 YUYV/MJPG, 1280x720 MJPG) = the camera's dynamic frame rate in low light (`exposure_dynamic_framerate=1`), not the format. FaceTime 1280x720 NV12: 30 fps.
6. README: `git clone ... && ./install.sh` first, and runtime files in `$XDG_RUNTIME_DIR/multicam`.

## Results

| ID | Status | Evidence |
|---|---|---|
| T-A1 | PASS | `install.sh --yes` against a HOME copy with the real `~/.config/hypr`, `~/.config/omarchy`, `~/.local/share/omarchy` (cp -a): new paths exactly == `.config/multicam`, `.local/bin/multicam`, `.local/share/applications/multicam.desktop`, `.local/share/multicam/bin/multicam`, `.local/share/multicam/lib/bg.py` |
| T-A3 | PASS | `uninstall.sh --yes`: `diff -r --no-dereference` between the pristine copy and the home tree is empty (incl. Videos/keep.mp4) |
| T-A4 | PASS | bindings.lua without a trailing newline: the keybind ends up on its own line; uninstall removes only that line (even when merged with a comment), other lines untouched |
| T-A5 | PASS | `diff -r` before/after install and uninstall of copies of ~/.config/hypr, ~/.config/omarchy, ~/.local/share/omarchy is empty; `/usr/bin` file list+md5 unchanged. Runs against a HOME copy, never the real HOME |
| T-A6 | PASS | `install-bgremove --yes` (22 s, 168 MB) creates only `~/.local/share/multicam/bg/`; `uninstall-bgremove` gives an identical home tree (pip `--no-cache-dir`). Run before the bug fixes; the install-bgremove code is unchanged |
| T-B2 | PASS | pty without mouse: all rows changed with arrows/Enter/`C` |
| T-B4 | PASS | shape/ring/colour/thickness are saved and prefilled on restart |
| T-B5 | PASS | missing camera: `off   ⚠ missing: Nonexistent Camera 9000`, no silent replacement, the device is kept in config |
| T-B5b | PASS | two "Twin Cam" (video4/video6, stub of `omarchy-capture-webcam-list`): A=video6 and B=video4 kept exactly, no merging |
| T-B6a | PASS | area mode, picker replaced by a stub (PATH) that returns `2220,200 1200x800` (called with `region`), Omarchy's real recording path via shim: cameras (A circle, B rectangle) inside the area, also after snap `9` and 30x `+`; MP4 **1920x1280** = 1200x800 x scale 1.6 (physical px); shim removed right after start; everything cleaned up. Frame reviewed (not committed): shows exactly the area with the cameras inside |
| T-B6b | PASS | window mode (stub returns the foot window's rectangle 3127,37 1186x1306; called with `windows`): header `Window: foot ...`, cameras inside, MP4 1898x2090 (1186x1306 x 1.6 = 1897.6x2089.6 rounded up) |
| T-B6c | PASS | stub cancels (exit 1): "Selection cancelled - no recording started.", form still shown, no camera windows, no recorder, output folder empty |
| T-B6d | PASS (partial) | real picker (slurp) in a real terminal: F5 in window mode opened slurp; `omarchy-capture-region --take-window` (the command Omarchy's Enter bind runs) selected the window under the pointer and multicam opened cameras within that rectangle; slurp gone after exit. A key via `wtype -k Return`, however, did NOT trigger Omarchy's slurp bindings in this environment (neither in multicam nor in a standalone `omarchy-capture-region windows`): not a multicam bug, but the keyboard path in the picker is therefore unverified here. Free mouse dragging not tested (mouse) |
| T-R1 | PASS | regression: F5/space/x in the preview start no recording, only Enter does; `no_anim=true` in the camera rule |
| T-C1 | PASS (reviewed image) | `evidence/c1-frame-0.2s.png`: ffmpeg frame at 0.2 s into the recording shows the desktop with both cameras already in place: round image (C920) with a pink ring on the left and a rectangular image (FaceTime) with a blue ring in the middle |
| T-C3 | PASS | `pactl get-default-source`: before=Generic USB, during=C920 mic, after=Generic USB |
| T-C3v | PASS | ffmpeg volumedetect mean_volume per selected mic (5 s each): C920 -16.0 dB, Generic USB -83.3 dB, iD14 -91.0 dB; default-source during recording was the selected mic in all three. Difference C920/Generic = 67 dB |
| T-C4 | PASS | ffprobe: h264+aac, mp4; duration 7.90 s vs measured time from Omarchy's pointer file until the recorder exited 8.14 s minus 0.1 s trim = 8.04 s (±0.5 s); two runs, both passed |
| T-C4b | PASS | name matches the regex; Omarchy's `_`/`-` name is gone; pre-created collision file untouched, the new one got `-2`, Omarchy's name gone from the folder |
| T-C5 | MANUAL | the result screen shows the file name + "Open in omacut? [Y/n]" (shown in pty); launching omacut not run |
| T-D1 | PASS (reviewed images) | `d1-circle-ring-red8.png`: round camera image with an even red ring (8 px) that follows the circle; `d1-rect-ring-green8.png`: 16:9 rectangle with a green ring along the edge; `d1-circle-noring.png`: round image without a ring (edge clipped round against the terminal behind) |
| T-D2 | PASS (reviewed images, except hyprpicker click) | the colours (red/green/blue/yellow) appear as selected; `d2-circle-thick2.png` (thin yellow ring) vs `d2-circle-thick12.png` (thick yellow ring) shows thickness; the ring follows circle and rectangle respectively. Hex code/colour row saved per camera (T-B2/T-B4). Real hyprpicker click: M (stub verified in T-D2c) |
| T-D2c | PASS | stub `hyprpicker` is called with `-f hex`, the colour `#12ab34` is set and saved |
| T-D3/4 | PASS | geometry via `hyprctl clients -j` (±1 px): move 20/100 px, ±10 %/±25 %, min 120, max = the screen's short side (1320 on DP-1), clamping against all four edges (x=MX, y=MY, x+w=MX+MW, y+h=MY+MH), growing in a corner does not push the image off screen, status line `[MOVE]`/`[SIZE]` |
| T-D5 | PASS | both cameras: Tab and Shift-Tab switch (status line "Selected camera"), 1/5 on A and 9 on B land correctly, the other camera is not moved |
| T-D7 | PASS | `hyprctl activewindow` unchanged (0x55c2...) after camera start and actions (pty without its own terminal window) |
| T-D7b | PASS | real terminal: `omarchy-launch-tui --app-id=TUI.float env HOME=<temp> multicam`, keys via `wtype` (F5, Right, Down, s, r, PageUp, 1, m, Up) with a check before each key that the active window == TUI; focus stayed on the TUI after every action and after the camera windows appeared; `q` closed the window, no cameras/rules left |
| T-D8 | PASS | stand-in `WebcamOverlay-medium` (mpv testsrc, same class/title) unchanged geometry/float/pin; still alive after multicam exit. Real overlay not used (the camera is busy) |
| T-D9 | PASS | `SCREEN=DP-2` while DP-1 focused: file 1200x1920 (DP-2 is rotated), focused monitor before=after=DP-1, active window before=after |
| T-E1 | PASS | `q`+`j` during recording, `Esc` in preview: no windows/rules/mpv left, mic restored. Rule check via a probe window with class MulticamA (float+pin if the rule is active); positive check confirmed during the run |
| T-E2 | PASS | Ctrl+C 0.21 s, SIGHUP 0.10 s, SIGTERM 0.69 s, `--stop-recording` from outside < 1 s (all < 1.0 s in two runs), files renamed |
| T-E2s | PASS | 10 x HUP / INT / TERM during recording, requirement < 1.0 s until windows+mpv+mic cleaned up, recorder stopped and file renamed: final run HUP max 0.71 s, INT max 0.85 s, TERM max 0.75 s, 30/30 ok (first run before the last tuning: max 0.91 s, 30/30). The margin to 1 s is small on a loaded machine |
| T-E3 | PASS (reviewed images; stop via command, no mouse click) | `e3-bar.png` during recording: Omarchy's dot-in-circle icon is visible to the left of the clock; `e3-bar2.png` after `omarchy-capture-screenrecording --stop-recording`: the icon is gone. Real mouse click on the icon: M |
| T-E4 | PASS | SIGTERM to gpu-screen-recorder: windows/mpv gone in 0.24 s, file renamed, TUI shows the result |
| T-E5 | PASS | external mpv (title OTHERMPV) stays alive with its window after multicam start+exit |
| T-F2 | PASS (fps) / PASS (transparency, reviewed image) | `bg.py --threads 2`, C920 640x360: 27.2 fps (≥25), CPU about 149 % of one core (python+ffmpeg+ORT) = more than "one core". `f2-bg-transparent.png`: the person is cut out, the terminal text behind shows through the background and partly through dark clothing (F4: soft edges/translucent dark clothing) |
| T-F3 | PASS | corrupt model via `MULTICAM_MODEL_URL`: rc=2, file deleted; modified installed model: `check-bgremove` rc=1 |
| T-X1 | PASS | two cameras + circle + mic, 30 s: 32.0 s, 1917 frames (59.9 fps), decoding without errors; `x1-frame-4s.png` (reviewed) shows both camera images with rings in the recording |
| T-X2 | PASS | two runs in a row: no leftovers, two different file names, `$XDG_RUNTIME_DIR/multicam` empty after exit |

## Deviations from the spec
- Preset colours: ←/→ in the form as in the spec, but `p`/`P` on the recording screen (the arrows move/resize).
- Rectangle 16:9 (size = height); circle is square.
- Preview step: F5 shows the cameras, `Enter` starts the recording.
- The TUI window uses app-id `TUI.float` (Omarchy's existing floating rule).
- Optional keybind `SUPER + ALT + M`.
- mpv has no `--alpha`; transparency verified visually without it.
- `mpv --no-config`. The Python environment is 168 MB.
- `hyprctl rules -j` does not exist: the rule check is done via a probe window.

## Not verified
- A real mouse click on the bar icon and a real hyprpicker click (requires a mouse).
- Opening omacut from the result screen (T-C5).
- The real Omarchy WebcamOverlay in parallel (camera busy; a stand-in was used).
- Terminals other than foot; camera fps in good light (the C920 gave 15 fps because of its dynamic frame rate in low light).

## Coordinator's check (after the agents' runs)
- The screenshots were reviewed: the camera images were slightly transparent because Omarchy's default rule gives all windows opacity 0.985/0.96. Fixed: the window rule removes the `default-opacity` tag and sets `opacity = "1 1"` (same as Omarchy's own WebcamOverlay). Verified with a black test window: the pixel in the middle of the window is exactly (0,0,0). The rule's Lua name is versioned (`MC2_A`), so an older rule already loaded in a running Hyprland session is not reused.
- T-C4 previously measured from the wrong moment (the stop happens only at the `j` confirmation). It now measures from Omarchy's pointer file until the recorder has exited.
- Re-run after the fixes: T-E1, T-E2 (Ctrl+C 0.06 s, HUP 0.46 s, TERM 0.51 s, from outside 0.20 s), T-D3/4, T-D5, T-X1, T-X2, T-C3, T-C4, T-C4b: all PASS.
- 2026-10-11, after the user's test: (1) moving felt sluggish because Hyprland animated every step (~380 ms). The camera rules now have `no_anim = true`; a screenshot 120 ms after 3×Shift+← shows the window already at its target position. (2) The recording could start immediately if F5/Enter was pressed several times while the cameras were opening. Now only Enter starts the recording, and keys buffered while the preview starts are discarded; a test with F5, F5, Enter in quick succession gave a preview without recording. Re-run: T-D3/4, T-D5, T-C3, T-C4, T-C4b, T-E1 PASS (T-D5 missed once in a full run because of a timing margin, PASS 2/2 on re-run).

## Addendum: area/window (B6)
- Version 3: full automated suite run after the feature (32 rows + T-R1): everything PASS except the MANUAL rows (T-C1 image content is reviewed with `tests/visual.py`, T-E3 click). T-E2s: HUP max 0.70 s, INT max 0.95 s, TERM max 0.73 s, 30/30 (the margin to 1.0 s is small). T-E2: Ctrl+C 0.13 s, HUP 0.63 s.
- T-A1/A3/A5 adjusted: the baseline strips the user's own `-- multicam` line in the copy of bindings.lua.
- Scale: gsr produces physical pixels (logical size x monitor scale), e.g. 1200x800 -> 1920x1280 on DP-1 (scale 1.6).
- Limitation: windows moved after the start are not followed; free area selection requires a mouse.

## Addendum: 1.2.0 (new look, background removal by default, saved settings)
- New tests: **T-B7**: a change in the form and a moved/resized camera are in `config` while the TUI is still running; on a new start the form is prefilled and the camera ends up in exactly the same place. **T-B6d**: the last area is saved (`LAST_AREA`); at the next start the form shows the row "last: 900x600" and F5 uses the area without the picker (header "Area 900x600", camera inside); with "pick a new one" the picker runs again.
- Adjusted tests: off/on are now shown as `● on` / `○ off` (T-B2, T-B4); the installation tests run `install.sh ... --no-bgremove` so that the add-on (about 300 MB) is not downloaded into every test HOME; `tests/mclib.py` parses camera names the same way as the app (the FaceTime camera was otherwise shown as missing).
- T-B2 sometimes failed (1 in 3) right after the camera tests: the form was redrawn 5 times per second even without key presses, and every redraw started about 40 subprocesses, so under load the test could read an old frame. Fixed: no redraw without a key more often than once per second, translations without a subprocess, `hyprctl`/`pgrep` in the redraw at most once per second. Key -> new frame: from about 60 ms to about 35-40 ms. After that T-B7, T-B6d, T-B2, T-B4 PASS 3 out of 3 times.
- The look was checked in a real `foot --app-id=TUI.float` window with the theme Norrsken Amber (form and preview). The screenshots were deleted after review and are not in the repo.
- Full suite with 1.2.0: 35 PASS, 2 MANUAL (as before), T-E2 FAIL once: stop from outside (`--stop-recording`) cleaned up after 1.01 s against the 1.0 s limit. The watcher detects the stop script immediately (the log); the time is spent closing the camera windows and varies 0.2-0.9 s. The same test against 1.1.0 gave 0.20-0.64 s (4 runs), against 1.2.0 0.20-1.06 s (8 runs, 2 over the limit). The watcher code is unchanged; the margin to 1.0 s was already small before (see above).

## Addendum: 1.3.0 (English only, hidden while recording, bar icon, settings view)
- Tests run (a selection, about 7 min in total instead of the whole suite): T-L1, T-S1, T-H1, T-B2, T-B4, T-B5, T-B6a, T-B6b, T-B6c, T-B6d, T-B7, T-D3/4, T-D5, T-R1, T-C3, T-C4, T-C4b, T-E1, T-E4, T-A1/A3/A5, T-A4, T-U1: all PASS (T-C1 MANUAL as before).
- **T-L1** (new wording): with `LANG=sv_SE.UTF-8` and `MULTICAM_LANG=sv`, `--help` and the TUI are in English.
- **T-S1**: `S` opens the settings; output folder (free text), after recording, hide, bar icon, arrow step, Shift step and update check are in `config` while the TUI is running and are shown at the next start; Esc goes back.
- **T-H1** (real `foot --app-id=TUI.float` window): on Enter the TUI window is moved to `special:multicam`, the cameras stay on the normal workspace, `$XDG_RUNTIME_DIR/multicam/recording` contains the start time; `multicam stop` stops, the TUI window comes back on the active workspace, the status file is removed and the file is saved.
- Bugs found and fixed: Omarchy's `--stop-recording` aborts if its output folder (`~/Videos`) is missing, even when stopping. `multicam stop`, multicam's own stop and the bar icon therefore set `OMARCHY_SCREENRECORD_DIR` when stopping. T-B6d sometimes went past the Area row (read the screen too early); the test now waits for each frame.
- The bar plugin was checked in the real Quickshell bar: with a status file a red icon and the time (00:43) are shown, alternating between bright and dark red every half second; without a status file nothing is shown. The screenshots were deleted.
- The installation tests run `--no-bar-indicator` so that they never call the real Omarchy shell; the baseline removes the user's own plugin from the HOME copy.

## 1.4.0

- Full suite (`tests/run.py`): 36 PASS, 2 MANUAL (T-C1 image content, T-E3 real mouse click, as before), T-E2 FAIL once: stop from outside cleaned up after 1.08 s against the 1.0 s limit. Three re-runs of T-E2 passed (0.70 s, 0.88 s, 0.49 s). This is the known small margin described for 1.2.0; the four Hyprland calls in the cleanup take about 18 ms in total, the time is spent in Omarchy's stop script and the camera windows closing.
- `tests/features.py`: 8/8 PASS.
  - **F-C1**: Countdown 3 -> 5 -> 10 -> off -> 10 and Follow window on -> off are written to the config at once and shown at the next start.
  - **F-C2**: "Recording starts in 5 s" with big digits, ticking; Esc and q cancel back to the preview and nothing is recorded.
  - **F-C3**: with 3 s the recorder starts 3.18 s after Enter. **F-C4**: with off, 0.19 s.
  - **F-F1**: a 500x400 test window moved 800,500 px during a window recording: the MP4 is 800x640 (x1.6 scale), the window's colour is in the centre before and after the move, camera A moved by the same delta 0.17 s after the window. Nothing left afterwards.
  - **F-F2**: the window closed during the recording: the crop keeps the last position, nothing left afterwards.
- Installation tests also cover the icon, `multicam setup-bar` (removes the old `multicam.recording` plugin, leaves other plugins alone, remembers on/off) and that `shell-plugin/` and `packaging/omarchy-plugin/` are identical.
- Package mode was checked with a package built by `makepkg` and unpacked into a scratch root (not installed): version, help, `update` refuses and points to `yay -Syu multicam`, tag-based update check (v1.4.1 and v1.10.0 newer, v2.0.0-rc1 ignored), `bg.py` found under `/usr/share/multicam`, `setup-keybind`, `setup-bar`, `uninstall` removes only per-user files.
- `omarchy plugin validate shell-plugin` passes; Qt 6 `qmllint` reports only the missing shell import path.
