#!/bin/bash
# multicam - install. No root, no packages installed.
# Flags: --yes (no questions, no keybind), --keybind / --no-keybind, --no-bgremove (skip the background-removal add-on)
SRC=$(cd "$(dirname "$(readlink -f "$0")")" && pwd)
DATA=$HOME/.local/share/multicam
BIN=$HOME/.local/bin/multicam
APPS=$HOME/.local/share/applications
BINDINGS=$HOME/.config/hypr/bindings.lua
KEYCOMBO="SUPER + ALT + M"
# English, or Swedish if the system language is Swedish (MULTICAM_LANG=sv|en overrides)
case ${MULTICAM_LANG:-${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}} in sv*) sv=1 ;; *) sv=0 ;; esac
_() { if ((sv)); then printf '%s\n' "$2"; else printf '%s\n' "$1"; fi; }
yes=0; kb=ask; bg=yes
for a in "$@"; do
  case $a in
    --yes | -y) yes=1 ;;
    --keybind) kb=yes ;;
    --no-keybind) kb=no ;;
    --bgremove) bg=yes ;;
    --no-bgremove) bg=no ;;
    *) echo "Unknown flag: $a" >&2; exit 2 ;;
  esac
done

missing=()
for c in hyprctl jq mpv pactl gpu-screen-recorder omarchy-capture-screenrecording omarchy-launch-tui; do
  command -v "$c" >/dev/null || missing+=("$c")
done
if ((${#missing[@]})); then
  echo "$(_ "Missing dependencies (install them yourself, nothing is installed here):" "Saknade beroenden (installera själv, inget installeras här):") ${missing[*]}" >&2
  exit 1
fi
for c in v4l2-ctl hyprpicker omacut grim git; do
  command -v "$c" >/dev/null || echo "$(_ "Note: optional program missing:" "Obs: valfritt program saknas:") $c"
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
  read -r -p "$(_ "Add the shortcut $KEYCOMBO to ~/.config/hypr/bindings.lua? [y/N] " "Lägg in genvägen $KEYCOMBO i ~/.config/hypr/bindings.lua? [j/N] ")" a
  [[ $a == [jJyY]* ]] && kb=yes
fi
if [[ $kb == yes ]]; then
  if [[ ! -f $BINDINGS ]]; then
    _ "Could not find $BINDINGS - no shortcut added." "Hittade inte $BINDINGS - ingen genväg inlagd."
  elif grep -q -- '-- multicam$' "$BINDINGS"; then
    _ "The shortcut already exists." "Genvägen finns redan."
  elif grep -q "\"$KEYCOMBO\"" "$BINDINGS"; then
    _ "$KEYCOMBO is already used in $BINDINGS - no shortcut added." "$KEYCOMBO används redan i $BINDINGS - ingen genväg inlagd."
  else
    # make sure our line starts on its own line (the file may lack a trailing newline)
    [[ -s $BINDINGS && -n $(tail -c1 "$BINDINGS") ]] && echo >>"$BINDINGS"
    printf 'o.bind("%s", "Multicam", "omarchy-launch-tui --app-id=TUI.float %s") -- multicam\n' "$KEYCOMBO" "$BIN" >>"$BINDINGS"
    _ "Shortcut $KEYCOMBO added (the line ends with '-- multicam')." "Genväg $KEYCOMBO inlagd (raden slutar med '-- multicam')."
  fi
fi

# background removal (transparent camera background, about 300 MB) is installed by default; --no-bgremove skips it.
# A failure (e.g. offline) does not stop the installation: the add-on can be installed later.
if [[ $bg == yes ]]; then
  _ "Installing the background-removal add-on (skip with --no-bgremove)..." "Installerar tillägget bakgrund bort (hoppa över med --no-bgremove)..."
  "$BIN" install-bgremove --yes || _ "The add-on could not be installed now - try again later with 'multicam install-bgremove'." "Tillägget kunde inte installeras nu - försök igen senare med 'multicam install-bgremove'."
fi

_ "multicam installed: $BIN" "multicam installerat: $BIN"
[[ -x $DATA/bg/venv/bin/python ]] || _ "Optional: 'multicam install-bgremove' (or select the Background removal row in the app) adds transparent camera background." "Valfritt: 'multicam install-bgremove' (eller välj raden Bakgrund bort i appen) lägger till transparent kamerabakgrund."
_ "Update later with 'multicam update' (the app also tells you when a new version exists)." "Uppdatera senare med 'multicam update' (appen säger också till när en ny version finns)."
