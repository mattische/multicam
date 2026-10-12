#!/usr/bin/env python3
"""Automatiska tester för multicam. Kör: tests/run.py [T-ID ...]  (utan argument: alla utom bg)
Skärmdumpar sparas i $SCRATCH/evidence/ (checkas aldrig in: de visar kamerabild och skärm). Rapport skrivs som JSON till $SCRATCH/results.json."""
import sys, glob, stat
from mclib import *

EVID = os.path.join(SCRATCH, 'evidence')   # utanför repot: bilderna visar kamerabild och skärm
os.makedirs(EVID, exist_ok=True)
os.makedirs(SCRATCH, exist_ok=True)
R = Report()
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


EXPECTED_INSTALL = {
    '.local/bin/multicam',
    '.local/share/multicam/bin/multicam',
    '.local/share/multicam/lib/bg.py',
    '.local/share/multicam/rev',
    '.local/share/multicam/source',
    '.local/share/applications/multicam.desktop',
    '.config/multicam',
}


def realistic_home(name):
    """Tom HOME-kopia med riktiga ~/.config/hypr, ~/.config/omarchy, ~/.local/share/omarchy och en Videos-fil."""
    home = os.path.join(SCRATCH, name)
    shutil.rmtree(home, ignore_errors=True)
    os.makedirs(home + '/.config'); os.makedirs(home + '/.local/share/applications'); os.makedirs(home + '/.local/bin'); os.makedirs(home + '/Videos')
    open(home + '/Videos/keep.mp4', 'w').write('x')
    R_ = os.path.expanduser('~')
    for rel in ('.config/hypr', '.config/omarchy', '.local/share/omarchy'):
        if os.path.exists(f'{R_}/{rel}'):
            subprocess.run(['cp', '-a', f'{R_}/{rel}', f'{home}/{rel}'], check=True)
    bl = home + '/.config/hypr/bindings.lua'   # användarens egen multicam-genväg ska inte ingå i baslinjen
    if os.path.exists(bl):
        txt = open(bl).read().splitlines(True)
        open(bl, 'w').write(''.join(l for l in txt if not l.rstrip().endswith('-- multicam')))
    return home


def diff_r(a, b):
    r = subprocess.run(['diff', '-r', '--no-dereference', a, b], capture_output=True, text=True)
    return r.stdout.strip()


@test('T-A1', 'T-A3', 'T-A5')
def t_install():
    home = realistic_home('mc-home')
    pristine = os.path.join(SCRATCH, 'mc-home-pristine')
    shutil.rmtree(pristine, ignore_errors=True)
    subprocess.run(['cp', '-a', home, pristine], check=True)
    before = snapshot(home)
    env = dict(os.environ, HOME=home)
    usr_before = sh('find /usr/bin -type f -printf "%p %T@ %s\\n" | sort | md5sum').stdout
    r = subprocess.run([REPO + '/install.sh', '--yes', '--no-bgremove'], env=env, capture_output=True, text=True)
    expect(r.returncode == 0, r.stdout + r.stderr)
    after = snapshot(home)
    new = {os.path.relpath(p, home) for p in set(after) - set(before)}
    new = {p for p in new if p not in ('.local', '.local/bin', '.local/share', '.local/share/applications', '.cache')}
    # kataloger under multicam räknas inte separat
    new = {p for p in new if not p.startswith('.local/share/multicam/') or p.count('/') > 3 or p.endswith(('bin/multicam', 'lib/bg.py', '/rev', '/source'))}
    new = {p for p in new if p not in ('.local/share/multicam', '.local/share/multicam/bin', '.local/share/multicam/lib')}
    expect(new == EXPECTED_INSTALL, f'filuppsättning avviker: extra={sorted(new - EXPECTED_INSTALL)} saknas={sorted(EXPECTED_INSTALL - new)}')
    d_hypr = diff_r(pristine + '/.config/hypr', home + '/.config/hypr')
    d_om = diff_r(pristine + '/.config/omarchy', home + '/.config/omarchy')
    d_sh = diff_r(pristine + '/.local/share/omarchy', home + '/.local/share/omarchy')
    expect(not (d_hypr or d_om or d_sh), f'install ändrade Omarchy/Hypr-filer:\n{d_hypr}\n{d_om}\n{d_sh}')
    dsk = open(home + '/.local/share/applications/multicam.desktop').read()
    expect('Exec=omarchy-launch-tui --app-id=TUI.float ' + home in dsk, dsk)
    R.add('T-A1', 'GODKÄND', 'install.sh --yes mot HOME-kopia med riktiga ~/.config/{hypr,omarchy} och ~/.local/share/omarchy: nya sökvägar exakt == ' + ', '.join(sorted(EXPECTED_INSTALL)))
    v = subprocess.run([home + '/.local/bin/multicam', '--version'], env=env, capture_output=True, text=True).stdout
    expect('multicam' in v, v)
    r = subprocess.run([REPO + '/uninstall.sh', '--yes'], env=env, capture_output=True, text=True)
    expect(r.returncode == 0, r.stdout + r.stderr)
    final = snapshot(home)
    left = {os.path.relpath(p, home) for p in set(final) - set(before)} - {'.local', '.local/bin', '.local/share', '.local/share/applications'}
    expect(not left, f'rester: {sorted(left)}')
    gone = sorted(os.path.relpath(p, home) for p in set(before) - set(final))
    expect(not gone, f'borttagna: {gone}')
    full = diff_r(pristine, home)
    expect(not full, f'diff -r efter uninstall ej tom:\n{full[:500]}')
    expect(open(home + '/Videos/keep.mp4').read() == 'x', 'Videos rört')
    R.add('T-A3', 'GODKÄND', 'uninstall.sh --yes: `diff -r --no-dereference` mellan orörd kopia och hemträdet är tomt (hela trädet, inkl. Videos/keep.mp4)')
    usr_after = sh('find /usr/bin -type f -printf "%p %T@ %s\\n" | sort | md5sum').stdout
    expect(usr_before == usr_after, '/usr/bin ändrad')
    R.add('T-A5', 'GODKÄND', f'`diff -r` före/efter install (och efter uninstall) av kopior av ~/.config/hypr, ~/.config/omarchy, ~/.local/share/omarchy: tomt; /usr/bin fillista+md5 oförändrad. Obs: körs mot HOME-kopia, aldrig verkligt HOME')
    shutil.rmtree(pristine, ignore_errors=True)
    shutil.rmtree(home, ignore_errors=True)


