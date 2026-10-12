# Status and handoff (2026-10-12)

_1.3.0: English only (Swedish removed); multicam hides itself (special:multicam) while recording and comes back when it stops; a Quickshell bar plugin (`shell-plugin/`, installed as `multicam.recording`) shows a blinking red icon + time while recording, click stops; `multicam stop` (also the keybind pressed again while recording); settings view (`S`): output folder, after recording, hide, bar indicator, arrow steps, update check. Tests T-S1, T-H1 added, T-L1 now checks English only._

_1.2.0: new TUI look that follows the active Omarchy theme (colours from `colors.toml`), the background-removal add-on is installed by default (`--no-bgremove` skips it), and all settings are saved as soon as they change, including camera positions for area/window recording and the last area (reusable from the form)._

_Added after 1.0.0: English UI with system-language detection (Swedish kept), optional background-removal install from `install.sh` and from the form, `multicam update` / `check-update` with a startup update check (U in the form). Tests T-L1 (language) and T-U1 (update, local git origin) added._

## Where things stand
- multicam 1.3.0 is complete per `docs/kravspec.md` (requirements A–F plus B6: full screen / area / window).
- Test results: `docs/TEST-REPORT.md`. The automatic suite passes on the original machine (mbp-omarchy).
- Installed there with the keybind `SUPER + ALT + M` (line ending in `-- multicam` in `~/.config/hypr/bindings.lua`).

## Continue on another machine
```
git clone git@github.com:mattische/multicam.git && cd multicam
./install.sh --keybind        # or ./install.sh for no keybind; the background-removal add-on is included (--no-bgremove skips it)
```
Requirements: Omarchy with Hyprland 0.56+ and Lua config. Only Lua dispatches are used (see BRIEF.md).

## Running the tests elsewhere
Devices are autodetected (first two cameras from `omarchy-capture-webcam-list`, first two non-monitor sources from `pactl`). Override with env vars:
`MC_CAM_A_DEV`, `MC_CAM_A_NAME`, `MC_CAM_B_DEV`, `MC_CAM_B_NAME`, `MC_MIC`, `MC_MIC2` (T-C3v needs two mics), `MC_SCRATCH`.
Run with `python3 tests/run.py [T-ID ...]`; the screen must be unlocked.
Screenshots/frames are written outside the repo and must never be committed (they show the camera and screen).

## Open items / not verified
- A real mouse click on the bar's recording icon (stopping via the command works).
- A real hyprpicker click (`c`).
- Omacut opening from the result screen (T-C5).
- Omarchy's area picker with mouse drag, and keyboard selection in its window picker (Tab/arrows + Enter).
- Terminals other than foot.
- Background removal uses about 1.5 cores, not 1 (27 fps).
- The C920 gives about 15 fps in poor light (the camera's auto exposure); fine in good light.

## Files
- `bin/multicam`: the whole app (bash). `lib/bg.py`: background removal.
- `install.sh` / `uninstall.sh` / `multicam.desktop`.
- `docs/kravspec.md`: requirements spec (Swedish). `docs/BRIEF.md`: technical facts and design for developers/agents.
- `docs/prototypes/`: early prototypes (reference only).
- `docs/images/`: illustrations for the README (SVG).
