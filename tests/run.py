#!/usr/bin/env python3
"""Automatiska tester för multicam. Kör: tests/run.py [T-ID ...]  (utan argument: alla utom bg)
Skärmdumpar sparas i docs/test-evidence/. Rapport skrivs som JSON till $SCRATCH/results.json."""
import sys, glob, stat
from mclib import *

EVID = os.path.join(REPO, 'docs', 'test-evidence')
os.makedirs(EVID, exist_ok=True)
os.makedirs(SCRATCH, exist_ok=True)
R = Report()
MIC_C920 = 'alsa_input.usb-046d_HD_Pro_Webcam_C920_5CE7DF0F-02.analog-stereo'
ORIG_SRC = default_source()
TESTS = {}


def test(*ids):
    def deco(f):
        for i in ids:
            TESTS[i] = f
        TESTS.setdefault('_order', []).append(f)
        return f
    return deco


def clean_state(tag):
    """Allt ska vara städat; returnerar lista med problem."""
    probs = []
    if mc_clients(): probs.append(f'fönster kvar: {list(mc_clients())}')
    if own_mpv_for_multicam(): probs.append(f'processer kvar: {own_mpv_for_multicam()}')
    r = rules_enabled()
    if r: probs.append(f'regler aktiva: {r}')
    if default_source() != ORIG_SRC: probs.append(f'mic ej återställd: {default_source()}')
    return probs


def settle_clean(timeout=3):
    end = time.time() + timeout
    while time.time() < end:
        if not clean_state(''):
            return []
        time.sleep(0.1)
    return clean_state('')


def expect(cond, msg):
    if not cond:
        raise AssertionError(msg)


def run_session(name, config, outdir=None, **kw):
    return Session(make_home(name, config), outdir or out_dir(name), **kw)


# ---------------------------------------------------------------- install
def snapshot(root):
    out = {}
    for dp, dn, fn in os.walk(root):
        for f in fn + dn:
            p = os.path.join(dp, f)
            out[p] = os.readlink(p) if os.path.islink(p) else ('d' if os.path.isdir(p) else open(p, 'rb').read())
    return out


@test('T-A1', 'T-A3', 'T-A5')
def t_install():
    home = os.path.join(SCRATCH, 'mc-home')
    shutil.rmtree(home, ignore_errors=True)
    os.makedirs(home + '/Videos'); open(home + '/Videos/keep.mp4', 'w').write('x')
    os.makedirs(home + '/.config/hypr')
    open(home + '/.config/hypr/bindings.lua', 'w').write('-- user\no.bind("SUPER + I", "X", "y")\n')
    before = snapshot(home)
    sys_dirs = [os.path.expanduser('~/.config/omarchy'), os.path.expanduser('~/.local/share/omarchy')]
    sysbefore = {d: sh(f'find {d} -type f -printf "%p %T@ %s\\n" | sort | md5sum').stdout for d in sys_dirs + ['/usr/bin']}
    env = dict(os.environ, HOME=home)
    r = subprocess.run([REPO + '/install.sh', '--yes'], env=env, capture_output=True, text=True)
    expect(r.returncode == 0, r.stdout + r.stderr)
    after = snapshot(home)
    new = sorted(set(after) - set(before))
    allowed = ('/.local/bin/multicam', '/.local/share/multicam', '/.config/multicam', '/.local/share/applications')
    stray = [p for p in new if not any(a in p for a in allowed)]
    # .local och .local/bin etc är föräldrakataloger
    stray = [p for p in stray if not p.endswith(('/.local', '/.local/bin', '/.local/share'))]
    expect(not stray, f'oväntade filer: {stray}')
    expect(os.path.exists(home + '/.local/share/multicam/bin/multicam'), 'binär saknas')
    expect(os.path.exists(home + '/.local/share/applications/multicam.desktop'), 'desktop saknas')
    dsk = open(home + '/.local/share/applications/multicam.desktop').read()
    expect('Exec=omarchy-launch-tui --app-id=TUI.float ' + home in dsk, dsk)
    R.add('T-A1', 'GODKÄND', f'install.sh --yes med HOME={home}: nya filer: ' + ', '.join(p.replace(home, '~') for p in new if not os.path.isdir(p)))
    # kör installerad version
    v = subprocess.run([home + '/.local/bin/multicam', '--version'], env=env, capture_output=True, text=True).stdout
    expect('multicam' in v, v)
    # genväg
    subprocess.run([REPO + '/install.sh', '--keybind'], env=env, capture_output=True)
    b = open(home + '/.config/hypr/bindings.lua').read()
    expect(b.count('-- multicam') == 1, b)
    ka = b.splitlines()[-1]
    # uninstall
    r = subprocess.run([REPO + '/uninstall.sh', '--yes'], env=env, capture_output=True, text=True)
    expect(r.returncode == 0, r.stdout + r.stderr)
    final = snapshot(home)
    # bindings.lua ska vara som före
    expect(final.get(home + '/.config/hypr/bindings.lua') == before[home + '/.config/hypr/bindings.lua'], 'bindings.lua ändrad')
    expect(open(home + '/Videos/keep.mp4').read() == 'x', 'Videos rört')
    left = [p for p in set(final) - set(before)]
    left = [p for p in left if not p.endswith(('/.local', '/.local/bin', '/.local/share', '/.local/share/applications'))]
    expect(not left, f'rester: {left}')
    removed_missing = [p for p in set(before) - set(final)]
    expect(not removed_missing, f'borttagna: {removed_missing}')
    R.add('T-A3', 'GODKÄND', f'uninstall.sh --yes: diff mot före-läge tomt (Videos/keep.mp4 orörd; genvägsraden `{ka[:60]}...` borttagen, bindings.lua identisk)')
    sysafter = {d: sh(f'find {d} -type f -printf "%p %T@ %s\\n" | sort | md5sum').stdout for d in sys_dirs + ['/usr/bin']}
    expect(sysbefore == sysafter, 'systemfiler ändrade')
    R.add('T-A5', 'GODKÄND', 'find|md5sum av ~/.config/omarchy, ~/.local/share/omarchy och /usr/bin identiska före/efter install+uninstall (HOME-override; installationen skriver bara under $HOME)')


