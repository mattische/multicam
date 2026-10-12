# Status and handoff (2026-10-12)

## Where things stand
- multicam 1.0.0 is complete per `docs/kravspec.md` (requirements A–F plus B6: full screen / area / window).
- Test results: `docs/TEST-REPORT.md`. The automatic suite passes on the original machine (mbp-omarchy).
- Installed there with the keybind `SUPER + ALT + M` (line ending in `-- multicam` in `~/.config/hypr/bindings.lua`).

## Continue on another machine
```
git clone git@github.com:mattische/multicam.git && cd multicam
./install.sh --keybind        # or ./install.sh for no keybind
multicam install-bgremove     # optional background-removal add-on
```
Requirements: Omarchy with Hyprland 0.56+ and Lua config. Only Lua dispatches are used (see BRIEF.md).

## Running the tests elsewhere
The tests were written for the original machine and contain hardware-specific values:
- `tests/mclib.py`: `SCRATCH=/tmp/claude-1000/multicam-tests`, `CAMS` (C920 = /dev/video2, FaceTime = /dev/video0), `BASE_CFG`.
- `tests/run.py`: `MIC_C920` (PulseAudio source name) and camera paths in some tests.

Adjust these to the new machine's devices first (`omarchy-capture-webcam-list`, `pactl list short sources`).
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
