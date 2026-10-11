# multicam – kravspecifikation (v1, utkast)

Status: förslag, inget är byggt ännu. Underlag: tester på användarens dator (Omarchy, Hyprland 0.56.2, quickshell-fält).
Varje krav har ett ID. Varje krav har ett test (T-ID) som ska kunna köras och rapporteras som GODKÄND / UNDERKÄND.

## 1. Syfte
Ett litet tillägg till Omarchy som spelar in skärm + upp till två kameror + vald mikrofon till en vanlig MP4-fil,
med kamerorna som flytande bilder (rektangel eller cirkel) som kan flyttas och skalas med tangentbordet.
Bygger på `omarchy-capture-screenrecording` (ersätter bara `...-with-webcam`). Ändrar inget i /usr eller i Omarchys filer.

## 2. Krav

### A. Installation och borttagning
- A1. Installation med ett kommando: `./install.sh`. Inga roträttigheter. Inga paket installeras (kontrollerar bara beroenden och säger vad som saknas).
- A2. Allt som installeras ligger på kända platser: `~/.local/bin/multicam`, `~/.local/share/multicam/`, `~/.config/multicam/`, `~/.local/share/applications/multicam.desktop`. Inget annat.
- A3. Borttagning med ett kommando: `multicam uninstall` (eller `./uninstall.sh`). Tar bort allt i A2 efter bekräftelse. Inspelningar i Videos rörs aldrig.
- A4. Valfri genväg läggs bara in om användaren väljer det, i `~/.config/hypr/` via en tydligt märkt rad som uninstall tar bort.
- A5. Ingen systemd-tjänst, inga ändringar i `shell.json`, ingen ändring av Omarchys filer.
- A6. Bakgrundsborttagning (se F) installeras separat med `multicam install-bgremove` och tas bort med `multicam uninstall-bgremove` (en mapp).

### B. Start och användning
- B1. Starta från programmenyn ("Multicam") eller `multicam`. Öppnas som TUI i ett flytande terminalfönster (`omarchy-launch-tui`).
- B2. TUI:t kan styras helt med tangentbordet. Ingen funktion kräver mus.
- B3. Formulär: kamera A, kamera B (var och en "av" eller en enhet, samma enhet kan inte väljas två gånger), mikrofon (lista eller "ingen"), skrivbordsljud på/av, form (rektangel/cirkel) per kamera, ring på/av, bakgrund bort på/av per kamera (om tillägget finns), skärm att spela in (den fokuserade som standard).
- B4. Senaste val sparas i `~/.config/multicam/config` och förifylls nästa gång.
- B5. Kamera- och mikrofonlistor läses vid start. Saknas en sparad enhet markeras den tydligt och väljs aldrig om i tysthet.

### C. Inspelning
- C1. Kamerorna startas före inspelningen och finns med från första bildruta.
- C2. Inspelningen startas med `omarchy-capture-screenrecording --fullscreen` (plus `--with-microphone-audio`, `--with-desktop-audio` efter val). Ingen `--with-webcam`.
- C3. Vald mikrofon sätts som systemets standardmikrofon före start. Ursprungsvärdet återställs alltid vid slut, krasch och avbrott.
- C4. Resultatet är en MP4 (h264 + AAC) i `~/Videos`. Filnamn: `screenrecording-ÅÅÅÅ-MM-DD-TT_MM_SS.mp4` (exempel `screenrecording-2026-10-11-15_01_17.mp4`). Omarchy skriver sitt eget namn (`ÅÅÅÅ-MM-DD_TT-MM-SS`); multicam byter namn på filen först när Omarchys slutbehandling (trimning, ljudutjämning, förhandsbild) är klar. Namnbytet får inte krocka med befintlig fil (vid krock läggs `-2` till). Omarchys förhandsbild (`-preview.png`) lämnas som den är.
- C5. Efter inspelning visas filnamnet, och användaren erbjuds att öppna den i **omacut** (förinstallerad videoredigerare).