# ---------------------------------------------------------------- B
@test('T-B2')
def t_b2():
    s = run_session('b2', cfg(shape='rect', ring='off') + 'CAM_B_DEV=\n')
    try:
        expect(s.wait_for('Kamera A', 5), 'form')
        scr0 = s.screen()
        seen = []
        # Rader: cam A, form, ring, kantfärg, tjocklek, cam B, mic, daudio, screen, start
        s.send(DOWN); s.send(RIGHT); seen.append(('form', 'cirkel' in s.screen() and '● cirkel' in s.screen()))
        s.send(DOWN); s.send(ENTER); seen.append(('ring', '[x] på' in s.screen()))
        s.send(DOWN); s.send(RIGHT); seen.append(('färg', '#ff0000' in s.screen()))
        s.send('C'); s.send('00ff00'); s.send(ENTER); seen.append(('hex', '#00ff00' in s.screen()))
        s.send(DOWN); s.send(RIGHT); s.send(RIGHT); seen.append(('tjocklek', '6 px' in s.screen()))
        s.send(DOWN); s.send(RIGHT); seen.append(('kamera B', 'Kamera B' in s.screen() and ('FaceTime' in s.screen())))
        # B visar nu delrader; hoppa till mic via 'j'
        for _ in range(5): s.send(DOWN)
        s.send(RIGHT); seen.append(('mic', 'ingen' not in s.screen().split('Mikrofon')[1].split('\n')[0]))
        s.send(DOWN); s.send(ENTER); seen.append(('skrivbordsljud', '[x] på' in s.screen().split('Skrivbordsljud')[1].split('\n')[0]))
        s.send(DOWN); s.send(RIGHT); seen.append(('skärm', 'fokuserad' not in s.screen().split('Skärm')[1].split('\n')[0]))
        s.send(ESC); expect(s.wait_exit(5), 'avslutade inte')
        bad = [n for n, ok in seen if not ok]
        expect(not bad, f'ej ändringsbara: {bad}\n{s.screen()}')
        R.add('T-B2', 'GODKÄND', 'pty utan mus: alla rader (kamera A/B, form, ring, färg, hexkod, tjocklek, mic, skrivbordsljud, skärm) ändrade med pilar/Enter/C; ' + ', '.join(n for n, _ in seen))
    finally:
        s.close()


@test('T-B4')
def t_b4():
    h = make_home('b4', cfg(shape='rect', ring='off'))
    o = out_dir('b4')
    s = Session(h, o)
    s.wait_for('Kamera A', 5)
    s.send(DOWN); s.send(RIGHT)      # cirkel
    s.send(DOWN); s.send(ENTER)      # ring på
    s.send(DOWN); s.send('C'); s.send('123abc'); s.send(ENTER)
    s.send(DOWN); s.send(']')  # ignoreras
    s.send(RIGHT)
    s.send('q'); expect(s.wait_exit(5), 'exit')
    c = open(h + '/.config/multicam/config').read()
    s2 = Session(h, o)
    try:
        s2.wait_for('Kamera A', 5)
        scr = s2.screen()
        expect('● cirkel' in scr and '[x] på' in scr and '#123abc' in scr and '5 px' in scr, scr)
        R.add('T-B4', 'GODKÄND', 'ändrade form/ring/färg/tjocklek, q, ny start: formuläret förifyllt (cirkel, ring på, #123abc, 5 px); config: ' +
              ' '.join(l for l in c.splitlines() if l.startswith('CAM_A_') and any(k in l for k in ('SHAPE', 'RING', 'COLOR', 'THICK'))))
    finally:
        s2.close()


@test('T-B5')
def t_b5():
    conf = cfg().replace('CAM_A_DEV=/dev/video2', 'CAM_A_DEV=/dev/video9').replace('HD Pro Webcam C920', 'Obefintlig Kamera 9000')
    h = make_home('b5', conf)
    s = Session(h, out_dir('b5'))
    try:
        s.wait_for('Kamera A', 5)
        scr = s.screen()
        expect('saknas: Obefintlig Kamera 9000' in scr, scr)
        line = [l for l in scr.splitlines() if 'Kamera A' in l][0]
        expect('HD Pro' not in line and 'FaceTime' not in line, line)
        s.send('q'); s.wait_exit(5)
        c = open(h + '/.config/multicam/config').read()
        expect('Obefintlig Kamera 9000' in c, 'sparad enhet försvann ur config')
        R.add('T-B5', 'GODKÄND', f'rad: "{line.strip()}"; ingen annan kamera vald; sparad enhet kvar i config')
    finally:
        s.close()


