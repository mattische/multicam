#!/bin/bash
# multicam - install. No root, no packages installed.
# Flags: --yes (no questions, no keybind), --keybind / --no-keybind, --no-bgremove (skip the background-removal add-on),
#        --no-bar-indicator (skip the Quickshell bar plugin that blinks red while recording)
SRC=$(cd "$(dirname "$(readlink -f "$0")")" && pwd)
DATA=$HOME/.local/share/multicam
BIN=$HOME/.local/bin/multicam
APPS=$HOME/.local/share/applications
BINDINGS=$HOME/.config/hypr/bindings.lua
KEYCOMBO="SUPER + ALT + M"
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
for c in v4l2-ctl hyprpicker omacut grim git; do
  command -v "$c" >/dev/null || echo "Note: optional program missing: $c"
done

install -Dm755 "$SRC/bin/multicam" "$DATA/bin/multicam"
install -Dm644 "$SRC/lib/bg.py" "$DATA/lib/bg.py"
mkdir -p "$HOME/.local/bin" "$APPS" "$HOME/.config/multicam"
ln -sfn "$DATA/bin/multicam" "$BIN"
sed "s|@BIN@|$BIN|" "$SRC/multicam.desktop" >"$APPS/multicam.desktop"
# remember where this came from, so 'multicam update' / the update check can compare with origin/main
if git -C "$SRC" rev-parse HEAD >/dev/null 2>&1; then
  git -C "$SRC" rev-parse HEAD >"$DATA/rev"
  git -C "$SRC" remote get-url origin >"$DATA/source" 2>/dev/null || rm -f "$DATA/source"
fi

if [[ $kb == ask && $yes == 0 && -t 0 ]]; then
  read -r -p "Add the shortcut $KEYCOMBO to ~/.config/hypr/bindings.lua? [y/N] " a
  [[ $a == [jJyY]* ]] && kb=yes
fi
if [[ $kb == yes ]]; then
  if [[ ! -f $BINDINGS ]]; then
    echo "Could not find $BINDINGS - no shortcut added."
  elif grep -q -- '-- multicam$' "$BINDINGS"; then
    echo "The shortcut already exists."
  elif grep -q "\"$KEYCOMBO\"" "$BINDINGS"; then
    echo "$KEYCOMBO is already used in $BINDINGS - no shortcut added."
  else
    # make sure our line starts on its own line (the file may lack a trailing newline)
    [[ -s $BINDINGS && -n $(tail -c1 "$BINDINGS") ]] && echo >>"$BINDINGS"
    printf 'o.bind("%s", "Multicam", "omarchy-launch-tui --app-id=TUI.float %s") -- multicam\n' "$KEYCOMBO" "$BIN" >>"$BINDINGS"
    echo "Shortcut $KEYCOMBO added (the line ends with '-- multicam')."
  fi
fi

# bar indicator: a small Omarchy shell (Quickshell) plugin that shows a blinking red record icon while multicam
# records; click stops the recording. Installed into ~/.config/omarchy/plugins/multicam.recording and enabled.
PLUGIN_DIR=$HOME/.config/omarchy/plugins/multicam.recording
if [[ $barind == yes ]]; then
  if [[ -d $HOME/.config/omarchy ]] && command -v omarchy-shell >/dev/null; then
    install -Dm644 "$SRC/shell-plugin/manifest.json" "$PLUGIN_DIR/manifest.json"
    install -Dm644 "$SRC/shell-plugin/Recording.qml" "$PLUGIN_DIR/Recording.qml"
    timeout 5 omarchy-shell shell rescanPlugins >/dev/null 2>&1
    if timeout 10 omarchy plugin enable multicam.recording >/dev/null 2>&1; then
      echo "Bar indicator enabled (blinking red icon while recording)."
    else
      echo "Bar indicator installed in $PLUGIN_DIR; enable it with: omarchy plugin enable multicam.recording"
    fi
  else
    echo "Note: Omarchy shell not found - the bar indicator was not installed."
  fi
fi

# background removal (transparent camera background, about 300 MB) is installed by default; --no-bgremove skips it.
# A failure (e.g. offline) does not stop the installation: the add-on can be installed later.
if [[ $bg == yes ]]; then
  echo "Installing the background-removal add-on (skip with --no-bgremove)..."
  "$BIN" install-bgremove --yes || echo "The add-on could not be installed now - try again later with 'multicam install-bgremove'."
fi

echo "multicam installed: $BIN"
[[ -x $DATA/bg/venv/bin/python ]] || echo "Optional: 'multicam install-bgremove' (or select the Background removal row in the app) adds transparent camera background."
echo "Update later with 'multicam update' (the app also tells you when a new version exists)."