### D. Kamerabilder (under inspelning och förhandsvisning)
- D1. Formen är rektangel eller cirkel, valbar per kamera. Cirkel = kvadratisk bild (1:1-beskärning) + Hyprland-rundning = halva sidan, omsatt efter varje storleksändring.
- D2. Valfri kant runt kameran, följer formen (cirkel/rektangel). Färg väljs per kamera på tre sätt: `c` startar `hyprpicker` (klicka på valfri pixel på skärmen), `C` låter användaren skriva en hexkod (`#rrggbb`), och en rad med åtta färdiga färger bläddras med ←/→. Tjocklek 1–12 px med `[` och `]` (standard 4). Färg och tjocklek sparas per kamera i konfigurationen. Kanten är Hyprlands fönsterram (`set_prop border_size` / `inactive_border_color`), ritas inuti fönstret och ändrar inte bildens storlek.
- D3. Storlek ändras med `+`/`-` och PgUp/PgDn (±10 % runt mitten) i båda lägena, samt med piltangenterna i storleksläge (se D4). Minst 120 px, högst skärmens höjd.
- D4. Piltangenterna har två lägen som växlas med `m`. Flyttläge (standard): pil flyttar vald kamera 20 px, Shift+pil 100 px. Storleksläge: ↑/→ större och ↓/← mindre (±10 %, Shift ±25 %), runt bildens mitt. Aktuellt läge visas alltid i statusraden som `[FLYTTA]` eller `[STORLEK]`. Bilden hålls alltid inom skärmen.
- D5. Tab växlar vald kamera. Siffertangenterna 1–9 snappar till hörn/kant/mitt (numpad-layout).
- D6. `s` växlar cirkel/rektangel, `r` kant på/av, `c`/`C` kantfärg, `[`/`]` kanttjocklek, `m` flytta/storlek, `b` bakgrund bort på/av.
- D7. Fönstren öppnas flytande, fastnålade, utan ram, utan fokus (TUI:t behåller tangentbordsfokus).
- D8. Kamerafönstren har egen klass (`MulticamA`, `MulticamB`) och påverkas inte av Omarchys WebcamOverlay-regler.

### E. Avsluta
- E1. `q` eller Esc i TUI:t avslutar: stoppar inspelningen om den pågår (efter bekräftelse), stänger kamerafönster, tar bort fönsterregler, återställer mikrofon.
- E2. Samma städning vid Ctrl+C, vid stängt terminalfönster och när inspelningen stoppas utifrån (Alt+Print eller klick i fältet).
- E3. Ikonen i mitten av fältet: multicam använder Omarchys befintliga inspelningsikon (prick i cirkel till vänster om klockan). Den visas automatiskt eftersom `gpu-screen-recorder` kör, och ett klick stoppar inspelningen. Multicam anropar `omarchy-shell -q omarchy.indicators refresh` vid start och stopp. Ingen egen plugin och ingen ändring av `shell.json`.
- E4. En bakgrundsvakt (startas först när inspelaren bekräftats köra) städar allt när `gpu-screen-recorder` försvinner.
- E5. Multicam stänger bara sina egna fönster och processer (via klass och sparade PID), aldrig med `pkill mpv`.

### F. Bakgrund bort (valfritt tillägg)
- F1. Per kamera ett val i TUI:t. Visas bara om tillägget är installerat.
- F2. Pipeline: kamera → ONNX-modell (Robust Video Matting mobilenetv3) → RGBA → `mpv` med genomskinlig bakgrund. Mål ≥ 25 fps på en kärna (1–2 trådar).
- F3. Installeras i egen Python-miljö under `~/.local/share/multicam/bg/`. Modellen laddas ner från projektets officiella release och verifieras med fast SHA256 (88d45312…2828).
- F4. Känd kvalitet: mjuka kanter, mörka kläder delvis genomskinliga. Dokumenteras i hjälptexten (inte ett fel).
- F5. Licensnotis (GPL-3.0 för RVM) visas vid installation.

### G. Icke-krav
- Scenbyte under inspelning, fler än två kameror, musstyrning, egen klippeditor, ljudmixer.

## 3. Tester (ska köras och rapporteras)
Alla testkörningar ska städa efter sig. Tester markerade (M) kräver att användaren själv tittar/klickar.