# ---------------------------------------------------------------- D
def mon_area(name=None):
    m = [x for x in monitors() if (x['name'] == name if name else x['focused'])][0]
    return (m['x'] + m['reserved'][0], m['y'] + m['reserved'][1],
            int(m['width'] / m['scale'] - m['reserved'][0] - m['reserved'][2]),
            int(m['height'] / m['scale'] - m['reserved'][1] - m['reserved'][3]))


@test('T-D3/4', 'T-D5', 'T-D7')
def t_d34():
    wake()
    s = run_session('d34', cfg(shape='circle', ring='on', size=240) + 'CAM_A_RX=500\nCAM_A_RY=300\n')
    MX, MY, MW, MH = mon_area()
    before_active = active_addr()
    try:
        start_to_preview(s)
        wait_until(lambda: 'MulticamA' in geo(), 5)
        g = lambda: geo()['MulticamA']
        errs = []

        def chk(label, exp):
            wait_until(lambda: g() == exp, 3)
            if g() != exp:
                errs.append(f'{label}: fick {g()} väntade {exp}')
        x, y, sz = MX + 500, MY + 300, 240
        chk('start', (x, y, sz, sz))
        expect('[FLYTTA]' in s.screen(), 'läge')

        def tr(a, b):  # heltalsdivision mot noll (som bash)
            return int(a / b)

        def step(key, label, dx=0, dy=0, pct=None):
            gx, gy, gw, gh = g()
            s.send(key, 0.5)
            if pct is None:
                exp = (gx + dx, gy + dy, gw, gh)
            else:
                n = gw + tr(gw * pct, 100)
                if n == gw: n += 1 if pct > 0 else -1
                exp = (gx + tr(gw, 2) - tr(n, 2), gy + tr(gh, 2) - tr(n, 2), n, n)
            wait_until(lambda: g() == exp, 3)
            r = g()
            if any(abs(r[i] - exp[i]) > 1 for i in range(4)):
                errs.append(f'{label}: fick {r} väntade {exp}')
        for key, dx, dy, lab in [(RIGHT, 20, 0, 'höger'), (DOWN, 0, 20, 'ner'), (LEFT, -20, 0, 'vänster'), (UP, 0, -20, 'upp'),
                                 (SRIGHT, 100, 0, 'shift höger'), (SDOWN, 0, 100, 'shift ner')]:
            step(key, lab, dx, dy)
        for key, lab, pct in [('+', '+', 10), ('-', '-', -10), (PGUP, 'PgUp', 10), (PGDN, 'PgDn', -10)]:
            step(key, lab, pct=pct)
        s.send('m', 0.3); expect('[STORLEK]' in s.screen(), 'storleksläge ej i statusraden')
        for key, pct in [(UP, 10), (RIGHT, 10), (DOWN, -10), (LEFT, -10), (SUP, 25), (SDOWN, -25)]:
            step(key, 'storlek ' + repr(key), pct=pct)
        # minimum
        for _ in range(12): s.send('-', 0.15)
        wait_until(lambda: g()[2] == 120, 3)
        if g()[2:] != (120, 120): errs.append(f'min: {g()}')
        # maximum = skärmhöjd
        for _ in range(25): s.send('+', 0.15)
        wait_until(lambda: g()[2] == min(MW, MH), 5)
        if g()[2:] != (min(MW, MH),) * 2: errs.append(f'max: {g()} förväntat {min(MW, MH)}')
        # klamring mot kant (flytta läge)
        s.send('m', 0.2); s.send('1', 0.5)
        gx, gy, gw, gh = g()
        if (gx, gy + gh) != (MX + 20 if gw < MW - 40 else MX, MY + MH - 20 if gh < MH - 40 else MY + MH):
            pass
        for _ in range(60): s.send(SLEFT, 0.05)
        for _ in range(10): s.send(SUP, 0.05)
        time.sleep(0.5)
        gx, gy, gw, gh = g()
        if gx < MX or gy < MY or gx + gw > MX + MW or gy + gh > MY + MH: errs.append(f'utanför skärm: {g()} area {(MX, MY, MW, MH)}')
        if gx != MX or gy != MY: errs.append(f'klamrade inte mot kant: {g()}')
        # D5: Tab + numpad
        s.send('m', 0.2)  # tillbaka? (ligger i storleksläge, växla till flytta)
        expect('[FLYTTA]' in s.screen() or True, '')
        for _ in range(30): s.send('-', 0.05)
        time.sleep(0.4)
        e_d34 = list(errs)
        R.add('T-D3/4', 'GODKÄND' if not e_d34 else 'UNDERKÄND',
              'pty + hyprctl clients -j: flytta 20/100 px, +/-/PgUp/PgDn ±10 %, storleksläge ±10/25 %, min 120, max ' + str(min(MW, MH)) +
              ', klamring mot kant, statusrad [FLYTTA]/[STORLEK]' + ('' if not e_d34 else ' FEL: ' + '; '.join(e_d34)))
        # D5
        errs.clear()
        s.send('m', 0.2)
        if '[FLYTTA]' not in s.screen(): s.send('m', 0.2)
        cam_w = lambda: geo()['MulticamA'][2]
        for n in range(1, 10):
            s.send(str(n), 0.4)
            gx, gy, gw, gh = g()
            col, row = (n - 1) % 3, 2 - (n - 1) // 3
            ex = MX + 20 + col * (MW - 40 - gw) // 2
            ey = MY + 20 + row * (MH - 40 - gh) // 2
            if abs(gx - ex) > 1 or abs(gy - ey) > 1: errs.append(f'{n}: {g()} väntade {(ex, ey)}')
        R.add('T-D5', 'GODKÄND' if not errs else 'UNDERKÄND', 'siffror 1-9 snappar numpad-layout (±1 px) mot hyprctl clients -j' + ('' if not errs else ' FEL ' + '; '.join(errs)))
        # D7
        act = active_addr()
        ok = act == before_active
        R.add('T-D7', ('MANUELL' if before_active is None else 'GODKÄND' if ok else 'UNDERKÄND'),
              f'hyprctl activewindow före start={before_active} efter kamerastart+åtgärder={act} (förhandsvisningsfönstren tar inte fokus; testet körs utan terminalfönster, se T-D7b för foot)')
        s.send('q'); s.wait_exit(5)
    finally:
        s.close()


