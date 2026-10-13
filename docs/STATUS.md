# Status and handoff (2026-10-12)

_Navigation hints: the form, preview and recording screens now say what Enter and Esc do (Esc in the preview goes back to the form; a recording is stopped only by F12 in the window, the bar icon, the keybind or `multicam stop` - q/Esc/Enter are ignored while recording); test T-N1._

_1.4.0: countdown before recording (3/5/10 s or off, `COUNTDOWN`); window capture follows a moving window (`FOLLOW_WINDOW`: records the window's monitor, tracks the window, moves the cameras along, crops with ffmpeg afterwards); everything in the repo is English (code comments, tests, docs; the spec is now `docs/requirements.md`); MIT licence; app icon (`assets/multicam.svg`); system-wide install from an AUR package (`packaging/aur/`, package mode in `bin/multicam`: `/usr/share/multicam`, update/uninstall point to yay/pacman); the bar plugin is now `io.github.mattische.multicam` (`shell-plugin/`, `multicam setup-bar`, replaces `multicam.recording`) and is prepared for publishing as an Omarchy plugin (`packaging/omarchy-plugin/`, `packaging/NOTES.md`); `multicam setup-keybind`; one-line install with `curl … | bash`. Tests: `tests/features.py` (F-C1–F-C4 countdown, F-F1/F-F2 follow), T-A1 extended (icon, setup-bar migration)._

_1.3.0: English only (Swedish removed); multicam hides itself (special:multicam) while recording and comes back when it stops; a Quickshell bar plugin (`shell-plugin/`, installed as `multicam.recording`) shows a blinking red icon + time while recording, click stops; `multicam stop` (also the keybind pressed again while recording); settings view (`S`): output folder, after recording, hide, bar indicator, arrow steps, update check. Tests T-S1, T-H1 added, T-L1 now checks English only._

_1.2.0: new TUI look that follows the active Omarchy theme (colours from `colors.toml`), the background-removal add-on is installed by default (`--no-bgremove` skips it), and all settings are saved as soon as they change, including camera positions for area/window recording and the last area (reusable from the form)._

_Added after 1.0.0: English UI with system-language detection (Swedish kept), optional background-removal install from `install.sh` and from the form, `multicam update` / `check-update` with a startup update check (U in the form). Tests T-L1 (language) and T-U1 (update, local git origin) added._

## Where things stand
- multicam 1.4.0 is complete per `docs/requirements.md` (requirements A–F plus B6: full screen / area / window).
- The GitHub repository is public; release `v1.4.0` exists (tag + GitHub release). `packaging/aur/PKGBUILD` has the real
  sha256 of the v1.4.0 tarball and builds with `makepkg` (checked; not installed, namcap not run).
- `curl -fsSL https://raw.githubusercontent.com/mattische/multicam/main/install.sh | bash` was tested against GitHub.
- Test results: `docs/TEST-REPORT.md`. The automatic suite passes on the original machine (mbp-omarchy).
- Installed there with the keybind `SUPER + ALT + M` (line ending in `-- multicam` in `~/.config/hypr/bindings.lua`).

## Next steps (pick up here)
1. Publish the AUR package (needs the user's AUR account + ssh key; see `packaging/NOTES.md`):
   `git clone ssh://aur@aur.archlinux.org/multicam.git`, copy `packaging/aur/PKGBUILD` and `.SRCINFO`, commit, push.
   Then `yay -S multicam` should work. Run `namcap` on the built package first if available.
2. Optional: publish the bar plugin on its own: a separate public repo (e.g. `mattische/omarchy-multicam-plugin`) whose
   root is `packaging/omarchy-plugin/` (`omarchy plugin add` clones the whole repo and needs `manifest.json` at the
   root), then submit it to the Omarchy plugin marketplace. `shell-plugin/` is the single source; keep the copy identical.
3. Each new release: bump `VERSION` in `bin/multicam`, tag `vX.Y.Z`, `gh release create`, then in `packaging/aur/`
   set `pkgver`, run `updpkgsums` and `makepkg --printsrcinfo > .SRCINFO`, and push those to the AUR.
- Known: T-E2 "stop from outside" has a small margin to its 1.0 s limit (1.08 s once, re-runs 0.49–0.88 s).
- Known: enabling the bar plugin makes the Omarchy shell busy for a few seconds, so `install.sh` may print
  "omarchy-shell is not responding"; the plugin is still enabled.

## Continue on another machine
```
git clone https://github.com/mattische/multicam.git && cd multicam
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
- `install.sh` / `uninstall.sh` / `multicam.desktop` / `assets/multicam.svg` (icon).
- `shell-plugin/`: the Omarchy bar plugin (single source; `packaging/omarchy-plugin/` is a copy for a separate plugin repo).
- `packaging/aur/`: PKGBUILD + .SRCINFO. `packaging/NOTES.md`: package mode and publishing steps.
- `docs/requirements.md`: requirements spec. `docs/BRIEF.md`: technical facts and design for developers/agents.
- `docs/prototypes/`: early prototypes (reference only).
- `docs/images/`: illustrations for the README (SVG).
