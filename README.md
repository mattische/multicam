# multicam

Record your screen with one or two **camera overlays** and a microphone, from a small keyboard-driven terminal app.
For [Omarchy](https://omarchy.org) (Hyprland on Arch Linux). The result is a plain MP4.

- Cameras are floating windows: round or rectangular, with an optional coloured ring, placed and resized with the keyboard.
- Record the full screen, an area or a single window (it can follow the window if you move it).
- Optional transparent camera background (background removal).
- Countdown before recording, a blinking red icon in the bar while recording, remembers all settings.

![multicam: a code editor with a round and a rectangular camera overlay, and the multicam window](docs/images/overview.svg)

![The settings form](docs/images/form.svg)
![Placing the cameras in the preview](docs/images/controls.svg)

<sub>Illustrations, not screenshots.</sub>

## Install

```
curl -fsSL https://raw.githubusercontent.com/mattische/multicam/main/install.sh | bash
```

Per user, no root. It asks about an optional keybind (`SUPER + ALT + M`). Start multicam from the app menu or with `multicam`.
Arch users can also use the AUR package (`yay -S multicam`, once published). More options: [docs/GUIDE.md](docs/GUIDE.md#install).

## Update

```
multicam update
```

The app also tells you at startup when a new version exists (press `U`). AUR: `yay -Syu multicam`.

## Uninstall

```
multicam uninstall
```

Your recordings are never touched. AUR: also `sudo pacman -Rns multicam`.

## Dependencies

Normal Omarchy install: `hyprctl`, `jq`, `mpv`, `pactl`, `gpu-screen-recorder`, `omarchy-capture-screenrecording`.
Optional: `v4l2-ctl`, `hyprpicker` (colour picker), `ffmpeg` (follow a window), `git` (updates),
`python3` + `curl` (background removal, ~300 MB, installed by default and can be skipped with `--no-bgremove`).

## Use

1. Choose cameras, microphone and what to record, then select **Preview cameras** and press `Enter`.
2. Place the cameras with the arrow keys (`m` switches between move and resize), then press `Enter` to record.
3. Stop with **`F12`**, the bar icon, the keybind again, or `multicam stop`. `Esc` goes back, `q` quits.

Keys, settings, capture modes, background removal, limitations and tests: **[docs/GUIDE.md](docs/GUIDE.md)**.

## Licence

MIT. Background removal uses Robust Video Matting (GPL-3.0), downloaded separately.