@test('T-A4')
def t_keybind():
    """Genväg: bindings.lua utan avslutande newline; raden får inte smälta ihop med föregående; uninstall tar exakt bort den."""
    home = os.path.join(SCRATCH, 'mc-home-kb')
    shutil.rmtree(home, ignore_errors=True)
    os.makedirs(home + '/.config/hypr')
    orig = '-- user comment\no.bind("SUPER + I", "X", "y")\n-- sista raden utan newline'
    open(home + '/.config/hypr/bindings.lua', 'w').write(orig)
    env = dict(os.environ, HOME=home)
    r = subprocess.run([REPO + '/install.sh', '--keybind', '--no-bgremove'], env=env, capture_output=True, text=True)
    expect(r.returncode == 0, r.stderr)
    b = open(home + '/.config/hypr/bindings.lua').read()
    lines = b.split('\n')
    kb = [l for l in lines if l.endswith('-- multicam')]
    expect(len(kb) == 1 and kb[0].startswith('o.bind("SUPER + ALT + M"'), f'raden sammanfogad/fel: {lines}')
    expect('-- sista raden utan newline' in lines, f'föregående rad skadad: {lines}')
    # sämre fall: en tidigare version smälte ihop raden med kommentaren; uninstall ska ändå ta bort bara genvägen
    merged = orig + kb[0] + '\n'
    open(home + '/.config/hypr/bindings.lua', 'w').write(merged)
    r = subprocess.run([REPO + '/uninstall.sh', '--yes'], env=env, capture_output=True, text=True)
    b2 = open(home + '/.config/hypr/bindings.lua').read()
    expect('-- multicam' not in b2 and 'Multicam' not in b2, f'genväg kvar: {b2!r}')
    expect(b2.rstrip('\n') == orig.rstrip('\n') or b2.startswith(orig.rsplit('\n', 1)[0]), f'övriga rader ändrade: {b2!r}')
    expect('-- sista raden utan newline' in b2 and 'o.bind("SUPER + I", "X", "y")' in b2, b2)
    # och normalfallet: ren rad på egen rad, andra "-- multicam"-liknande rader som inte är vår bind rörs inte
    open(home + '/.config/hypr/bindings.lua', 'w').write('-- note about multicam\n' + kb[0] + '\n-- keep -- multicam-ish\n')
    subprocess.run([REPO + '/bin/multicam', 'uninstall', '--yes'], env=env, capture_output=True)
    b3 = open(home + '/.config/hypr/bindings.lua').read()
    expect(b3 == '-- note about multicam\n-- keep -- multicam-ish\n', repr(b3))
    R.add('T-A4', 'GODKÄND', 'bindings.lua utan avslutande newline: installerad rad hamnar på egen rad, föregående rad intakt; uninstall tar bort bara bind-raden även när den smält ihop med en kommentar; andra rader orörda')
    shutil.rmtree(home, ignore_errors=True)


# ---------------------------------------------------------------- B
@test('T-B2')
def t_b2():
    s = run_session('b2', cfg(shape='rect', ring='off') + 'CAM_B_DEV=\n')
    try:
        expect(s.wait_for('Kamera A', 5), 'form')
        scr0 = s.screen()
        seen = []
        # Rader: cam A, form, ring, kantfärg, tjocklek, cam B, bgsetup, mic, daudio, screen, start
        s.send(DOWN); s.send(RIGHT); seen.append(('form', 'cirkel' in s.screen() and '● cirkel' in s.screen()))
        s.send(DOWN); s.send(ENTER); seen.append(('ring', '● på' in s.screen().split('Ring')[1].split('\n')[0]))
        s.send(DOWN); s.send(RIGHT); seen.append(('färg', '#ff0000' in s.screen()))
        s.send('C'); s.send('00ff00'); s.send(ENTER); seen.append(('hex', '#00ff00' in s.screen()))
        s.send(DOWN); s.send(RIGHT); s.send(RIGHT); seen.append(('tjocklek', '6 px' in s.screen()))
        s.send(DOWN); s.send(RIGHT); seen.append(('kamera B', 'Kamera B' in s.screen() and (CAM_B_NAME.split()[0] in s.screen())))
        # B visar nu delrader + raden 'Bakgrund bort' (tillägget är inte installerat i testets HOME); hoppa till mic
        for _ in range(6): s.send(DOWN)
        s.send(RIGHT); seen.append(('mic', 'ingen' not in s.screen().split('Mikrofon')[1].split('\n')[0]))
        s.send(DOWN); s.send(ENTER); seen.append(('skrivbordsljud', '● på' in s.screen().split('Skrivbordsljud')[1].split('\n')[0]))
        s.send(DOWN); s.send(RIGHT); seen.append(('spela in', '● område' in s.screen()))
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
        expect('● cirkel' in scr and '● på' in scr.split('Ring')[1].split('\n')[0] and '#123abc' in scr and '5 px' in scr, scr)
        R.add('T-B4', 'GODKÄND', 'ändrade form/ring/färg/tjocklek, q, ny start: formuläret förifyllt (cirkel, ring på, #123abc, 5 px); config: ' +
              ' '.join(l for l in c.splitlines() if l.startswith('CAM_A_') and any(k in l for k in ('SHAPE', 'RING', 'COLOR', 'THICK'))))
    finally:
        s2.close()


@test('T-B5')
def t_b5():
    conf = cfg().replace(f'CAM_A_DEV={CAM_A_DEV}', 'CAM_A_DEV=/dev/video99').replace(CAM_A_NAME, 'Obefintlig Kamera 9000')
    h = make_home('b5', conf)
    s = Session(h, out_dir('b5'))
    try:
        s.wait_for('Kamera A', 5)
        scr = s.screen()
        expect('saknas: Obefintlig Kamera 9000' in scr, scr)
        line = [l for l in scr.splitlines() if 'Kamera A' in l][0]
        expect(CAM_A_NAME not in line and (not CAM_B_NAME or CAM_B_NAME not in line), line)
        s.send('q'); s.wait_exit(5)
        c = open(h + '/.config/multicam/config').read()
        expect('Obefintlig Kamera 9000' in c, 'sparad enhet försvann ur config')
        R.add('T-B5', 'GODKÄND', f'rad: "{line.strip()}"; ingen annan kamera vald; sparad enhet kvar i config')
    finally:
        s.close()


# ---------------------------------------------------------------- D
def mon_area_of(g):
    """Skärmytan (logiska px minus reserverat) för den monitor som innehåller fönstrets övre vänstra hörn."""
    for m in monitors():
        w, h = m['width'] / m['scale'], m['height'] / m['scale']
        if m.get('transform', 0) % 2: w, h = h, w
        if m['x'] <= g[0] < m['x'] + w and m['y'] <= g[1] < m['y'] + h:
            return mon_area(m['name'])
    return mon_area()


