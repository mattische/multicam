# Implementation brief (for agents)

Authoritative requirements: `docs/kravspec.md` (Swedish). Every requirement ID (A1…F5) must be met, every test (T-…) must be runnable.
This brief adds verified facts from earlier prototyping on this machine. Read both before writing code.

## Machine facts
- Omarchy, Hyprland 0.56.2 **with Lua config**. Only Lua dispatches work:
  `hyprctl dispatch 'hl.dsp.window.move({ window = "class:^MulticamA$", x = X, y = Y })'` (global layout px),
  `hl.dsp.window.resize({ window = ..., x = W, y = H })`, `hl.dsp.window.set_prop({ window = ..., prop = "rounding", value = N })`,
  `hl.dsp.window.close({ window = ... })`. Batch with `hyprctl --batch "dispatch ...; dispatch ..."`.
  Legacy `movewindowpixel`/`resizewindowpixel`, `hyprctl setprop/getprop` do NOT work.
- Runtime window rule (create before mpv starts, disable at cleanup):
  `hyprctl eval 'MC_A = hl.window_rule({name="multicam-A", match={class="^MulticamA$"}, float=true, pin=true, no_initial_focus=true, border_size=0, no_dim=true, size={300,300}})'`
  and `hyprctl eval 'MC_A:set_enabled(false)'`. Rule `rounding` is capped at 20, so circle = `set_prop rounding = size/2` after map.
  Border ring: `set_prop border_size`, `inactive_border_color` and `active_border_color` = `"rgba(rrggbbff)"`.
- Shell env inside agent Bash tool needs: `export XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-1 HYPRLAND_INSTANCE_SIGNATURE=$(ls -t /run/user/1000/hypr | head -1)`.
- Monitors: eDP-1 (scale 1.6), DP-1 3840x2160 scale 1.6 at x=1920 (usually focused), DP-2 1920x1200 at x=4320. All reserve 30 px top (bar). Use logical size = width/scale minus `reserved`.
- Cameras: `omarchy-capture-webcam-list` prints `/dev/video2  HD Pro Webcam C920 (...)` and `/dev/video0  FaceTime HD Camera (Built-in): (...)`. A v4l2 device can only be opened by one process at a time.
  Pick video_size per device with `v4l2-ctl --list-formats-ext` (prefer 1280x720, then 640x480; FaceTime supports 1280x720).
- Mics: `pactl -f json list sources`, skip names ending in `.monitor`. Current default is the user's; save with `pactl get-default-source`, restore always.
- `bc` is not installed (use awk/bash ints). gum 2.0, jq, hyprpicker, wtype, grim, ffmpeg/ffprobe, mpv, omacut (`/usr/bin/omacut <file>`), `omarchy-launch-tui` all present.

## omarchy-capture-screenrecording (read /usr/bin/omarchy-capture-screenrecording)
- `--fullscreen` records the **focused** monitor (`omarchy-hyprland-monitor-focused`). To record another monitor, focus it first (Lua dispatch for focusing a monitor) and restore afterwards — or just document "focused monitor" if you can't verify it.
- Output dir `$OMARCHY_SCREENRECORD_DIR` or `$XDG_VIDEOS_DIR` or `~/Videos`; file `screenrecording-%Y-%m-%d_%H-%M-%S.mp4`; current file path written to `/tmp/omarchy-screenrecord-filename` while recording. multicam should honour a `MULTICAM_OUTPUT_DIR` env var (passed through as `OMARCHY_SCREENRECORD_DIR`) so tests don't litter ~/Videos.
- Start returns once the file exists and gpu-screen-recorder runs. Calling the script again (or `--stop-recording`) stops: SIGINT, then **finalize** (trim/loudnorm, ~2 s), preview png (deleted after 2 s), notification, then removes `/tmp/omarchy-screenrecord-filename`. Finalize runs in whichever process called stop (ours, or the bar click / Alt+Print). So: "recording finished" = gpu-screen-recorder gone AND `/tmp/omarchy-screenrecord-filename` gone. Only then rename to `screenrecording-YYYY-MM-DD-HH_MM_SS.mp4` (C4; `-2`, `-3` on collision).
- Mic: script uses PipeWire `default_input`, so set `pactl set-default-source <chosen>` before start, restore after (C3).
- Never pass `--with-webcam`. Cameras must be mapped and positioned BEFORE starting the recording (C1).
- Refuse to start if a recording is already running (`pgrep -f '^gpu-screen-recorder'`).

