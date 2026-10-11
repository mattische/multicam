#!/bin/bash
# kbd-proto.sh - keyboard control prototype for multicam TUI. bash+jq+hyprctl+mpv only.
# env: MC_MON=DP-1  MC_N=1|2  MC_DEV=/dev/video0  MC_LOG=file (state log after every key)
MON=${MC_MON:-DP-1}; N=${MC_N:-2}; DEV=${MC_DEV:-/dev/video0}; LOG=${MC_LOG:-}
STEP=20; BIG=100; MARGIN=20; MINS=120
declare -A X Y S SHAPE RING
IDS=(A B); SEL=0; MPVPIDS=(); CLEANED=0; STTY=$(stty -g 2>/dev/null)

hc(){ hyprctl "$@" >/dev/null 2>&1; }

cleanup(){
  (( CLEANED )) && return; CLEANED=1
  trap '' INT TERM HUP
  for id in "${IDS[@]:0:$N}"; do
    hc dispatch "hl.dsp.window.close({ window = \"class:^Multicam$id\$\" })"
    hc eval "MC_$id:set_enabled(false)"
  done
  sleep 0.3
  for p in "${MPVPIDS[@]}"; do kill "$p" 2>/dev/null; done   # only the pids we started
  [[ -n $STTY ]] && stty "$STTY" 2>/dev/null
  printf '\e[?25h\n'
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP

# monitor bounds (logical px, global), minus reserved bars
read -r MX MY MW MH < <(hyprctl monitors -j | jq -r --arg n "$MON" '.[]|select(.name==$n)|
  "\(.x+.reserved[0]) \(.y+.reserved[1]) \(((.width/.scale)-.reserved[0]-.reserved[2])|floor) \(((.height/.scale)-.reserved[1]-.reserved[3])|floor)"')
[[ -z $MW ]] && { echo "monitor $MON not found"; exit 1; }
MAXS=$(( (MW<MH?MW:MH) ))

clamp(){ # clamp id
  local i=$1 s=${S[$1]}
  (( s>MAXS )) && s=$MAXS; (( s<MINS )) && s=$MINS; S[$i]=$s
  (( X[$i] < MX )) && X[$i]=$MX; (( Y[$i] < MY )) && Y[$i]=$MY
  (( X[$i]+s > MX+MW )) && X[$i]=$((MX+MW-s)); (( Y[$i]+s > MY+MH )) && Y[$i]=$((MY+MH-s))
}

apply(){ # apply id  (one batched hyprctl call)
  local i=$1 s=${S[$1]} r=0 b=0 w="class:^Multicam$1\$"
  [[ ${SHAPE[$i]} == circle ]] && r=$((s/2))
  [[ ${RING[$i]} == on ]] && b=4
  hyprctl --batch "dispatch hl.dsp.window.resize({ window = \"$w\", x = $s, y = $s }); \
dispatch hl.dsp.window.move({ window = \"$w\", x = ${X[$i]}, y = ${Y[$i]} }); \
dispatch hl.dsp.window.set_prop({ window = \"$w\", prop = \"rounding\", value = $r }); \
dispatch hl.dsp.window.set_prop({ window = \"$w\", prop = \"border_size\", value = $b }); \
dispatch hl.dsp.window.set_prop({ window = \"$w\", prop = \"inactive_border_color\", value = \"rgba(ff3399ff)\" }); \
dispatch hl.dsp.window.set_prop({ window = \"$w\", prop = \"active_border_color\", value = \"rgba(ff3399ff)\" })" >/dev/null 2>&1
}

preset(){ # preset id n  (numpad layout: 7 8 9 / 4 5 6 / 1 2 3)
  local i=$1 n=$2 s=${S[$1]} col row
  col=$(( (n-1)%3 )); row=$(( 2-(n-1)/3 ))   # row 0=top
  X[$i]=$(( MX + MARGIN + col*(MW-2*MARGIN-s)/2 ))
  Y[$i]=$(( MY + MARGIN + row*(MH-2*MARGIN-s)/2 ))
}

status(){
  local i=${IDS[$SEL]}
  printf '\r\e[2K[%s] x=%d y=%d size=%d %s ring=%s  (mon %s %dx%d @%d,%d)' "$i" "${X[$i]}" "${Y[$i]}" "${S[$i]}" "${SHAPE[$i]}" "${RING[$i]}" "$MON" "$MW" "$MH" "$MX" "$MY"
  [[ -n $LOG ]] && echo "$i ${X[$i]} ${Y[$i]} ${S[$i]} ${SHAPE[$i]} ${RING[$i]}" >> "$LOG"
}

# --- start windows ---
for k in $(seq 0 $((N-1))); do
  id=${IDS[$k]}
  S[$id]=300; SHAPE[$id]=rect; RING[$id]=off
  X[$id]=$(( k==0 ? MX+MARGIN+800 : MX+MARGIN+1300 )); Y[$id]=$(( MY+400 ))
  hc eval "MC_$id = hl.window_rule({name=\"multicam-$id\", match={class=\"^Multicam$id\$\"}, float=true, pin=true, no_initial_focus=true, border_size=0, no_dim=true, size={300,300}})"
  if (( k==0 )); then src="av://v4l2:$DEV"; opts=(--demuxer-lavf-o=video_size=640x480,framerate=30)
  else src="av://lavfi:testsrc2=size=480x480"; opts=(); fi    # 2nd window: synthetic (only one real cam allowed)
  mpv "$src" --profile=low-latency --untimed --no-cache "${opts[@]}" '--vf=lavfi=[crop=ih:ih]' \
    --title="Multicam$id" --wayland-app-id="Multicam$id" --no-border --no-audio --no-osc \
    --osd-level=0 --no-input-default-bindings --really-quiet &>/dev/null &
  MPVPIDS+=($!)
done
for i in $(seq 100); do   # wait until mapped
  c=$(hyprctl clients -j | jq '[.[]|select(.class|test("^Multicam[AB]$"))]|length'); (( c>=N )) && break; sleep 0.1
done
for id in "${IDS[@]:0:$N}"; do clamp $id; apply $id; done

# --- key loop ---
printf '\e[?25l'
status
while :; do
  IFS= read -rsn1 k || break       # EOF (stdin closed / hangup) -> exit
  seq=$k
  if [[ $k == $'\e' ]]; then
    if IFS= read -rsn1 -t 0.05 c; then
      seq+=$c
      if [[ $c == '[' || $c == 'O' ]]; then       # CSI/SS3: read until final byte
        while IFS= read -rsn1 -t 0.05 c; do seq+=$c; [[ $c == [@-~] ]] && break; done
      fi
    fi
  fi
  [[ -n ${MC_SEQLOG:-} ]] && printf '%q\n' "$seq" >> "$MC_SEQLOG"
  i=${IDS[$SEL]}; d=0
  case $seq in
    $'\t') SEL=$(( (SEL+1)%N )); status; continue ;;
    $'\e[A'|$'\eOA') Y[$i]=$((Y[$i]-STEP)) ;;  $'\e[B'|$'\eOB') Y[$i]=$((Y[$i]+STEP)) ;;
    $'\e[C'|$'\eOC') X[$i]=$((X[$i]+STEP)) ;;  $'\e[D'|$'\eOD') X[$i]=$((X[$i]-STEP)) ;;
    $'\e[1;2A') Y[$i]=$((Y[$i]-BIG)) ;; $'\e[1;2B') Y[$i]=$((Y[$i]+BIG)) ;;
    $'\e[1;2C') X[$i]=$((X[$i]+BIG)) ;; $'\e[1;2D') X[$i]=$((X[$i]-BIG)) ;;
    '+'|'='|$'\e[5~') d=1 ;;  '-'|$'\e[6~') d=-1 ;;
    s) [[ ${SHAPE[$i]} == circle ]] && SHAPE[$i]=rect || SHAPE[$i]=circle ;;
    r) [[ ${RING[$i]} == on ]] && RING[$i]=off || RING[$i]=on ;;
    [1-9]) preset $i $seq ;;
    q|$'\e') break ;;
    *) continue ;;
  esac
  if (( d )); then   # resize 10% around centre
    old=${S[$i]}; new=$(( old + d*old/10 )); (( d>0 && new==old )) && new=$((old+1))
    (( new<MINS )) && new=$MINS; (( new>MAXS )) && new=$MAXS
    X[$i]=$(( X[$i] + (old-new)/2 )); Y[$i]=$(( Y[$i] + (old-new)/2 )); S[$i]=$new
  fi
  clamp $i; apply $i; status
done
exit 0