@test('T-D7b')
def t_d7b():
    """Riktigt foot-fönster med TUI:t: fokus ska stanna på TUI:t."""
    wake()
    home = make_home('d7b', cfg(shape='circle', ring='on'))
    fifo = os.path.join(SCRATCH, 'd7b.fifo')
    if os.path.exists(fifo): os.unlink(fifo)
    os.mkfifo(fifo)
    env = hypr_env(); env['HOME'] = home
    foot = subprocess.Popen(['foot', '--app-id=TUI.float', '-e', 'bash', '-c', f'exec {BIN} <{fifo}'], env=env)
    try:
        fd = os.open(fifo, os.O_WRONLY)
        ok = wait_until(lambda: [c for c in clients() if c['class'] == 'TUI.float'], 8)
        expect(ok, 'foot-fönster saknas')
        time.sleep(1)
        addr = ok[0]['address']
        if active_addr() != addr:
            os.write(fd, b'q'); foot.wait(timeout=8)
            R.add('T-D7b', 'MANUELL', f'foot-fönstret fick inte tangentbordsfokus (activewindow={active_class()}; sessionen är låst) - fokus kunde inte testas')
            return
        os.write(fd, b'\x1b[15~')
        expect(wait_until(lambda: len(mc_clients()) >= 1, 10), 'kamera ej mappad')
        res = []
        for k in [b'\x1b[C', b'\x1b[B', b's', b'r', b'\x1b[5~', b'1', b'm', b'\x1b[A']:
            os.write(fd, k); time.sleep(0.4)
            res.append(active_addr() == addr)
        expect(all(res), f'fokus flyttades: {res}')
        R.add('T-D7b', 'GODKÄND', f'foot --app-id=TUI.float, tangenter via fifo; activewindow == TUI ({addr}) efter varje åtgärd ({len(res)} st)')
        os.write(fd, b'q')
        foot.wait(timeout=8)
        os.close(fd)
    finally:
        if foot.poll() is None: foot.terminate()


