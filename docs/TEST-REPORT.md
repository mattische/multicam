# Testrapport multicam

Körd 2026-10-11 på mbp-omarchy (Hyprland 0.56.2, DP-2 fokuserad, kameror C920 + FaceTime). Testkod: `tests/run.py`, `tests/mclib.py`.
Kommandon: `python3 tests/run.py <T-ID...>`; inspelningar skrevs till `/tmp/claude-1000/multicam-tests/` via `MULTICAM_OUTPUT_DIR` och raderades.

## Viktig begränsning i testmiljön
Under hela testkörningen var användarens session **låst** (hyprlock-liknande "Enter Password"-yta på alla monitorer, `hyprctl activewindow` = null,
skärmarna DPMS-släckta tills testerna väckte dem med `dpms on`). Konsekvenser:
- `grim` och inspelningar visar låsskärmen, inte kamerafönstren, så **alla visuella krav är inte verifierade** (form/ring/färg/transparens/ikon).
- Fönstergeometri via `hyprctl clients -j` fungerar och är verifierad. Tangentbordsfokus på TUI-fönstret kunde inte testas (inget aktivt fönster).
- Sessionen låstes inte upp (inget försök gjordes). De visuella testerna bör köras om med upplåst skärm (`tests/run.py T-D1 T-C1 T-F2`) och granskas manuellt.

## Resultat

