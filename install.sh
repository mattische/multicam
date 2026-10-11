#!/bin/bash
# multicam - installation. Inga roträttigheter, inga paket installeras.
# Flaggor: --yes (inga frågor, ingen genväg), --keybind (lägg in genväg), --no-keybind
SRC=$(cd "$(dirname "$(readlink -f "$0")")" && pwd)
DATA=$HOME/.local/share/multicam
BIN=$HOME/.local/bin/multicam
APPS=$HOME/.local/share/applications
BINDINGS=$HOME/.config/hypr/bindings.lua
KEYCOMBO="SUPER + ALT + M"
yes=0; kb=ask
for a in "$@"; do
  case $a in
    --yes | -y) yes=1 ;;
    --keybind) kb=yes ;;
    --no-keybind) kb=no ;;
    *) echo "Okänd flagga: $a" >&2; exit 2 ;;
  esac
done

missing=()
for c in hyprctl jq mpv pactl gpu-screen-recorder omarchy-capture-screenrecording omarchy-launch-tui; do
  command -v "$c" >/dev/null || missing+=("$c")
done
if ((${#missing[@]})); then
  echo "Saknade beroenden (installera själv, inget installeras här): ${missing[*]}" >&2
  exit 1
fi
for c in v4l2-ctl hyprpicker omacut grim; do
  command -v "$c" >/dev/null || echo "Obs: valfritt program saknas: $c"
done

install -Dm755 "$SRC/bin/multicam" "$DATA/bin/multicam"
install -Dm644 "$SRC/lib/bg.py" "$DATA/lib/bg.py"
mkdir -p "$HOME/.local/bin" "$APPS" "$HOME/.config/multicam"
ln -sfn "$DATA/bin/multicam" "$BIN"
sed "s|@BIN@|$BIN|" "$SRC/multicam.desktop" >"$APPS/multicam.desktop"

if [[ $kb == ask && $yes == 0 && -t 0 ]]; then
  read -r -p "Lägg in genvägen $KEYCOMBO i ~/.config/hypr/bindings.lua? [j/N] " a
  [[ $a == [jJyY]* ]] && kb=yes
fi
if [[ $kb == yes ]]; then
  if [[ ! -f $BINDINGS ]]; then
    echo "Hittade inte $BINDINGS - ingen genväg inlagd."
  elif grep -q -- '-- multicam$' "$BINDINGS"; then
    echo "Genvägen finns redan."
  elif grep -q "\"$KEYCOMBO\"" "$BINDINGS"; then
    echo "$KEYCOMBO används redan i $BINDINGS - ingen genväg inlagd."
  else
    printf 'o.bind("%s", "Multicam", "omarchy-launch-tui --app-id=TUI.float %s") -- multicam\n' "$KEYCOMBO" "$BIN" >>"$BINDINGS"
    echo "Genväg $KEYCOMBO inlagd (raden slutar med '-- multicam')."
  fi
fi

echo "Multicam installerat: $BIN"
echo "Valfritt: 'multicam install-bgremove' för bakgrund bort."