## Camera windows (prototype in kbd-proto.sh below — reuse its logic)
```
mpv "av://v4l2:$DEV" --profile=low-latency --untimed --no-cache --demuxer-lavf-o=video_size=WxH,framerate=30 \
  '--vf=lavfi=[crop=ih:ih]'    # circle (1:1); rectangle: crop=ih*8/9:ih  (or keep 4:3/16:9 — your call, document it)
  --title=MulticamA --wayland-app-id=MulticamA --no-border --no-audio --no-osc --osd-level=0 \
  --no-input-default-bindings --panscan=1 --keepaspect-window=no --terminal=no --really-quiet
```
Use `--input-ipc-server=$RUNDIR/mpvA.sock` so shape change (crop) can be applied live via `vf set` without restarting, or restart that one mpv (acceptable). Keep a PID file per window in `$XDG_RUNTIME_DIR/multicam/`. Never `pkill mpv`; close by class + own PIDs (E5).
Prototype key loop handles CSI/SS3 escape sequences, Shift+arrows (`\e[1;2A` etc.), PgUp/PgDn (`\e[5~`/`\e[6~`), numpad presets 1–9, clamp to monitor, resize ±10 % around centre. Copy from it.

## TUI design (agreed with user; UI text in Swedish)
Screen 1 (form, pure bash full-screen, no gum needed; ↑↓ row, ←→ change value, Enter = toggle/choose, F5 or `Enter` on "Starta" starts, q/Esc quits):
```
┌─ multicam ──────────────────────────────────────────────┐
│  Kamera A    ▸ HD Pro Webcam C920                       │
│     form       ● cirkel   ○ rektangel      ring [x]     │
│     kantfärg   ■ #ff3399   tjocklek 4                    │
│     bakgrund   [ ] bort        (only if add-on installed)│
│  Kamera B      FaceTime HD Camera                       │
│     ...                                                 │
│  Mikrofon      Audient iD14                             │
│  Skrivbordsljud  [x] på                                 │
│  Skärm           DP-1 (fokuserad)                       │
│  ↑↓ rad   ←→ ändra   F5 starta   q avsluta              │
└─────────────────────────────────────────────────────────┘
```
Screen 2 (after start: cameras appear, are placed, THEN recording starts; header shows `● SPELAR IN mm:ss`, selected camera, `[FLYTTA]`/`[STORLEK]`):
keys per kravspec D3–D6: Tab, arrows (+Shift), m, +/-/PgUp/PgDn, 1–9, s, r, c (hyprpicker), C (hex input), ←/→ in colour row? — NOTE: arrows are taken by move/size; put the 8 preset colours on `p` (cycle) instead and document this deviation clearly in README + report, or find a clean alternative. `[`/`]` thickness, b bg-removal, q/Esc stop (confirm), after stop: show final filename and "Öppna i omacut? [J/n]".
Position/size/shape/colour per camera are saved to config on exit (B4) and reused next time.
Hardware ids in config: store device path AND name; on start, if saved device missing, show a clear warning in the form row ("⚠ saknas: <name>") and set to "av" (B5).

## Robustness (E)
- trap EXIT/INT/TERM/HUP → cleanup (idempotent): stop recording if ours running, close own windows, disable rules, restore mic, refresh indicator, restore tty.
- Watcher (E4): background subshell started after recorder confirmed, polls `pgrep -f '^gpu-screen-recorder'` every 0.2 s; when gone, closes windows/rules/mic and signals the TUI (e.g. writes a flag + kill -USR1 TUI pid) so the TUI shows the result screen. The TUI also polls the flag in its key loop (read -t 0.2).
- Rename happens after finalize (see above), done by whoever notices first (TUI or watcher), guarded by a lock (`mkdir` lock).

## Background removal add-on (F)
Prototype `bg.py` (below) + launch: `python bg.py | mpv - --demuxer=rawvideo --demuxer-rawvideo-w=640 --demuxer-rawvideo-h=480 --demuxer-rawvideo-mp-format=rgba --demuxer-rawvideo-fps=30 --vo=gpu-next --background=color --background-color='#00000000' ...`.
Install: `python3 -m venv ~/.local/share/multicam/bg/venv`, pip install `onnxruntime numpy` (no opencv needed in prod), download
`https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3_fp32.onnx`, verify SHA256 `88d4531297118f595bf2fd60f6f566aec2e559393802d1f436c380f0cbbd2828`, abort + delete on mismatch. Show GPL-3.0 notice. Threads 2, ratio 0.25.
For circle shape with bg removal, crop square in bg.py before output.

## Files / install
- Repo layout suggestion: `bin/multicam` (main, bash), `lib/` (bash modules and `bg.py` if wanted), `install.sh`, `uninstall.sh`, `multicam.desktop`, `tests/` (automated tests), `README.md` (English, short: what, install, uninstall, usage, keys table, known limitations).
- install.sh copies to `~/.local/share/multicam/`, symlink or wrapper at `~/.local/bin/multicam`, desktop file `Exec=omarchy-launch-tui --app-id=multicam multicam` (check that flag exists in /usr/bin/omarchy-launch-tui; window should float — add a runtime-free way: e.g. app-id matching an existing Omarchy floating rule, or document), checks deps and lists missing ones, asks y/N for optional keybind (line in `~/.config/hypr/bindings.lua` with marker comment `# multicam` / `-- multicam`, uninstall removes exactly that). `install.sh --yes`/`--no-keybind` for non-interactive tests. HOME override must work for test T-A1 (use `$HOME` everywhere).
- `multicam uninstall` confirms, removes A2 files, keybind line, bg add-on; never touches Videos.