| ID | Status | Bevis |
|---|---|---|
| T-A1 | GODKÄND | `install.sh --yes` med `HOME=/tmp/.../mc-home`: nya filer endast `~/.local/bin/multicam` (symlänk), `~/.local/share/multicam/{bin/multicam,lib/bg.py}`, `~/.local/share/applications/multicam.desktop`, tom `~/.config/multicam/` (snapshot-diff före/efter) |
| T-A3 | GODKÄND | `uninstall.sh --yes`: diff mot före-läge tomt; `Videos/keep.mp4` orörd; genvägsraden (`--keybind`, `-- multicam`) borttagen, `bindings.lua` byte-identisk |
| T-A5 | GODKÄND | md5 över fillistor för `~/.config/omarchy`, `~/.local/share/omarchy`, `/usr/bin` identiska före/efter (install skriver bara under `$HOME`) |
| T-A6 | GODKÄND | `install-bgremove --yes` (22 s, 168 MB) skapar bara `~/.local/share/multicam/bg/`; `uninstall-bgremove`: hela hemträdet identiskt med före (pip körs med `--no-cache-dir`) |
| T-B2 | GODKÄND | pty utan mus: kamera A/B, form, ring, färg (←/→ + hexkod via `C`), tjocklek, mikrofon, skrivbordsljud, skärm ändrade enbart med tangenter |
| T-B4 | GODKÄND | ändrade form/ring/färg/tjocklek, `q`, omstart: förifyllt (cirkel, ring på, #123abc, 5 px); config innehåller värdena |
| T-B5 | GODKÄND | sparad kamera "Obefintlig Kamera 9000": raden visar `av   ⚠ saknas: Obefintlig Kamera 9000`, ingen annan kamera vald, enheten bevaras i config |
| T-C1 | MANUELL | Kamerorna är mappade och placerade i förhandsvisningen innan inspelningen startas (C1 uppfylls av flödet). Bildruta vid 0,2 s extraherad (`docs/test-evidence/c1-frame-0.2s.png`) men innehåller låsskärmen: ej visuellt verifierat |
| T-C3 | GODKÄND (delvis) | `pactl get-default-source`: före=`alsa_input.usb-Generic_USB_Audio-00...`, under=`alsa_input.usb-046d_HD_Pro_Webcam_C920...`, efter=ursprungsvärdet; ljudström finns i filen. Volymmätning (ffmpeg) av vilken källa som spelades in gjordes inte |
| T-C4 | GODKÄND | `ffprobe`: h264 + aac, mp4, längd 9,10 s resp. 7,70 s för ca 8 s inspelning |
| T-C4b | GODKÄND | filnamn matchar regex `^screenrecording-...-HH_MM_SS\.mp4$`; Omarchys `_`/`-`-namn finns inte kvar; förskapad krockfil orörd, ny fick `-2` |
| T-C5 | MANUELL | Resultatskärmen visar filnamn och frågan "Öppna i omacut? [J/n]"; start av omacut (`setsid -f omacut FIL`) ej testad (M) |
| T-D1 | MANUELL | Form: cirkel = kvadratiskt fönster + `rounding = storlek/2` via `set_prop` (verifierat i `hyprctl clients -j`: 240x240 resp. 426x240 för 16:9). Utseende (rund/ring) ej verifierat visuellt: skärmen låst |
| T-D2 | MANUELL | Färgval via hexkod (T-B2/T-B4), färgrad, och stub-`hyprpicker` (T-D2c) sparas per kamera i config; själva kantens färg/tjocklek på skärmen ej verifierad (låst) |
| T-D2c | GODKÄND | `hyprpicker` ersatt med stub i PATH: anropad med `-f hex`, färg `#12ab34` satt och sparad (verklig pipett kräver musklick: M) |
| T-D3/4 | GODKÄND | pty + `hyprctl clients -j`: flytt 20/100 px, `+ - PgUp PgDn` ±10 %, storleksläge ±10/25 %, min 120, max 1170 (skärmhöjd), klamring mot skärmkant, statusraden visar `[FLYTTA]`/`[STORLEK]` (±1 px) |
| T-D5 | GODKÄND | Siffror 1–9 snappar till numpad-layout (±1 px) |
| T-D7 | MANUELL | Inget aktivt fönster fanns (låst session, `activewindow` = null före och efter); `T-D7b` (riktigt foot-fönster med fifo-stdin) kunde inte få fokus. Mekanismen: regel `no_initial_focus=true` |
| T-D8 | GODKÄND | Stand-in `mpv` med klass `WebcamOverlay-medium` + titel `WebcamOverlay` (riktiga overlayn skulle ta samma kamera): oförändrad geometri/float/pin före och efter multicam-åtgärder; lever kvar efter multicam-exit |
| T-E1 | GODKÄND | `q`+`j` under inspelning, och `Esc` i förhandsvisning: inga Multicam-fönster, regler (`hyprctl rules -j`), egna mpv/python kvar; mic återställd |
| T-E2 | GODKÄND | Ctrl+C, SIGHUP (stängd terminal), SIGTERM: fönster/mpv borta efter 0,23 s; `omarchy-capture-screenrecording --stop-recording` utifrån: borta efter 0,23 s och TUI visar resultat; filer korrekt namngivna |
| T-E3 | MANUELL | `gpu-screen-recorder` kör under inspelning (Omarchys ikon beror på det); `omarchy-shell -q omarchy.indicators refresh` rc=0. Ikon/klick ej verifierat (låst skärm, musklick) |
| T-E4 | GODKÄND | SIGTERM mot `gpu-screen-recorder`: vakten stänger fönster/mpv på 0,23 s, filen byter namn, TUI visar resultat |
| T-E5 | GODKÄND | Utomstående `mpv` (titel ANNANMPV) lever och har kvar sitt fönster efter multicam start+exit |
| T-F2 | MANUELL (fps GODKÄND) | `bg.py --threads 2`, C920 640x360, 15,6 s: 424 RGBA-rutor = **27,2 fps** (≥25). CPU ca 149 % av en kärna (python+ffmpeg+ORT-trådar), alltså över "en kärna". TUI med bg=på: python+mpv startar via fifo, fönster mappas, allt städas vid `q`. Genomskinlig bakgrund/skrivbord synligt ej verifierat (låst skärm) |
| T-F3 | GODKÄND | Korrupt modell via `MULTICAM_MODEL_URL=file://...`: rc=2, modellfilen raderad, "SHA256-kontrollen misslyckades". Ändrad installerad modell: `check-bgremove` rc=1; TUI använder då ingen bg (visar varning) |
| T-X1 | GODKÄND (delvis) | Två kameror (C920 cirkel + FaceTime rektangel, ring) + mic, 30 s: längd 30,6 s, 1834 bildrutor (59,9 fps av 60), `ffmpeg -f null` avkodar utan fel. Att kamerabilderna syns i filen ej verifierat (låst skärm) |
| T-X2 | GODKÄND | Två körningar i rad: inga rester (fönster/regler/processer/mic), två filer med olika namn, `/run/user/1000/multicam` tomt efter exit |

## Avvikelser från spec
- Förinställda färger: ←/→ fungerar i formuläret, men på inspelningsskärmen ligger de på `p`/`P` (pilarna flyttar/storleksändrar). Dokumenterat i README.
- Rektangel är 16:9 (storlek = höjd, bredd = höjd*16/9); cirkel är kvadratisk.
- Flödet har ett förhandsvisningssteg: F5 visar kamerorna, `Enter` startar inspelningen (kamerorna finns alltså i bild från första bildrutan).
- TUI-fönstret startas med app-id `TUI.float` (matchar Omarchys befintliga flytande-regel) i stället för `multicam`; ingen konfigändring behövs.
- Genväg (valfri): `SUPER + ALT + M` (fri i Omarchys standardbindningar).
- `--alpha` finns inte i den installerade mpv; transparens förlitar sig på `--background-color=#00000000` (verifierat att pipelinen startar, ej visuellt).
- Fönsterstorlek: `mpv --no-config` används för reproducerbarhet.
- Python-miljön blev 168 MB, inte 300 MB.

## Ej verifierat
Allt visuellt (T-D1, T-D2 utseende, T-C1 bildinnehåll, T-E3 ikon/klick, T-F2 transparens), fokus på TUI-fönstret (T-D7), omacut-start (T-C5), äkta hyprpicker-klick,
volymmätning av vald mic, val av annan skärm än den fokuserade (koden finns men testades inte), foot som terminal med verklig tangentbordsinmatning.
