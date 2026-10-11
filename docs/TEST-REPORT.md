# Testrapport multicam

Körd 2026-10-11 på mbp-omarchy (Hyprland 0.56.2; DP-1 3840x2160 fokuserad, DP-2 roterad 1200x1920, kameror C920 + FaceTime).
Testkod: `tests/run.py` + `tests/mclib.py` (automatiska) och `tests/visual.py` (visuella, bilderna granskas av människa/agent).
Inspelningar skrevs till `/tmp/claude-1000/multicam-tests/` via `MULTICAM_OUTPUT_DIR` och raderades.

Version 2 av rapporten: efter oberoende verifiering fixades sex buggar (se nedan) och testerna skärptes. Skärmen var låst under
första körningen; den låstes sedan upp och de visuella testerna kördes på riktigt (bilderna i `docs/test-evidence/` är granskade).
Obs: bilderna innehåller användarens webbkamerabild och skärminnehåll vid testögonblicket (privat repo).

## Buggfixar (verifieringsrunda)
1. `install.sh`: lägger radbrytning före genvägsraden; `uninstall` tar bort bara bind-raden även om den smält ihop med en kommentar. Test T-A4.
2. Städning: vakten (`multicam --watch <sessionkatalog> <tui-pid>`) bevakar nu även TUI-processen och en `quit`-flagga, och stoppar inspelningen
   själv om TUI:t försvinner; Omarchys stoppskript (Alt+Print/klick/`--stop-recording`) städar kamerorna direkt. Stopp körs under lås (en gång).
   Trap-hanterare: SIGPIPE ignoreras, utskrift stängs efter HUP, långa förgrundsanrop (start av inspelning, hyprpicker) körs i bakgrunden + `wait`
   så att signaler hanteras direkt. Körfiler ligger per session i `$XDG_RUNTIME_DIR/multicam/s.<pid>/` (ingen delad state mellan sessioner).
3. Skärmval: fokuserad monitor och TUI-fönstret (via pid-kedjan, annars aktivt fönster) återställs efter att inspelningen startat. Roterade skärmar (transform) hanteras (DP-2).
4. `resolve_saved`: exakt träff på sökväg+namn först, sedan namn bland oanvända enheter; två likadana kameror slås inte ihop. Test T-B5b.
5. Kameraupplösning: vanlig kamera 1280x720 (MJPEG om enheten klarar >=25 fps i MJPG, annars YUYV/NV12), annars 640x360/640x480; bg-borttagning 640x360 först.
   Mätning: C920 ger just nu ~15 fps i alla lägen (640x360 YUYV/MJPG, 1280x720 MJPG) = kamerans dynamiska bildfrekvens i svagt ljus (`exposure_dynamic_framerate=1`), inte format. FaceTime 1280x720 NV12: 30 fps.
6. README: `git clone ... && ./install.sh` först, och körfiler i `$XDG_RUNTIME_DIR/multicam`.

## Resultat