| ID | Krav | Test | Förväntat |
|---|---|---|---|
| T-A1 | A1,A2 | Kör install.sh på ren användare (eller med tom HOME-kopia) | Bara filerna i A2 skapas; `diff` före/efter bekräftar |
| T-A3 | A3 | uninstall.sh därefter | Alla filer borta, Videos orört, `diff` mot före-läge tomt |
| T-A5 | A5 | `diff -r` av `~/.config/omarchy`, `/usr`, `~/.local/share/omarchy` före/efter install | Ingen skillnad |
| T-A6 | A6 | install-bgremove, sedan uninstall-bgremove | En mapp skapad/borttagen |
| T-B2 | B2 | Driv hela TUI:t med `wtype`/pty utan mus | Alla val nåbara och ändringsbara |
| T-B4 | B4 | Ändra val, avsluta, starta om | Val förifyllda |
| T-B5 | B5 | Sätt sparad kamera till obefintlig enhet | Tydlig varning, ingen tyst ersättning |
| T-C1 | C1 | Spela in 8 s, extrahera bild vid 0,2 s | Kameror syns redan vid första bildrutorna |
| T-C3 | C3 | Välj annan mic, spela in, kontrollera `pactl get-default-source` före/under/efter | Återställd; volymmätning (ffmpeg) visar vald källa |
| T-C4 | C4 | `ffprobe` på resultatet | MP4, h264 + AAC, längd ±0,5 s |
| T-C5 | C5 | Välj "öppna i omacut" | omacut startar med filen (M) |
| T-D1 | D1,D2 | Skärmdump i cirkel, rektangel, med/utan ring (grim, Read) | Rund/fyrkantig/ring som förväntat; samma i inspelad bildruta |
| T-D3/4 | D3,D4 | Tangentsekvenser via pty; läs `hyprctl clients -j`; testa båda lägena (`m`) | Geometri enligt tabell (±1 px), klamrat mot skärmkant; statusraden visar rätt läge |
| T-D2 | D2 | Sätt färg via hexkod, via färgrad och via `hyprpicker`; skärmdump (grim, Read); ändra tjocklek; starta om | Kanten har vald färg och tjocklek, följer cirkel och rektangel, värdena sparas per kamera |
| T-C4b | C4 | Spela in; kontrollera filnamn med regex `^screenrecording-[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}_[0-9]{2}_[0-9]{2}\.mp4$`; kolla att Omarchys namn inte finns kvar; skapa krock | Rätt namn i ~/Videos, ingen dubbel, krock får `-2` |
| T-D5 | D5 | Tab + 1–9 | Rätt kamera, rätt position |
| T-D7 | D7 | `hyprctl activewindow` efter varje åtgärd | Fokus kvar på TUI:t |
| T-D8 | D8 | Starta Omarchys WebcamOverlay parallellt | Ingen störning åt något håll |
| T-E1 | E1 | q, Esc | Inga Multicam-fönster/regler/mpv-processer kvar; mic återställd |
| T-E2 | E2 | Ctrl+C, stäng terminalen, `--stop-recording` utifrån | Samma städresultat inom 1 s |
| T-E3 | E3 | Skärmdump av fältet under inspelning; kör klickkommandot | Ikon syns; stoppar; ikon borta (M för verkligt musklick) |
| T-E4 | E4 | Döda inspelaren med SIGTERM | Vakten städar |
| T-E5 | E5 | Starta annan `mpv` i förväg | Den påverkas inte |
| T-F2 | F2 | Mät fps och CPU 15 s; skärmdump | ≥ 25 fps, genomskinlig bakgrund (skrivbord syns) |
| T-F3 | F3 | Ändra modellfil, kör installationens kontroll | SHA256-fel stoppar |
| T-X1 | allt | Två kameror + cirkel + mic + 30 s inspelning | Stabil, inga tappade bilder, fil spelbar |
| T-X2 | allt | Kör hela flödet två gånger i rad | Ingen rest från första körningen |

## 4. Kända begränsningar (från testerna)
- Hyprland 0.56.2: endast Lua-dispatch fungerar (`hl.dsp.window.*`); gamla `movewindowpixel` gör det inte.
- Fönsterregeln `rounding` är begränsad till 20, så cirkeln sätts med `set_prop` efter att fönstret öppnats.
- Rundning går inte att läsa tillbaka; cirkel verifieras med skärmdump.
- Omarchys stopp (klick/Alt+Print) stänger bara `WebcamOverlay`; resten städas av multicams vakt.
- Ett Omarchy-hanterat inspelning och multicam kan inte köras samtidigt.
- `hyprpicker` kräver musklick; tangentbordsalternativen är hexkod och färgrad.
- Bakgrund bort: ~300 MB Python-miljö (kan minskas), GPL-3.0-modell, mjuka kanter.
- Inte verifierat ännu: riktigt musklick på fältikonen, andra terminaler än foot, kombination cirkel + bakgrund bort, två riktiga kameror samtidigt med bakgrund bort.

## 5. Leveransordning
1. `multicam` med kameror, form, ring, tangentbordsstyrning, mic, inspelning, städning (testerna A–E).
2. install/uninstall + .desktop + valfri genväg.
3. Bakgrund bort som tillägg (F).
4. Privat GitHub-repo.
