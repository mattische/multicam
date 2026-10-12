#!/bin/bash
# multicam - install. No root, no packages installed.
# Flags: --yes (no questions, no keybind), --keybind / --no-keybind, --no-bgremove (skip the background-removal add-on),
#        --no-bar-indicator (skip the Quickshell bar plugin that blinks red while recording)
#        curl -fsSL https://raw.githubusercontent.com/mattische/multicam/main/install.sh | bash [-s -- flags]
# A system-wide install from the AUR (yay -S multicam) needs none of this; the two must not be mixed.
if command -v pacman >/dev/null && pacman -Q multicam >/dev/null 2>&1; then
  echo "multicam is installed as a package (pacman -Q multicam); update it with: yay -Syu multicam" >&2
  echo "For a per-user install instead, remove the package first: sudo pacman -Rns multicam" >&2
  exit 1
fi
# read from stdin (curl | bash) there is no script file, so never use the current folder as the source
SRC=
[[ -f ${BASH_SOURCE[0]} ]] && SRC=$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)

# bootstrap: run without the repository next to it (curl | bash, or a lone downloaded install.sh) -> clone it into a
# temporary folder and run the install.sh from there. MULTICAM_REPO overrides the git URL.
if [[ ! -f $SRC/bin/multicam || ! -f $SRC/multicam.desktop ]]; then
  repo=${MULTICAM_REPO:-https://github.com/mattische/multicam.git}
  command -v git >/dev/null || { echo "git is needed to download multicam." >&2; exit 1; }
  tmp=$(mktemp -d) || exit 1
  echo "Downloading multicam from $repo ..."
  if ! GIT_TERMINAL_PROMPT=0 git clone -q --depth 1 -b main "$repo" "$tmp/multicam"; then
    rm -rf "$tmp"
    echo "Could not download $repo (offline, or the repository is not public)." >&2
    exit 1
  fi
  bash "$tmp/multicam/install.sh" "$@"
  rc=$?
  rm -rf "$tmp"
  exit $rc
fi

DATA=$HOME/.local/share/multicam
BIN=$HOME/.local/bin/multicam
APPS=$HOME/.local/share/applications
ICON=$HOME/.local/share/icons/hicolor/scalable/apps/multicam.svg
yes=0; kb=ask; bg=yes; barind=yes
for a in "$@"; do
  case $a in
    --yes | -y) yes=1 ;;
    --keybind) kb=yes ;;
    --no-keybind) kb=no ;;
    --bgremove) bg=yes ;;
    --no-bgremove) bg=no ;;
    --no-bar-indicator) barind=no ;;
    *) echo "Unknown flag: $a" >&2; exit 2 ;;
  esac
done

missing=()
for c in hyprctl jq mpv pactl gpu-screen-recorder omarchy-capture-screenrecording omarchy-launch-tui; do
  command -v "$c" >/dev/null || missing+=("$c")
done
if ((${#missing[@]})); then
  echo "Missing dependencies (install them yourself, nothing is installed here): ${missing[*]}" >&2
  exit 1
fi
for c in v4l2-ctl hyprpicker omacut git; do
  command -v "$c" >/dev/null || echo "Note: optional program missing: $c"
done

install -Dm755 "$SRC/bin/multicam" "$DATA/bin/multicam"
install -Dm644 "$SRC/lib/bg.py" "$DATA/lib/bg.py"
rm -rf "$DATA/shell-plugin"   # the bar plugin files (copied into the plugin folder by 'multicam setup-bar')
mkdir -p "$DATA/shell-plugin" && cp -- "$SRC"/shell-plugin/* "$DATA/shell-plugin/"
install -Dm644 "$SRC/assets/multicam.svg" "$ICON"
mkdir -p "$HOME/.local/bin" "$APPS" "$HOME/.config/multicam"
ln -sfn "$DATA/bin/multicam" "$BIN"
sed "s|@BIN@|$BIN|" "$SRC/multicam.desktop" >"$APPS/multicam.desktop"
# remember where this came from, so 'multicam update' / the update check can compare with origin/main
if git -C "$SRC" rev-parse HEAD >/dev/null 2>&1; then
  git -C "$SRC" rev-parse HEAD >"$DATA/rev"
  git -C "$SRC" remote get-url origin >"$DATA/source" 2>/dev/null || rm -f "$DATA/source"
fi

# questions are read from the terminal, so they also work when this script itself arrives on stdin (curl | bash)
if [[ $kb == ask && $yes == 0 ]] && { exec 3</dev/tty; } 2>/dev/null; then
  read -r -u 3 -p "Add the shortcut SUPER + ALT + M to ~/.config/hypr/bindings.lua? [y/N] " a
  exec 3<&-
  [[ $a == [jJyY]* ]] && kb=yes
fi
# the keybind and the bar plugin are set up by the app itself (also used by the AUR package)
[[ $kb == yes ]] && "$BIN" setup-keybind

# bar indicator: a small Omarchy shell (Quickshell) plugin that shows a blinking red record icon while multicam
# records; click stops the recording. 'multicam setup-bar' copies it into
# ~/.config/omarchy/plugins/io.github.mattische.multicam, enables it and removes the older multicam.recording plugin.
[[ $barind == yes ]] && "$BIN" setup-bar

# background removal (transparent camera background, about 300 MB) is installed by default; --no-bgremove skips it.
# A failure (e.g. offline) does not stop the installation: the add-on can be installed later.
if [[ $bg == yes ]]; then
  echo "Installing the background-removal add-on (skip with --no-bgremove)..."
  "$BIN" install-bgremove --yes || echo "The add-on could not be installed now - try again later with 'multicam install-bgremove'."
fi

echo "multicam installed: $BIN"
[[ -x $DATA/bg/venv/bin/python ]] || echo "Optional: 'multicam install-bgremove' (or select the Background removal row in the app) adds transparent camera background."
echo "Update later with 'multicam update' (the app also tells you when a new version exists)."