| ID | Status | Bevis |
|---|---|---|
| T-A1 | GODKÄND | `install.sh --yes` mot HOME-kopia med riktiga `~/.config/hypr`, `~/.config/omarchy`, `~/.local/share/omarchy` (cp -a): nya sökvägar exakt == `.config/multicam`, `.local/bin/multicam`, `.local/share/applications/multicam.desktop`, `.local/share/multicam/bin/multicam`, `.local/share/multicam/lib/bg.py` |
| T-A3 | GODKÄND | `uninstall.sh --yes`: `diff -r --no-dereference` mellan orörd kopia och hemträdet tomt (inkl. Videos/keep.mp4) |
| T-A4 | GODKÄND | bindings.lua utan avslutande newline: genvägen hamnar på egen rad; uninstall tar bort bara den (även ihopsmält med kommentar), andra rader orörda |
| T-A5 | GODKÄND | `diff -r` före/efter install och uninstall av kopior av ~/.config/hypr, ~/.config/omarchy, ~/.local/share/omarchy tomt; `/usr/bin` fillista+md5 oförändrad. Körs mot HOME-kopia, aldrig verkligt HOME |
| T-A6 | GODKÄND | `install-bgremove --yes` (22 s, 168 MB) skapar bara `~/.local/share/multicam/bg/`; `uninstall-bgremove` ger identiskt hemträd (pip `--no-cache-dir`). Körd före buggfixarna; koden i install-bgremove är oförändrad |
| T-B2 | GODKÄND | pty utan mus: alla rader ändrade med pilar/Enter/`C` |
| T-B4 | GODKÄND | form/ring/färg/tjocklek sparas och förifylls vid omstart |
| T-B5 | GODKÄND | saknad kamera: `av   ⚠ saknas: Obefintlig Kamera 9000`, ingen tyst ersättning, enheten bevaras i config |
| T-B5b | GODKÄND | två "Twin Cam" (video4/video6, stub av `omarchy-capture-webcam-list`): A=video6 och B=video4 bevaras exakt, ingen sammanslagning |
| T-C1 | GODKÄND (granskad bild) | `docs/test-evidence/c1-frame-0.2s.png`: ffmpeg-bildruta vid 0,2 s i inspelningen visar skrivbordet med båda kamerorna redan på plats: rund bild (C920) med rosa ring till vänster och rektangulär bild (FaceTime) med blå ring i mitten |
| T-C3 | GODKÄND | `pactl get-default-source`: före=Generic USB, under=C920-mic, efter=Generic USB |
| T-C3v | GODKÄND | ffmpeg volumedetect mean_volume per vald mic (5 s var): C920 -16,0 dB, Generic USB -83,3 dB, iD14 -91,0 dB; default-source under inspelning var vald mic i alla tre. Skillnad C920/Generic = 67 dB |
| T-C4 | GODKÄND | ffprobe: h264+aac, mp4; längd 7,70 s mot uppmätt recorder-start->stopp 7,59 s minus 0,1 s trim = 7,49 s (±0,5 s) |
| T-C4b | GODKÄND | namn matchar regex; Omarchys `_`/`-`-namn finns inte kvar; förskapad krockfil orörd, ny fick `-2`, Omarchys namn borta ur katalogen |
| T-C5 | MANUELL | resultatskärmen visar filnamn + "Öppna i omacut? [J/n]" (visat i pty); start av omacut ej körd |
| T-D1 | GODKÄND (granskade bilder) | `d1-circle-ring-red8.png`: rund kamerabild med jämn röd ring (8 px) som följer cirkeln; `d1-rect-ring-green8.png`: 16:9-rektangel med grön ring längs kanten; `d1-circle-noring.png`: rund bild utan ring (kanten klippt rund mot terminalen bakom) |
| T-D2 | GODKÄND (granskade bilder, utom hyprpicker-klick) | färgerna (röd/grön/blå/gul) syns som valda; `d2-circle-thick2.png` (tunn gul ring) mot `d2-circle-thick12.png` (tjock gul ring) visar tjocklek; ring följer cirkel resp. rektangel. Hexkod/färgrad sparas per kamera (T-B2/T-B4). Verkligt hyprpicker-klick: M (stub verifierad i T-D2c) |
| T-D2c | GODKÄND | stub-`hyprpicker` anropas med `-f hex`, färgen `#12ab34` sätts och sparas |
| T-D3/4 | GODKÄND | geometri via `hyprctl clients -j` (±1 px): flytt 20/100 px, ±10 %/±25 %, min 120, max = skärmens kortsida (1320 på DP-1), klamring mot alla fyra kanter (x=MX, y=MY, x+w=MX+MW, y+h=MY+MH), förstoring i hörn skjuter inte ut bilden, statusrad `[FLYTTA]`/`[STORLEK]` |
| T-D5 | GODKÄND | båda kameror: Tab och Shift-Tab växlar (statusraden "Vald kamera"), 1/5 på A och 9 på B hamnar rätt, den andra kameran rörs inte |
| T-D7 | GODKÄND | `hyprctl activewindow` oförändrad (0x55c2...) efter kamerastart och åtgärder (pty utan eget terminalfönster) |
| T-D7b | GODKÄND | riktig terminal: `omarchy-launch-tui --app-id=TUI.float env HOME=<temp> multicam`, tangenter via `wtype` (F5, Right, Down, s, r, PageUp, 1, m, Up) med kontroll före varje tangent att aktivt fönster == TUI; fokus låg kvar på TUI efter varje åtgärd och efter att kamerafönstren dök upp; `q` stängde fönstret, inga kameror/regler kvar |
| T-D8 | GODKÄND | stand-in `WebcamOverlay-medium` (mpv testsrc, samma klass/titel) oförändrad geometri/float/pin; lever kvar efter multicam-exit. Äkta overlay ej använd (kameran är upptagen) |
| T-D9 | GODKÄND | `SCREEN=DP-2` medan DP-1 fokuserad: filen 1200x1920 (DP-2 är roterad), fokuserad monitor före=efter=DP-1, aktivt fönster före=efter |
| T-E1 | GODKÄND | `q`+`j` under inspelning, `Esc` i förhandsvisning: inga fönster/regler/mpv kvar, mic återställd. Regelkontroll via sondfönster med klass MulticamA (float+pin om regeln är aktiv); positiv kontroll bekräftad under körning |
| T-E2 | GODKÄND | Ctrl+C 0,21 s, SIGHUP 0,10 s, SIGTERM 0,69 s, `--stop-recording` utifrån < 1 s (alla < 1,0 s i två körningar), filer omdöpta |
| T-E2s | GODKÄND | 10 x HUP / INT / TERM under inspelning, krav < 1,0 s till fönster+mpv+mic städat, inspelaren stoppad och filen omdöpt: slutlig körning HUP max 0,71 s, INT max 0,85 s, TERM max 0,75 s, 30/30 ok (första körningen före sista trimningen: max 0,91 s, 30/30). Marginalen mot 1 s är liten på en belastad maskin |
| T-E3 | GODKÄND (granskade bilder; stopp via kommando, inget musklick) | `e3-bar.png` under inspelning: Omarchys punkt-i-cirkel-ikon syns till vänster om klockan; `e3-bar2.png` efter `omarchy-capture-screenrecording --stop-recording`: ikonen borta. Verkligt musklick på ikonen: M |
| T-E4 | GODKÄND | SIGTERM mot gpu-screen-recorder: fönster/mpv borta på 0,24 s, filen omdöpt, TUI visar resultat |
| T-E5 | GODKÄND | utomstående mpv (titel ANNANMPV) lever med fönster kvar efter multicam start+exit |
| T-F2 | GODKÄND (fps) / GODKÄND (transparens, granskad bild) | `bg.py --threads 2`, C920 640x360: 27,2 fps (≥25), CPU ca 149 % av en kärna (python+ffmpeg+ORT) = över "en kärna". `f2-bg-transparent.png`: personen friläggd, terminaltexten bakom syns genom bakgrunden och delvis genom mörka kläder (F4: mjuka kanter/genomskinliga mörka kläder) |
| T-F3 | GODKÄND | korrupt modell via `MULTICAM_MODEL_URL`: rc=2, filen raderad; ändrad installerad modell: `check-bgremove` rc=1 |
| T-X1 | GODKÄND | två kameror + cirkel + mic, 30 s: 32,0 s, 1917 bildrutor (59,9 fps), avkodning utan fel; `x1-frame-4s.png` (granskad) visar båda kamerabilderna med ringar i inspelningen |
| T-X2 | GODKÄND | två körningar i rad: inga rester, två olika filnamn, `$XDG_RUNTIME_DIR/multicam` tomt efter exit |

## Avvikelser från spec
- Förinställda färger: ←/→ i formuläret som spec, men `p`/`P` på inspelningsskärmen (pilarna flyttar/storleksändrar).
- Rektangel 16:9 (storlek = höjd); cirkel kvadratisk.
- Förhandsvisningssteg: F5 visar kamerorna, `Enter` startar inspelningen.
- TUI-fönstret använder app-id `TUI.float` (Omarchys befintliga flytande-regel).
- Valfri genväg `SUPER + ALT + M`.
- mpv saknar `--alpha`; transparens verifierad visuellt utan den.
- `mpv --no-config`. Python-miljön 168 MB.
- `hyprctl rules -j` finns inte: regelkontrollen sker via sondfönster.

## Ej verifierat
- Verkligt musklick på bar-ikonen och verkligt hyprpicker-klick (kräver mus).
- Öppning av omacut från resultatskärmen (T-C5).
- Äkta Omarchy WebcamOverlay parallellt (kameran upptagen; stand-in användes).
- Terminaler andra än foot; kamerafps i bra ljus (C920 gav 15 fps p.g.a. dynamisk bildfrekvens i svagt ljus).