def mon_area(name=None):
    m = [x for x in monitors() if (x['name'] == name if name else x['focused'])][0]
    w, h = (m['height'], m['width']) if m.get('transform', 0) % 2 else (m['width'], m['height'])
    return (m['x'] + m['reserved'][0], m['y'] + m['reserved'][1],
            int(w / m['scale'] - m['reserved'][0] - m['reserved'][2]),
            int(h / m['scale'] - m['reserved'][1] - m['reserved'][3]))


@test('T-D3/4', 'T-D5')
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
        for _ in range(40): s.send('+', 0.12)
        wait_until(lambda: g()[2] == min(MW, MH), 5)
        if g()[2:] != (min(MW, MH),) * 2: errs.append(f'max: {g()} förväntat {min(MW, MH)}')
        # klamring: tillbaka till 300 px, sedan mot alla fyra kanter i flyttläge
        for _ in range(25): s.send('-', 0.1)
        for _ in range(3): s.send('+', 0.1)
        s.send('m', 0.3)
        if '[FLYTTA]' not in s.screen(): s.send('m', 0.3)
        cl = {}
        for name, key in [('vänster', SLEFT), ('upp', SUP), ('höger', SRIGHT), ('ner', SDOWN)]:
            for _ in range(max(MW, MH) // 100 + 2): s.send(key, 0.06)
            time.sleep(0.4)
            gx, gy, gw, gh = g()
            cl[name] = (gx, gy, gw, gh)
        gx, gy, gw, gh = cl['vänster']
        if gx != MX: errs.append(f'vänsterkant: x={gx} väntade {MX}')
        gx, gy, gw, gh = cl['upp']
        if gy != MY: errs.append(f'överkant: y={gy} väntade {MY}')
        gx, gy, gw, gh = cl['höger']
        if gx + gw != MX + MW: errs.append(f'högerkant: x+w={gx + gw} väntade {MX + MW}')
        gx, gy, gw, gh = cl['ner']
        if gy + gh != MY + MH: errs.append(f'nederkant: y+h={gy + gh} väntade {MY + MH}')
        for k, (gx, gy, gw, gh) in cl.items():
            if gx < MX or gy < MY or gx + gw > MX + MW or gy + gh > MY + MH:
                errs.append(f'utanför skärm efter {k}: {(gx, gy, gw, gh)} area {(MX, MY, MW, MH)}')
        # storleksökning vid kant får inte skjuta ut bilden
        s.send('1', 0.3)
        for _ in range(8): s.send('+', 0.1)
        time.sleep(0.4)
        gx, gy, gw, gh = g()
        if gx < MX or gy < MY or gx + gw > MX + MW or gy + gh > MY + MH: errs.append(f'utanför efter förstoring i hörn: {g()}')
        e_d34 = list(errs)
        R.add('T-D3/4', 'GODKÄND' if not e_d34 else 'UNDERKÄND',
              'pty + hyprctl clients -j: flytta 20/100 px, +/-/PgUp/PgDn ±10 %, storleksläge ±10/25 %, min 120, max ' + str(min(MW, MH)) +
              ', klamring mot alla fyra kanter (x=MX, y=MY, x+w=MX+MW, y+h=MY+MH), statusrad [FLYTTA]/[STORLEK]' + ('' if not e_d34 else ' FEL: ' + '; '.join(e_d34)))
        s.send('q'); s.wait_exit(5)
    finally:
        s.close()

    # ---- D5: båda kameror, Tab / Shift-Tab, siffror på B
    s = run_session('d5', cfg(shape='circle', ring='on', size=200) + 'CAM_A_RX=100\nCAM_A_RY=100\n'
                    + CAM_B_CFG + 'CAM_B_SHAPE=rect\nCAM_B_SIZE=180\nCAM_B_RX=600\nCAM_B_RY=100\n')
    errs = []
    try:
        start_to_preview(s)
        wait_until(lambda: len(geo()) == 2, 8)
        MX, MY, MW, MH = mon_area_of(geo()['MulticamA'])
        ga = lambda: geo()['MulticamA']; gb = lambda: geo()['MulticamB']
        expect('Vald kamera: A' in s.screen(), s.screen())
        # 1 på A -> nedre vänstra
        s.send('1', 0.5)
        a0, b0 = ga(), gb()
        exA = (MX + 20, MY + MH - 20 - a0[3])
        if abs(a0[0] - exA[0]) > 1 or abs(a0[1] - exA[1]) > 1: errs.append(f'A/1: {a0} väntade {exA}')
        s.send(TAB, 0.4)
        if 'Vald kamera: B' not in s.screen(): errs.append('Tab valde inte B')
        s.send('9', 0.5)
        a1, b1 = ga(), gb()
        if a1 != a0: errs.append(f'A flyttades när B styrdes: {a0} -> {a1}')
        exB = (MX + MW - 20 - b1[2], MY + 20)
        if abs(b1[0] - exB[0]) > 1 or abs(b1[1] - exB[1]) > 1: errs.append(f'B/9: {b1} väntade {exB}')
        s.send('\x1b[Z', 0.4)   # Shift-Tab tillbaka till A
        if 'Vald kamera: A' not in s.screen(): errs.append('Shift-Tab valde inte A')
        s.send('5', 0.5)
        a2, b2 = ga(), gb()
        exA = (MX + (MW - a2[2]) // 2, MY + (MH - a2[3]) // 2)
        if abs(a2[0] - exA[0]) > 2 or abs(a2[1] - exA[1]) > 2: errs.append(f'A/5: {a2} väntade {exA}')
        if b2 != b1: errs.append(f'B flyttades av A:s åtgärd: {b1} -> {b2}')
        s.send(TAB, 0.3); s.send(TAB, 0.3)
        if 'Vald kamera: A' not in s.screen(): errs.append('Tab två gånger ska ge A')
        R.add('T-D5', 'GODKÄND' if not errs else 'UNDERKÄND',
              'två kameror konfigurerade: Tab/Shift-Tab växlar vald kamera (statusrad), siffror 1/5 på A och 9 på B hamnar rätt (±1-2 px), den andra kameran rörs inte' + ('' if not errs else ' FEL ' + '; '.join(errs)))
        s.send('q'); s.wait_exit(5)
    finally:
        s.close()

@test('T-D7')
def t_d7():
    wake()
    before_active = active_addr()
    s = run_session('d7', cfg(shape='circle', ring='on'))
    try:
        start_to_preview(s)
        for k in [RIGHT, 's', 'r', '1']: s.send(k, 0.3)
        act = active_addr()
        R.add('T-D7', ('MANUELL' if before_active is None else 'GODKÄND' if act == before_active else 'UNDERKÄND'),
              f'hyprctl activewindow före={before_active} efter kamerastart+åtgärder={act}' +
              (' (inget aktivt fönster: låst session, kan inte avgöra fokus; se T-D7b)' if before_active is None else ''))
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
    conf = cfg(shape='circle', ring='on') + 'MIC=' + MIC + '\nMIC_DESC=testmic\nDESKTOP_AUDIO=off\n'
    conf = conf.replace('MIC=\n', '')
    o = out_dir('c4')
    s = run_session('c4', conf, o)
    try:
        before = default_source()
        start_recording(s)
        during = default_source()
        rec_ptr = open('/tmp/omarchy-screenrecord-filename').read().strip()
        t_start = os.stat('/tmp/omarchy-screenrecord-filename').st_mtime   # Omarchy bekräftar att inspelningen går
        time.sleep(7)
        s.send('q', 0.3)
        s.send('j', 0)
        wait_until(lambda: not gsr_pids(), 10, 0.02)
        t_stop = time.time()   # när gpu-screen-recorder avslutades
        expect(s.wait_for('klar', 25), s.screen())
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
        R.add('T-C3', 'GODKÄND' if (during == MIC and after == before) else 'UNDERKÄND',
              f'pactl get-default-source: före={before} under={during} efter={after} (förväntat under: {MIC}); ljudström i filen: {"audio" in codecs} (volymmätning av vald källa ej gjord: se rapport)')
        R.add('T-C4', 'GODKÄND' if (codecs.get('video') == 'h264' and codecs.get('audio') == 'aac' and 'mp4' in j['format']['format_name'] and abs(dur - (t_stop - t_start - 0.1)) <= 0.5) else 'UNDERKÄND',
              f'ffprobe: {codecs} format={j["format"]["format_name"]} längd={dur:.2f}s; uppmätt tid start (Omarchys pekarfil)->inspelaren avslutad {t_stop - t_start:.2f}s minus Omarchys 0,1 s trim = {t_stop - t_start - 0.1:.2f}s (tolerans ±0,5 s)')
        rx = r'^screenrecording-[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}_[0-9]{2}_[0-9]{2}\.mp4$'
        ok = re.match(rx, mp4[0]) and not any(re.match(r'screenrecording-\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.mp4', x) for x in files)
        R.add('T-C4b(namn)', 'GODKÄND' if ok else 'UNDERKÄND', f'filer i utmappen: {files}; Omarchys ursprungsnamn ({os.path.basename(rec_ptr)}) borta')
        # C1: bild vid 0,2 s
        png = EVID + '/c1-frame-0.2s.png'
        sh(f'ffmpeg -y -v error -ss 0.2 -i "{f}" -frames:v 1 -vf scale=640:-1 "{png}"')
        R.add('T-C1', 'MANUELL', f'bildruta vid 0,2 s sparad (ej incheckad): {png}; kamerabild i bildrutan granskas manuellt (se visual.py)')
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
        omarchy_name = f'screenrecording-{m[1]}_{m[2]}-{m[3]}-{m[4]}.mp4'
        ok = ((want[:-4] + '-2.mp4') in files and open(os.path.join(o, want)).read() == 'befintlig'
              and omarchy_name not in files and not os.path.exists(ptr))
        R.add('T-C4b', 'GODKÄND' if ok else 'UNDERKÄND', f'krock: {files}; befintlig fil orörd, ny fick -2; Omarchys namn ({omarchy_name}) finns inte kvar')
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
            gone = wait_until(lambda: not mc_clients() and not own_mpv_for_multicam(), 3, 0.02)
            dt = time.time() - t0
            s.wait_exit(15)
            res[f'E2 {name}'] = (bool(gone) and dt < 1.0, f'{dt:.2f}s', settle_clean(), os.listdir(o))
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
        gone = wait_until(lambda: not mc_clients() and not own_mpv_for_multicam(), 4, 0.02)
        dt = time.time() - t0
        ended = s.wait_for('klar', 20)
        p.wait(10)
        files = os.listdir(o)
        res['E2 --stop-recording utifrån'] = (bool(gone) and dt < 1.0 and ended, f'{dt:.2f}s', settle_clean(), files)
        s.send('n'); s.wait_exit(5)
    finally:
        s.close()
        shutil.rmtree(o, ignore_errors=True)
    bad = {k: v for k, v in res.items() if not (v[0] and not v[-1 if len(v) == 2 else 2])}
    ev = '; '.join(f'{k}: {v}' for k, v in res.items())
    R.add('T-E1b', 'GODKÄND' if res['E1 Esc (förhandsvisning)'][0] and not res['E1 Esc (förhandsvisning)'][1] else 'UNDERKÄND', ev.split('; E2')[0])
    R.add('T-E2', 'GODKÄND' if not bad or list(bad) == [] else 'UNDERKÄND', ev + (f' | FEL: {list(bad)}' if bad else ''))


@test('T-C3v')
def t_c3_volume():
    """Spela in 5 s med två olika mikrofoner och jämför ffmpeg volumedetect (Omarchys loudnorm jämnar ut, så mäter även rå bakgrund)."""
    wake()
    if not (MIC and MIC2):
        return R.add('T-C3v', 'MANUELL', 'kräver två mikrofoner (sätt MC_MIC och MC_MIC2)')
    mics = {'mic1': MIC, 'mic2': MIC2}
    vals = {}
    for name, mic in mics.items():
        o = out_dir('c3v')
        s = run_session('c3v', cfg() + 'MIC=' + mic + '\n', o)
        try:
            start_recording(s)
            during = default_source()
            time.sleep(5)
            s.send('q', 0.3); s.send('j', 0.3)
            expect(s.wait_for('klar', 25), s.screen())
            f = [x for x in os.listdir(o) if x.endswith('.mp4')][0]
            r = sh(f'ffmpeg -hide_banner -nostats -i "{o}/{f}" -af volumedetect -vn -f null - 2>&1 | grep -E "mean_volume|max_volume"')
            mv = re.search(r'mean_volume: (-?[0-9.]+)', r.stdout)
            vals[name] = (float(mv[1]) if mv else None, during == mic)
            s.send('n'); s.wait_exit(5)
        finally:
            s.close()
            shutil.rmtree(o, ignore_errors=True)
    v = {k: x[0] for k, x in vals.items()}
    ok_def = all(x[1] for x in vals.values())
    diff = abs(v['mic1'] - v['mic2']) if None not in (v['mic1'], v['mic2']) else None
    R.add('T-C3v', 'GODKÄND' if (ok_def and diff is not None and diff >= 10) else 'UNDERKÄND',
          f'mean_volume (dB) per vald mic: {v}; default-source under inspelning = vald mic för alla: {ok_def}; |mic1-mic2| = {diff}')


@test('T-E2s')
def t_e2_stress():
    """HUP/INT/TERM x10 under inspelning: fönster/mpv/mic städade < 1,0 s, filen avslutad och omdöpt."""
    wake()
    rows = {}
    for how in ('hup', 'int', 'term'):
        res = []
        for i in range(10):
            o = out_dir('e2s')
            s = run_session('e2s', cfg(), o)
            try:
                start_recording(s)
                time.sleep(1.5)
                # alla fönster/processer finns just nu
                t0 = time.time()
                if how == 'int': s.send('\x03', 0.0)
                else: s.kill(signal.SIGHUP if how == 'hup' else signal.SIGTERM)
                gone = wait_until(lambda: not mc_clients() and not own_mpv_for_multicam() and default_source() == ORIG_SRC, 3, 0.02)
                dt = time.time() - t0
                s.wait_exit(15)
                renamed = wait_until(lambda: [x for x in os.listdir(o) if re.match(r'screenrecording-\d{4}-\d\d-\d\d-\d\d_\d\d_\d\d\.mp4$', x)], 15)
                stopped = not gsr_pids()
                res.append((bool(gone) and dt < 1.0 and bool(renamed) and stopped, round(dt, 2)))
            finally:
                s.close()
                shutil.rmtree(o, ignore_errors=True)
            probs = settle_clean(3)
            if probs: res[-1] = (False, 'rest: ' + str(probs)[:80])
        rows[how] = res
    allok = all(ok for r in rows.values() for ok, _ in r)
    R.add('T-E2s', 'GODKÄND' if allok else 'UNDERKÄND',
          '10 körningar per signal; (ok, sekunder till städat): ' + '; '.join(f'{k}: max {max(t for _, t in v if isinstance(t, float)):.2f}s, ok={sum(ok for ok, _ in v)}/10' for k, v in rows.items()))


@test('T-B5b')
def t_identical_cams():
    """Två likadana kameror (samma namn, olika sökväg) får inte slås ihop; exakt sökväg+namn går före namnträff."""
    stub = os.path.join(SCRATCH, 'stub2'); os.makedirs(stub, exist_ok=True)
    open(stub + '/omarchy-capture-webcam-list', 'w').write(
        '#!/bin/bash\necho "/dev/video4  Twin Cam (usb-1):"\necho "/dev/video6  Twin Cam (usb-2):"\n')
    os.chmod(stub + '/omarchy-capture-webcam-list', 0o755)
    env = {'PATH': stub + ':' + os.environ['PATH']}
    conf = cfg().replace(f'CAM_A_DEV={CAM_A_DEV}', 'CAM_A_DEV=/dev/video6').replace(CAM_A_NAME, 'Twin Cam') \
        .replace('CAM_B_DEV=\nCAM_B_NAME=\n', 'CAM_B_DEV=/dev/video4\nCAM_B_NAME=Twin Cam\n')
    h = make_home('b5b', conf)
    s = Session(h, out_dir('b5b'), env=env)
    try:
        s.wait_for('Kamera A', 5)
        scr = s.screen()
        s.send('q'); s.wait_exit(5)
        c = open(h + '/.config/multicam/config').read()
        ok = 'CAM_A_DEV=/dev/video6' in c and 'CAM_B_DEV=/dev/video4' in c and 'saknas' not in scr
        # ändra inte: Kamera B-raden ska visa Twin Cam (inte "av"/saknas)
        lines = [l for l in scr.splitlines() if l.strip().startswith('Kamera')]
        R.add('T-B5b', 'GODKÄND' if ok and all('Twin Cam' in l for l in lines) else 'UNDERKÄND',
              f'A=/dev/video6, B=/dev/video4 (båda "Twin Cam") bevarade exakt: {lines}; config: ' + ' '.join(l for l in c.splitlines() if '_DEV=' in l))
    finally:
        s.close()


@test('T-D9')
def t_screen_focus():
    """Val av en annan skärm än den fokuserade: inspelningen sker på den skärmen och fokus (monitor + fönster) återställs."""
    wake()
    mons = monitors()
    foc = [m for m in mons if m['focused']][0]['name']
    other = [m for m in mons if m['name'] != foc and m['name'].startswith('DP')]
    if not other:
        R.add('T-D9', 'MANUELL', 'ingen andra DP-skärm tillgänglig'); return
    other = other[0]
    o = out_dir('d9')
    act0 = active_addr()
    s = run_session('d9', cfg() + 'SCREEN=' + other['name'] + '\n', o)
    try:
        start_recording(s)
        time.sleep(2)
        foc_after = [m for m in monitors() if m['focused']][0]['name']
        act1 = active_addr()
        s.send('q', 0.3); s.send('j', 0.3)
        expect(s.wait_for('klar', 25), s.screen())
        f = [x for x in os.listdir(o) if x.endswith('.mp4')][0]
        j = json.loads(sh(f'ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of json "{o}/{f}"').stdout)['streams'][0]
        exp = (other['width'], other['height'])  # råa lägesstorleken; roterad skärm (transform 1) ger omvänd ordning i filen
        if other.get('transform', 0) % 2: exp = (exp[1], exp[0])
        s.send('n'); s.wait_exit(5)
        ok = (j['width'], j['height']) == exp and foc_after == foc and act1 == act0
        R.add('T-D9', 'GODKÄND' if ok else 'UNDERKÄND',
              f'SCREEN={other["name"]} (fokuserad var {foc}): filens upplösning {j["width"]}x{j["height"]} (skärmen {exp[0]}x{exp[1]}); fokuserad monitor efter start={foc_after} (före {foc}); aktivt fönster före={act0} efter={act1}')
    finally:
        s.close()
        shutil.rmtree(o, ignore_errors=True)


def picker_stub(rect=None, cancel=False):
    d = os.path.join(SCRATCH, 'pickstub'); os.makedirs(d, exist_ok=True)
    open(d + '/omarchy-capture-region', 'w').write(
        f'#!/bin/bash\necho "$@" >> {d}/args\n[[ -f {d}/cancel ]] && exit 1\ncat {d}/rect\n')
    os.chmod(d + '/omarchy-capture-region', 0o755)
    for f in ('args', 'cancel', 'rect'):
        if os.path.exists(f'{d}/{f}'): os.unlink(f'{d}/{f}')
    if cancel: open(d + '/cancel', 'w').write('')
    if rect: open(d + '/rect', 'w').write(rect + '\n')
    return d


def focused_geo():
    m = [x for x in monitors() if x['focused']][0]
    return m['x'], m['y'], int(m['width'] / m['scale']), int(m['height'] / m['scale']), m['scale']


def region_test(tid, capture, rect, label_expect=None):
    wake()
    d = picker_stub(rect)
    o = out_dir('b6' + capture)
    rx, ry, rw, rh = [int(v) for v in re.match(r'(-?\d+),(-?\d+) (\d+)x(\d+)', rect).groups()]
    s = Session(make_home('b6' + capture, cfg(shape='circle', ring='on', size=200, extra='CAPTURE=' + capture + '\n')
                          + CAM_B_CFG + 'CAM_B_SHAPE=rect\nCAM_B_RING=on\nCAM_B_COLOR=#00aaff\nCAM_B_SIZE=160\n'
                          .replace('CAM_B_DEV=\nCAM_B_NAME=\n', '')),
                o, env={'PATH': d + ':' + os.environ['PATH']})
    try:
        start_to_preview(s)
        expect(wait_until(lambda: len(geo()) == 2, 8), 'kameror saknas')
        scr = s.screen()
        g = geo()
        inside = all(x >= rx and y >= ry and x + w <= rx + rw and y + h <= ry + rh for x, y, w, h in g.values())
        expect(inside, f'kameror utanför området {rect}: {g}')
        hdr = [l for l in scr.splitlines() if 'Område' in l or 'Fönster' in l]
        expect(hdr and (label_expect is None or label_expect in hdr[0]), f'rubrik: {hdr}\n{scr}')
        # numpad-snap och maxstorlek ska klampas mot området
        s.send('9', 0.4)
        for _ in range(30): s.send('+', 0.05)
        time.sleep(0.4)
        g = geo()
        inside2 = all(x >= rx and y >= ry and x + w <= rx + rw and y + h <= ry + rh for x, y, w, h in g.values())
        expect(inside2, f'kameror utanför efter snap/förstoring: {g}')
        s.send('1', 0.3); s.send('+', 0.2)
        s.send(ENTER, 0.3)
        expect(s.wait_for('SPELAR IN', 25), s.screen())
        shim_during = os.path.exists(f'{s.home}/../../run/user/1000/multicam')  # (ej relevant)
        time.sleep(4)
        run = '/run/user/1000/multicam'
        sessions = [x for x in os.listdir(run) if x.startswith('s.')]
        shim_left = [x for x in sessions if os.path.exists(f'{run}/{x}/shim')]
        frame_g = geo()
        grim('/tmp/claude-1000/b6-live.png')
        s.send('q', 0.3); s.send('j', 0.3)
        expect(s.wait_for('klar', 25), s.screen())
        f = [x for x in os.listdir(o) if x.endswith('.mp4')]
        expect(len(f) == 1, os.listdir(o))
        fp = os.path.join(o, f[0])
        j = json.loads(sh(f'ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of json "{fp}"').stdout)['streams'][0]
        out = f'{SCRATCH}/{tid}-frame.png'
        sh(f'ffmpeg -y -v error -ss 2 -i "{fp}" -frames:v 1 {out}')
        args = open(d + '/args').read().strip().splitlines() if os.path.exists(d + '/args') else []
        s.send('n'); s.wait_exit(5)
        probs = settle_clean()
        return dict(w=j['width'], h=j['height'], rect=(rx, ry, rw, rh), frame=out, args=args, cams=frame_g, shim_left=shim_left, probs=probs, files=os.listdir(o))
    finally:
        s.close()
        shutil.rmtree(o, ignore_errors=True)


@test('T-B6a')
def t_b6a():
    fx, fy, fw, fh, sc = focused_geo()
    rect = f'{fx + 300},{fy + 200} 1200x800'
    r = region_test('T-B6a', 'region', rect, 'Område 1200x800')
    R.add('T-B6a', 'GODKÄND' if not r['probs'] and not r['shim_left'] and r['args'] and r['args'][0].startswith('region') else 'UNDERKÄND',
          f'stub-väljare (anrop: {r["args"]}) gav {rect}; kameror inuti området före och efter snap/förstoring; MP4 {r["w"]}x{r["h"]} (område 1200x800 x skala {sc} = {int(1200*sc)}x{int(800*sc)}); '
          f'shim kvar efter start: {r["shim_left"]}; städat: {r["probs"] or "ja"}; bildruta (ej incheckad): {r["frame"]}')


@test('T-B6b')
def t_b6b():
    wake()
    fx, fy, fw, fh, sc = focused_geo()
    cands = [c for c in clients() if not c['class'].startswith('Multicam') and c['size'][0] >= 300 and c['size'][1] >= 300
             and fx <= c['at'][0] < fx + fw and fy <= c['at'][1] < fy + fh]
    expect(cands, 'inget fönster på fokuserad skärm')
    c = cands[0]
    rect = f'{c["at"][0]},{c["at"][1]} {c["size"][0]}x{c["size"][1]}'
    r = region_test('T-B6b', 'window', rect, 'Fönster: ' + c['class'])
    R.add('T-B6b', 'GODKÄND' if not r['probs'] and r['args'] and r['args'][0].startswith('windows') else 'UNDERKÄND',
          f'fönster {c["class"]} {rect}; väljare anropad med "{r["args"]}"; rubrik "Fönster: {c["class"]}"; MP4 {r["w"]}x{r["h"]} (förväntat {int(c["size"][0]*sc)}x{int(c["size"][1]*sc)} vid skala {sc}); städat: {r["probs"] or "ja"}')


@test('T-B6c')
def t_b6c():
    wake()
    d = picker_stub(cancel=True)
    o = out_dir('b6c')
    s = Session(make_home('b6c', cfg(extra='CAPTURE=region\n')), o, env={'PATH': d + ':' + os.environ['PATH']})
    try:
        s.wait_for('Kamera A', 5)
        s.send(F5, 0.5)
        got = s.wait_for('Valet avbröts', 5)
        scr = s.screen()
        ok = got and 'Kamera A' in scr and not mc_clients() and not gsr_pids() and not [x for x in os.listdir(o)]
        # formuläret ska fortfarande styras: växla tillbaka till hel skärm och förhandsvisa
        s.send(UP, 0.2)
        R.add('T-B6c', 'GODKÄND' if ok else 'UNDERKÄND', f'väljaren avbröt (exit 1): meddelande "Valet avbröts", formuläret kvar, inga kamerafönster/inspelare, utmapp tom={os.listdir(o) == []}')
        s.send('q'); s.wait_exit(5)
    finally:
        s.close()
        shutil.rmtree(o, ignore_errors=True)


def conf_kv(home):
    return dict(l.split('=', 1) for l in open(home + '/.config/multicam/config').read().splitlines() if '=' in l)


@test('T-B7')
def t_persist():
    """Inställningar sparas direkt när de ändras (inte bara vid avslut) och används vid nästa start (hel skärm och område)."""
    wake()
    h = make_home('b7', cfg(shape='circle', ring='on', size=200) + 'CAM_A_RX=100\nCAM_A_RY=100\nCAM_B_DEV=\nCAM_B_NAME=\n')
    o = out_dir('b7')
    s = Session(h, o)
    try:
        s.wait_for('Kamera A', 5)
        s.send(DOWN, 0.3); s.send(RIGHT, 0.3)            # form -> rektangel
        kv = conf_kv(h)
        expect(kv.get('CAM_A_SHAPE') == 'rect', f'formuläret: ändringen sparades inte direkt: {kv.get("CAM_A_SHAPE")}')
        s.send(F5)
        expect(s.wait_for('FÖRHANDSVISNING', 15), s.screen())
        expect(wait_until(lambda: 'MulticamA' in geo(), 8), 'kamera saknas')
        s.send(RIGHT, 0.3); s.send(RIGHT, 0.3); s.send(DOWN, 0.3); s.send('+', 0.3)
        time.sleep(1.6)                                    # sparas när det varit tyst en stund
        g1 = geo()['MulticamA']
        kv = conf_kv(h)                                    # TUI:t kör fortfarande
        expect(kv.get('CAM_A_SIZE') == str(g1[3]) and kv.get('CAM_A_RX') != '100', f'förhandsvisning: sparades inte direkt: {kv} geo={g1}')
        s.send('q'); expect(s.wait_exit(8), 'avslutade inte')
    finally:
        s.close()
    expect(not settle_clean(), settle_clean())
    s = Session(h, o)
    try:
        s.wait_for('Kamera A', 5)
        expect('● rektangel' in s.screen(), s.screen())
        s.send(F5)
        expect(s.wait_for('FÖRHANDSVISNING', 15), s.screen())
        expect(wait_until(lambda: geo().get('MulticamA') == g1, 8), f'ny start: {geo().get("MulticamA")} väntade {g1}')
        s.send('q'); expect(s.wait_exit(8), 'avslutade inte')
    finally:
        s.close()
        shutil.rmtree(o, ignore_errors=True)
    expect(not settle_clean(), settle_clean())
    R.add('T-B7', 'GODKÄND', f'form (rektangel) och kamerans position/storlek {g1} fanns i config medan TUI:t körde; ny start: formuläret förifyllt och kameran på samma plats')


@test('T-B6d')
def t_b6d():
    """Område: senaste området sparas och återanvänds vid F5 utan väljaren; raden Område kan välja nytt."""
    wake()
    mx, my, mw, mh, sc = focused_geo()
    rect = f'{mx + 100},{my + 80} 900x600'
    d = picker_stub(rect)
    o = out_dir('b6d')
    h = make_home('b6d', cfg(shape='circle', ring='on', size=200, extra='CAPTURE=region\n') + 'CAM_B_DEV=\nCAM_B_NAME=\n')
    env = {'PATH': d + ':' + os.environ['PATH']}
    calls = lambda: len(open(d + '/args').read().splitlines()) if os.path.exists(d + '/args') else 0
    try:
        s = Session(h, o, env=env)
        start_to_preview(s)
        expect(calls() == 1, f'väljaren anropades {calls()} gånger första gången')
        s.send('q'); expect(s.wait_exit(8), 'avslutade inte')
        s.close()
        kv = conf_kv(h)
        expect(kv.get('LAST_AREA') == f'{mx + 100},{my + 80},900,600', kv.get('LAST_AREA'))
        s = Session(h, o, env=env)
        s.wait_for('Kamera A', 5)
        scr = s.screen()
        expect('senaste: 900x600' in scr, scr)
        start_to_preview(s)
        hdr = [l for l in s.screen().splitlines() if 'Område 900x600' in l]
        expect(calls() == 1 and hdr, f'andra gången: väljaren anropad {calls()} ggr, rubrik {hdr}')
        g = geo()['MulticamA']
        expect(g[0] >= mx + 100 and g[1] >= my + 80 and g[0] + g[2] <= mx + 1000 and g[1] + g[3] <= my + 680, f'kameran utanför området: {g}')
        s.send('q'); expect(s.wait_exit(8), 'avslutade inte')
        s.close()
        # välj nytt via raden Område (Enter växlar) -> väljaren körs igen
        s = Session(h, o, env=env)
        s.wait_for('Kamera A', 5)
        while 'senaste:' not in [l for l in s.screen().splitlines() if '▌' in l][0]:
            s.send(DOWN, 0.15)
        s.send(ENTER, 0.3)
        expect('● välj nytt' in s.screen(), s.screen())
        start_to_preview(s)
        expect(calls() == 2, f'välj nytt: väljaren anropad {calls()} ggr')
        s.send('q'); expect(s.wait_exit(8), 'avslutade inte')
        s.close()
    finally:
        s.close()
        shutil.rmtree(o, ignore_errors=True)
    expect(not settle_clean(), settle_clean())
    R.add('T-B6d', 'GODKÄND', f'senaste området {rect} sparades; ny start: raden "senaste: 900x600" och F5 utan väljare (rubrik Område 900x600, kameran inuti); "välj nytt" kör väljaren igen')


@test('T-R1')
def t_enter_only():
    """Regression: i förhandsvisningen startar bara Enter inspelningen (inte F5/andra tangenter); kameraregeln har no_anim."""
    wake()
    src = open(BIN).read()
    expect('no_anim=true' in src, 'no_anim saknas i fönsterregeln')
    s = run_session('r1', cfg(shape='circle'))
    try:
        start_to_preview(s)
        s.send(F5, 0.6); s.send(' ', 0.4); s.send('x', 0.3)
        time.sleep(1.5)
        ok1 = not gsr_pids() and 'FÖRHANDSVISNING' in s.screen()
        s.send(ENTER, 0.3)
        ok2 = s.wait_for('SPELAR IN', 20) and bool(wait_until(gsr_pids, 5))
        time.sleep(1.5)
        s.send('q', 0.3); s.send('j', 0.3); s.wait_for('klar', 25); s.send('n'); s.wait_exit(5)
        R.add('T-R1', 'GODKÄND' if ok1 and ok2 else 'UNDERKÄND', f'F5/mellanslag/x i förhandsvisning startade inget (gsr={bool(ok1)}); Enter startade; no_anim=true i regeln')
    finally:
        s.close()
        shutil.rmtree(os.path.join(SCRATCH, 'out-r1'), ignore_errors=True)


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
        R.add('T-E3', 'MANUELL', f'gpu-screen-recorder kör under inspelning={gsr} (Omarchys ikon visas av det); indicators refresh: {r.stdout.strip()}; ikonens utseende granskas med tests/visual.py record (e3-bar*.png); verkligt musklick: M')
        s.send('n'); s.wait_exit(5)
    finally:
        s.close()
        shutil.rmtree(o, ignore_errors=True)


@test('T-X1', 'T-X2')
def t_x():
    wake()
    conf = cfg(shape='circle', ring='on') + CAM_B_CFG + 'CAM_B_SHAPE=rect\nCAM_B_RING=on\nCAM_B_COLOR=#00aaff\n' + 'MIC=' + MIC + '\n'
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
              f'två kameror ({alive_cams}) + cirkel + mic, 30 s: {dur:.1f}s, {nb} bildrutor ({nb / dur:.1f} fps av 60 begärda), ffmpeg-avkodning utan fel={not play}; innehållet granskas manuellt (bildruta ej incheckad)')
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
    subprocess.run([REPO + '/install.sh', '--yes', '--no-bgremove'], env=env, capture_output=True)
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
    subprocess.run([REPO + '/install.sh', '--yes', '--no-bgremove'], env=env, capture_output=True)
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
    pr = subprocess.Popen([py, REPO + '/lib/bg.py', '--dev', CAM_A_DEV, '--w', '640', '--h', '360', '--model', model,
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
          f'bg.py --threads 2, kamera A 640x360, {dt:.1f} s: {frames:.0f} RGBA-rutor = {fps:.1f} fps, CPU ca {cpu:.0f} % av en kärna (python+ffmpeg); stderr: {err.strip()[-120:]}')
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


@test('T-L1')
def t_language():
    """Språkval: engelska som standard, svenska när systemets språk är svenska; MULTICAM_LANG och LC_ALL väger tyngst."""
    def usage(**e):
        env = {k: v for k, v in os.environ.items() if k not in ('MULTICAM_LANG', 'LC_ALL', 'LC_MESSAGES', 'LANG')}
        env.update(e)
        return subprocess.run([BIN, '--help'], env=env, capture_output=True, text=True).stdout
    en, sv = 'start the TUI', 'starta TUI:t'
    cases = {'LANG=en_US.UTF-8': (dict(LANG='en_US.UTF-8'), en), 'LANG=sv_SE.UTF-8': (dict(LANG='sv_SE.UTF-8'), sv),
             'ingen LANG': ({}, en), 'LC_ALL=sv_SE väger över LANG=en': (dict(LC_ALL='sv_SE.UTF-8', LANG='en_US.UTF-8'), sv),
             'MULTICAM_LANG=en väger över LANG=sv': (dict(MULTICAM_LANG='en', LANG='sv_SE.UTF-8'), en)}
    bad = [k for k, (e, want) in cases.items() if want not in usage(**e)]
    expect(not bad, f'fel språk för: {bad}')
    # TUI på engelska
    s = Session(make_home('l1', cfg()), out_dir('l1'), env={'MULTICAM_LANG': 'en'})
    try:
        s.wait_for('Camera A', 5)
        scr = s.screen()
        expect('Preview cameras' in scr and 'Microphone' in scr and 'Kamera' not in scr, scr)
        s.send('q'); s.wait_exit(5)
    finally:
        s.close()
    R.add('T-L1', 'GODKÄND', 'språkval: ' + ', '.join(cases) + '; TUI på engelska (Camera A, Microphone, Preview cameras) utan svenska rester')


@test('T-U1')
def t_update():
    """Uppdatering mot ett lokalt git-förråd: ingen uppdatering -> check-update 1; ny commit -> check-update 0; update --yes hämtar och installerar."""
    base = os.path.join(SCRATCH, 'upd'); shutil.rmtree(base, ignore_errors=True); os.makedirs(base)
    git = lambda *a, cwd=base: subprocess.run(['git', *a], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()
    git('init', '-q', '--bare', '-b', 'main', 'origin.git')
    git('clone', '-q', REPO, 'clone')
    git('remote', 'set-url', 'origin', base + '/origin.git', cwd=base + '/clone')
    for f in ('bin', 'lib', 'install.sh', 'uninstall.sh', 'multicam.desktop'):   # arbetskopian (kan vara ocommitad)
        subprocess.run(['cp', '-a', f'{REPO}/{f}', base + '/clone/'], check=True)
    git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qam', 'working copy', '--allow-empty', cwd=base + '/clone')
    git('push', '-q', 'origin', 'HEAD:main', cwd=base + '/clone')
    home = os.path.join(base, 'home'); os.makedirs(home)
    env = dict(os.environ, HOME=home)
    mc = home + '/.local/bin/multicam'
    run = lambda *a: subprocess.run(a, env=env, capture_output=True, text=True)
    r = run(base + '/clone/install.sh', '--yes', '--no-bgremove'); expect(r.returncode == 0, r.stdout + r.stderr)
    expect(run(mc, 'check-update').returncode == 1, 'check-update: uppdatering trots att inget ändrats')
    u = run(mc, 'update', '--yes'); expect('uppdaterat' in u.stdout, 'update när allt är aktuellt: ' + u.stdout + u.stderr)
    c = base + '/clone'
    s = re.sub(r'(?m)^VERSION=\S+', 'VERSION=9.9.9', open(c + '/bin/multicam').read())
    open(c + '/bin/multicam', 'w').write(s)
    git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qam', 'bump', cwd=c); git('push', '-q', 'origin', 'HEAD:main', cwd=c)
    expect(run(mc, 'check-update').returncode == 0, 'check-update missar ny commit')
    r = run(mc, 'update', '--yes'); expect(r.returncode == 0, r.stdout + r.stderr)
    expect('9.9.9' in run(mc, '--version').stdout, 'ny version inte installerad')
    expect(run(mc, 'check-update').returncode == 1, 'check-update efter uppdatering')
    R.add('T-U1', 'GODKÄND', 'lokalt git-förråd som origin: check-update 1 -> ny commit -> 0 -> update --yes installerar 9.9.9 -> check-update 1 igen; HOME-kopia, aldrig verkligt HOME')
    shutil.rmtree(base, ignore_errors=True)


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