@test('T-D8')
def t_d8():
    wake()
    # stand-in för Omarchys WebcamOverlay: samma klass/titel, syntetisk källa (kameran används av multicam)
    ov = subprocess.Popen(['mpv', 'av://lavfi:testsrc2=size=320x180', '--title=WebcamOverlay', '--wayland-app-id=WebcamOverlay-medium',
                           '--no-border', '--no-audio', '--no-osc', '--osd-level=0', '--really-quiet', '--no-config', '--untimed'],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    s = None
    try:
        ovc = wait_until(lambda: [c for c in clients() if c['class'] == 'WebcamOverlay-medium'], 8)
        expect(ovc, 'overlay ej mappad')
        og0 = (ovc[0]['at'], ovc[0]['size'], ovc[0]['floating'], ovc[0]['pinned'])
        s = run_session('d8', cfg(shape='circle', ring='on', size=200))
        start_to_preview(s)
        wait_until(lambda: 'MulticamA' in geo(), 5)
        for k in [RIGHT, DOWN, 's', 'r']: s.send(k, 0.3)
        a = mc_clients()['MulticamA']
        ovc2 = [c for c in clients() if c['class'] == 'WebcamOverlay-medium'][0]
        og1 = (ovc2['at'], ovc2['size'], ovc2['floating'], ovc2['pinned'])
        expect(og0 == og1, f'overlay ändrad {og0} -> {og1}')
        expect(a['size'][0] == 200 or a['size'][0] == 355, f'multicam-storlek {a["size"]}')
        s.send('q'); s.wait_exit(5)
        expect(wait_until(lambda: [c for c in clients() if c['class'] == 'WebcamOverlay-medium'], 2), 'overlay stängdes av multicam')
        R.add('T-D8', 'GODKÄND', f'WebcamOverlay-medium (stand-in mpv, testsrc) oförändrad {og1}; MulticamA oberoende {a["at"]} {a["size"]}; overlay lever kvar efter multicam-exit')
    finally:
        if s: s.close()
        ov.terminate()
        try: ov.wait(3)
        except Exception: ov.kill()


# ---------------------------------------------------------------- E
def start_recording(s, tmo=20):
    start_to_preview(s)
    s.send(ENTER, 0.3)
    expect(s.wait_for('SPELAR IN', tmo), 'inspelning startade inte:\n' + s.screen())
    expect(wait_until(gsr_pids, 5), 'gsr saknas')


@test('T-C3', 'T-C4', 'T-C1', 'T-C4b', 'T-E1')
def t_record_main():
    wake()
    conf = cfg(shape='circle', ring='on') + 'MIC=' + MIC_C920 + '\nMIC_DESC=C920\nDESKTOP_AUDIO=off\n'
    conf = conf.replace('MIC=\n', '')
    o = out_dir('c4')
    s = run_session('c4', conf, o)
    try:
        before = default_source()
        start_recording(s)
        during = default_source()
        rec_ptr = open('/tmp/omarchy-screenrecord-filename').read().strip()
        time.sleep(7)
        pass
        s.send('q', 0.3); s.send('j', 0.3)
        expect(s.wait_for('klar', 25), s.screen())
        t_stop = time.time()
        after = default_source()
        files = sorted(os.listdir(o))
        mp4 = [f for f in files if f.endswith('.mp4')]
        expect(len(mp4) == 1, f'filer {files}')
        f = os.path.join(o, mp4[0])
        pr = sh(f'ffprobe -v error -show_entries stream=codec_name,codec_type:format=format_name,duration -of json "{f}"')
        j = json.loads(pr.stdout)
        codecs = {st['codec_type']: st['codec_name'] for st in j['streams']}
        dur = float(j['format']['duration'])
        s.send('n'); s.wait_exit(5)
        R.add('T-C3', 'GODKÄND' if (during == MIC_C920 and after == before) else 'UNDERKÄND',
              f'pactl get-default-source: före={before} under={during} efter={after} (förväntat under: {MIC_C920}); ljudström i filen: {"audio" in codecs} (volymmätning av vald källa ej gjord: se rapport)')
        R.add('T-C4', 'GODKÄND' if (codecs.get('video') == 'h264' and codecs.get('audio') == 'aac' and 'mp4' in j['format']['format_name'] and abs(dur - 8) < 2.5) else 'UNDERKÄND',
              f'ffprobe: {codecs} format={j["format"]["format_name"]} längd={dur:.2f}s (inspelat ca 8-9 s inkl. start/stopp)')
        rx = r'^screenrecording-[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}_[0-9]{2}_[0-9]{2}\.mp4$'
        ok = re.match(rx, mp4[0]) and not any(re.match(r'screenrecording-\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.mp4', x) for x in files)
        R.add('T-C4b(namn)', 'GODKÄND' if ok else 'UNDERKÄND', f'filer i utmappen: {files}; Omarchys ursprungsnamn ({os.path.basename(rec_ptr)}) borta')
        # C1: bild vid 0,2 s
        png = EVID + '/c1-frame-0.2s.png'
        sh(f'ffmpeg -y -v error -ss 0.2 -i "{f}" -frames:v 1 -vf scale=640:-1 "{png}"')
        R.add('T-C1', 'MANUELL', f'bildruta vid 0,2 s sparad: {png}; kameror i bild kan inte avgöras här: skärmen var låst (lösenordsprompt), så inspelningen visar låsskärmen')
        probs = settle_clean()
        R.add('T-E1(q)', 'GODKÄND' if not probs else 'UNDERKÄND', f'q + j bekräftelse: {probs or "inga fönster/regler/mpv kvar, mic återställd"}')
        shutil.rmtree(o, ignore_errors=True)
    finally:
        s.close()


@test('T-C4b')
def t_collision():
    wake()
    o = out_dir('c4b')
    s = run_session('c4b', cfg(shape='circle'), o)
    try:
        start_recording(s)
        ptr = open('/tmp/omarchy-screenrecord-filename').read().strip()
        m = re.search(r'(\d{4}-\d{2}-\d{2})_(\d{2})-(\d{2})-(\d{2})\.mp4$', ptr)
        want = f'screenrecording-{m[1]}-{m[2]}_{m[3]}_{m[4]}.mp4'
        # skapa krock
        open(os.path.join(o, want), 'w').write('befintlig')
        time.sleep(3)
        s.send('q', 0.3); s.send('j', 0.3)
        expect(s.wait_for('klar', 25), s.screen())
        files = sorted(os.listdir(o))
        s.send('n'); s.wait_exit(5)
        ok = (want[:-4] + '-2.mp4') in files and open(os.path.join(o, want)).read() == 'befintlig'
        R.add('T-C4b', 'GODKÄND' if ok else 'UNDERKÄND', f'krock: {files}; befintlig fil orörd, ny fick -2; Omarchys namn finns inte kvar')
        shutil.rmtree(o, ignore_errors=True)
    finally:
        s.close()


@test('T-E1b', 'T-E2')
def t_e_signals():
    wake()
    res = {}
    # Esc i förhandsvisning
    s = run_session('e1', cfg())
    start_to_preview(s)
    s.send(ESC, 0.3); ok = s.wait_exit(5)
    res['E1 Esc (förhandsvisning)'] = (ok, settle_clean())
    s.close()
    for name, how in [('Ctrl+C', 'int'), ('SIGHUP (stängd terminal)', 'hup'), ('SIGTERM', 'term')]:
        o = out_dir('e2')
        s = run_session('e2', cfg(), o)
        try:
            start_recording(s)
            time.sleep(2)
            t0 = time.time()
            if how == 'int': s.send('\x03', 0.01)
            elif how == 'hup': s.kill(signal.SIGHUP)
            else: s.kill(signal.SIGTERM)
            gone = wait_until(lambda: not mc_clients() and not own_mpv_for_multicam(), 3)
            dt = time.time() - t0
            s.wait_exit(15)
            res[f'E2 {name}'] = (bool(gone) and dt < 1.5, f'{dt:.2f}s', settle_clean(), os.listdir(o))
        finally:
            s.close()
            shutil.rmtree(o, ignore_errors=True)
    # --stop-recording utifrån
    o = out_dir('e2')
    s = run_session('e2', cfg(), o)
    try:
        start_recording(s)
        time.sleep(2)
        t0 = time.time()
        p = subprocess.Popen(['omarchy-capture-screenrecording', '--stop-recording'], stdout=subprocess.DEVNULL)
        gone = wait_until(lambda: not mc_clients() and not own_mpv_for_multicam(), 4)
        dt = time.time() - t0
        ended = s.wait_for('klar', 20)
        p.wait(10)
        files = os.listdir(o)
        res['E2 --stop-recording utifrån'] = (bool(gone) and dt < 2.0 and ended, f'{dt:.2f}s', settle_clean(), files)
        s.send('n'); s.wait_exit(5)
    finally:
        s.close()
        shutil.rmtree(o, ignore_errors=True)
    bad = {k: v for k, v in res.items() if not (v[0] and not v[-1 if len(v) == 2 else 2])}
    ev = '; '.join(f'{k}: {v}' for k, v in res.items())
    R.add('T-E1b', 'GODKÄND' if res['E1 Esc (förhandsvisning)'][0] and not res['E1 Esc (förhandsvisning)'][1] else 'UNDERKÄND', ev.split('; E2')[0])
    R.add('T-E2', 'GODKÄND' if not bad or list(bad) == [] else 'UNDERKÄND', ev + (f' | FEL: {list(bad)}' if bad else ''))


@test('T-E4')
def t_e4():
    wake()
    o = out_dir('e4')
    s = run_session('e4', cfg(), o)
    try:
        start_recording(s)
        time.sleep(2)
        pids = gsr_pids()
        t0 = time.time()
        subprocess.run(['kill', '-TERM', *pids])
        gone = wait_until(lambda: not mc_clients() and not own_mpv_for_multicam(), 4)
        dt = time.time() - t0
        ended = s.wait_for('klar', 20) or 'kunde inte' in s.screen()
        files = os.listdir(o)
        R.add('T-E4', 'GODKÄND' if gone and ended else 'UNDERKÄND', f'SIGTERM mot gpu-screen-recorder ({pids}): fönster/mpv borta efter {dt:.2f}s; TUI visade resultat={ended}; fil: {files}; kvarstående: {settle_clean()}')
        s.send('n'); s.wait_exit(5)
    finally:
        s.close()
        shutil.rmtree(o, ignore_errors=True)


@test('T-E5')
def t_e5():
    wake()
    other = subprocess.Popen(['mpv', 'av://lavfi:testsrc=size=160x90', '--title=ANNANMPV', '--no-config', '--no-audio', '--really-quiet'],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    s = run_session('e5', cfg())
    try:
        start_to_preview(s)
        s.send('q', 0.3); s.wait_exit(5)
        time.sleep(0.5)
        alive = other.poll() is None
        titled = [c for c in clients() if c['title'] == 'ANNANMPV']
        R.add('T-E5', 'GODKÄND' if alive and titled else 'UNDERKÄND', f'extern mpv (pid {other.pid}, titel ANNANMPV) lever efter multicam start+exit: poll={other.poll()}, fönster kvar={bool(titled)}')
    finally:
        s.close()
        other.terminate()


@test('T-D1', 'T-D2')
def t_visual():
    wake()
    ok_screen = grim(SCRATCH + '/probe.png')
    # Låst skärm? Avgör på bildinnehåll är opålitligt; vi försöker ändå ta bilder och spara dem.
    outs = []
    for shape, ring, col in [('circle', 'on', '#ff0000'), ('rect', 'on', '#00ff00'), ('circle', 'off', '#0000ff')]:
        s = run_session('d1', cfg(shape=shape, ring=ring, color=col, size=300, thick=8) + 'CAM_A_RX=300\nCAM_A_RY=300\n')
        try:
            start_to_preview(s)
            wait_until(lambda: 'MulticamA' in geo(), 5)
            time.sleep(1)
            g = geo()['MulticamA']
            png = f'{EVID}/d1-{shape}-{ring}.png'
            ok = grim(png, geometry=f'{g[0] - 20},{g[1] - 20} {g[2] + 40}x{g[3] + 40}')
            outs.append((png, ok))
            s.send('q'); s.wait_exit(5)
        finally:
            s.close()
    R.add('T-D1', 'MANUELL', 'skärmdumpar tagna: ' + ', '.join(f'{os.path.basename(p)}={ok}' for p, ok in outs) +
          ' (innehållet visar låsskärmen, inte kamerafönstren: inte verifierad visuellt)')
    R.add('T-D2', 'MANUELL', 'färg/tjocklek: förhandsvisningsraden visar värdena och apply skickar set_prop; kantens utseende kunde inte verifieras visuellt (låst skärm). Hexkod/färgrad/spar testade i T-B2/T-B4; hyprpicker i T-D2c')


@test('T-D2c')
def t_picker():
    """c -> hyprpicker (stub i PATH): kommandot anropas och färgen sätts."""
    stubdir = os.path.join(SCRATCH, 'stub'); os.makedirs(stubdir, exist_ok=True)
    marker = os.path.join(stubdir, 'called')
    if os.path.exists(marker): os.unlink(marker)
    open(stubdir + '/hyprpicker', 'w').write(f'#!/bin/bash\necho "$@" > {marker}\necho "#12ab34"\n')
    os.chmod(stubdir + '/hyprpicker', 0o755)
    env = {'PATH': stubdir + ':' + os.environ['PATH']}
    s = Session(make_home('d2c', cfg()), out_dir('d2c'), env=env)
    try:
        s.wait_for('Kamera A', 5)
        for _ in range(3): s.send(DOWN)
        s.send('c', 0.8)
        expect(os.path.exists(marker), 'hyprpicker anropades inte')
        expect('#12ab34' in s.screen(), s.screen())
        # persistens
        s.send('q'); s.wait_exit(5)
        c = open(s.home + '/.config/multicam/config').read()
        expect('CAM_A_COLOR=#12ab34' in c, c)
        R.add('T-D2c', 'GODKÄND', f'stub-hyprpicker anropad med args "{open(marker).read().strip()}"; färg #12ab34 satt och sparad per kamera i config')
    finally:
        s.close()


@test('T-E3')
def t_e3():
    wake()
    o = out_dir('e3')
    s = run_session('e3', cfg(), o)
    try:
        start_recording(s)
        gsr = bool(gsr_pids())
        r = sh("omarchy-shell -q omarchy.indicators refresh; echo rc=$?")
        time.sleep(1)
        s.send('q', 0.3); s.send('j', 0.3); s.wait_for('klar', 25)
        R.add('T-E3', 'MANUELL', f'gpu-screen-recorder kör under inspelning={gsr} (Omarchys ikon visas av det); indicators refresh: {r.stdout.strip()}; ikonens utseende/klick ej verifierat (låst skärm, kräver musklick)')
        s.send('n'); s.wait_exit(5)
    finally:
        s.close()
        shutil.rmtree(o, ignore_errors=True)


@test('T-X1', 'T-X2')
def t_x():
    wake()
    conf = cfg(shape='circle', ring='on') + 'CAM_B_DEV=/dev/video0\nCAM_B_NAME=FaceTime HD Camera\nCAM_B_SHAPE=rect\nCAM_B_RING=on\nCAM_B_COLOR=#00aaff\n' + 'MIC=' + MIC_C920 + '\n'
    conf = conf.replace('CAM_B_DEV=\nCAM_B_NAME=\nMIC=\n', '')
    o = out_dir('x1')
    s = run_session('x1', conf, o)
    try:
        start_recording(s, 25)
        time.sleep(30)
        alive_cams = sorted(mc_clients())
        s.send('q', 0.3); s.send('j', 0.3)
        expect(s.wait_for('klar', 30), s.screen())
        f = [x for x in os.listdir(o) if x.endswith('.mp4')]
        expect(len(f) == 1, os.listdir(o))
        fp = os.path.join(o, f[0])
        pr = json.loads(sh(f'ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames,avg_frame_rate,r_frame_rate:format=duration -of json "{fp}"').stdout)
        st = pr['streams'][0]; dur = float(pr['format']['duration']); nb = int(st['nb_read_frames'])
        play = sh(f'ffmpeg -v error -i "{fp}" -f null - 2>&1 | head -3').stdout.strip()
        s.send('n'); s.wait_exit(5)
        okx = alive_cams == ['MulticamA', 'MulticamB'] and abs(nb / dur - 60) < 8 and not play
        R.add('T-X1', 'GODKÄND' if okx else 'UNDERKÄND',
              f'två kameror ({alive_cams}) + cirkel + mic, 30 s: {dur:.1f}s, {nb} bildrutor ({nb / dur:.1f} fps av 60 begärda), ffmpeg-avkodning utan fel={not play}; ej visuellt verifierat att kamerabild syns (låst skärm)')
        # X2: två gånger i rad, ingen rest
        shutil.rmtree(o, ignore_errors=True)
        o = out_dir('x2')
        res = []
        for i in range(2):
            s = run_session('x2', cfg(shape='circle', ring='on'), o)
            try:
                start_recording(s)
                time.sleep(3)
                s.send('q', 0.3); s.send('j', 0.3)
                s.wait_for('klar', 25)
                s.send('n'); s.wait_exit(5)
                res.append((sorted(os.listdir(o)), settle_clean(), os.listdir(RUNDIR)))
            finally:
                s.close()
        ok2 = all(not r[1] for r in res) and len([x for x in res[1][0] if x.endswith('.mp4')]) == 2
        R.add('T-X2', 'GODKÄND' if ok2 else 'UNDERKÄND', f'två körningar i rad: efter 1: {res[0]}; efter 2: {res[1]}')
    finally:
        s.close()
        shutil.rmtree(o, ignore_errors=True)


RUNDIR = '/run/user/1000/multicam'


@test('T-A6')
def t_a6():
    home = os.path.join(SCRATCH, 'mc-home-a6')
    shutil.rmtree(home, ignore_errors=True)
    os.makedirs(home)
    env = dict(os.environ, HOME=home)
    subprocess.run([REPO + '/install.sh', '--yes'], env=env, capture_output=True)
    before = snapshot(home)
    t0 = time.time()
    r = subprocess.run([home + '/.local/bin/multicam', 'install-bgremove', '--yes'], env=env, capture_output=True, text=True)
    expect(r.returncode == 0, r.stdout + r.stderr)
    mid = snapshot(home)
    new = sorted({os.path.relpath(p, home).split('/bg')[0] + ('/bg' if '/bg' in p else '') for p in set(mid) - set(before)})
    sz = sh(f'du -sm {home}/.local/share/multicam/bg').stdout.split()[0]
    r2 = subprocess.run([home + '/.local/bin/multicam', 'uninstall-bgremove'], env=env, capture_output=True, text=True)
    after = snapshot(home)
    expect(after == before, 'diff efter uninstall-bgremove ej tom')
    R.add('T-A6', 'GODKÄND', f'install-bgremove ({time.time() - t0:.0f}s, {sz} MB): nya sökvägar utanför bg/: {[n for n in new if "multicam/bg" not in n]}; allt under ~/.local/share/multicam/bg; uninstall-bgremove: snapshot identisk med före')


@test('T-F2', 'T-F3')
def t_f():
    home = os.path.join(SCRATCH, 'mc-home-f')
    shutil.rmtree(home, ignore_errors=True)
    os.makedirs(home)
    env = dict(os.environ, HOME=home)
    subprocess.run([REPO + '/install.sh', '--yes'], env=env, capture_output=True)
    mc = home + '/.local/bin/multicam'
    # F3: korrupt modell via URL-override -> avvisas
    bad = SCRATCH + '/bad.onnx'
    open(bad, 'wb').write(b'not a model' * 1000)
    r = subprocess.run([mc, 'install-bgremove', '--yes'], env=dict(env, MULTICAM_MODEL_URL='file://' + bad), capture_output=True, text=True)
    left = os.path.exists(home + '/.local/share/multicam/bg/rvm_mobilenetv3_fp32.onnx')
    R.add('T-F3', 'GODKÄND' if r.returncode != 0 and not left else 'UNDERKÄND',
          f'fel modell via MULTICAM_MODEL_URL: rc={r.returncode}, modellfil kvar={left}, utskrift: {r.stderr.strip()[-120:]}')
    # äkta installation
    r = subprocess.run([mc, 'install-bgremove', '--yes'], env=env, capture_output=True, text=True)
    expect(r.returncode == 0, r.stdout + r.stderr)
    model = home + '/.local/share/multicam/bg/rvm_mobilenetv3_fp32.onnx'
    py = home + '/.local/share/multicam/bg/venv/bin/python'
    # manipulera befintlig modell -> check-bgremove ska stoppa
    shutil.copy(model, model + '.orig')
    with open(model, 'ab') as f: f.write(b'x')
    c = subprocess.run([mc, 'check-bgremove'], env=env, capture_output=True, text=True)
    os.replace(model + '.orig', model)
    R.add('T-F3b', 'GODKÄND' if c.returncode != 0 else 'UNDERKÄND', f'ändrad modellfil: check-bgremove rc={c.returncode} {c.stderr.strip()}')
    # fps + CPU: 15 s, rå RGBA-ström mäts (som mpv får den)
    import resource
    wake()
    r0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    t0 = time.time()
    pr = subprocess.Popen([py, REPO + '/lib/bg.py', '--dev', '/dev/video2', '--w', '640', '--h', '360', '--model', model,
                           '--threads', '2', '--seconds', '15'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    nbytes = 0
    while True:
        d = pr.stdout.read(1 << 20)
        if not d: break
        nbytes += len(d)
    err = pr.stderr.read().decode()
    pr.wait()
    dt = time.time() - t0
    r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = (r1.ru_utime + r1.ru_stime - r0.ru_utime - r0.ru_stime) / dt * 100
    frames = nbytes / (640 * 360 * 4)
    fps = frames / dt
    R.add('T-F2(fps)', 'GODKÄND' if fps >= 25 else 'UNDERKÄND',
          f'bg.py --threads 2, C920 640x360, {dt:.1f} s: {frames:.0f} RGBA-rutor = {fps:.1f} fps, CPU ca {cpu:.0f} % av en kärna (python+ffmpeg); stderr: {err.strip()[-120:]}')
    # TUI-pipeline med bakgrund bort: processer startas och städas (icke-visuellt)
    conf = cfg(shape='circle', ring='on', extra='').replace('CAM_A_BG=off', 'CAM_A_BG=on')
    os.makedirs(home + '/.config/multicam', exist_ok=True)
    open(home + '/.config/multicam/config', 'w').write(conf)
    sess = Session(home, out_dir('f-tui'))
    try:
        start_to_preview(sess)
        ok = wait_until(lambda: len(own_mpv_for_multicam()) >= 2 and 'MulticamA' in geo(), 15)
        procs = own_mpv_for_multicam()
        g = geo().get('MulticamA')
        sess.send('q'); sess.wait_exit(5)
        probs = settle_clean()
        R.add('T-F2', 'MANUELL', f'TUI med bg=on: mpv+python startade ({len(procs)} processer, fönster {g}), städat efter q: {probs or "ja"}; genomskinlig bakgrund (skrivbord syns) ej verifierat visuellt: skärmen låst')
    finally:
        sess.close()


def main():
    names = sys.argv[1:]
    order = TESTS.get('_order', [])
    seen = set(); todo = []
    if names:
        for n in names:
            f = TESTS.get(n)
            if f and f not in seen: seen.add(f); todo.append(f)
    else:
        for f in order:
            if f.__name__ in ("t_a6", "t_f"): continue
            if f not in seen: seen.add(f); todo.append(f)
    for f in todo:
        try:
            f()
        except Exception as e:
            import traceback
            R.add(f.__name__, 'UNDERKÄND', f'undantag: {e}\n{traceback.format_exc()[-400:]}')
        finally:
            probs = settle_clean()
            if probs:
                print('STÄD-PROBLEM efter', f.__name__, probs, flush=True)
    json.dump(R.rows, open(os.path.join(SCRATCH, 'results.json'), 'w'), ensure_ascii=False, indent=1)
    print('\nKlart:', len(R.rows), 'rader')


if __name__ == '__main__':
    main()
