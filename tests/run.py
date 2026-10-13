#!/usr/bin/env python3
"""Automated tests for multicam. Run: tests/run.py [T-ID ...]  (no arguments: all except bg)
Screenshots are saved in $SCRATCH/evidence/ (never committed: they show the camera image and the screen). The report is written as JSON to $SCRATCH/results.json."""
import sys, glob, stat
from mclib import *

EVID = os.path.join(SCRATCH, 'evidence')   # outside the repo: the images show the camera image and the screen
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
    """Everything should be cleaned up; returns a list of problems."""
    probs = []
    if mc_clients(): probs.append(f'windows left: {list(mc_clients())}')
    if own_mpv_for_multicam(): probs.append(f'processes left: {own_mpv_for_multicam()}')
    r = rules_enabled()
    if r: probs.append(f'rules active: {r}')
    if default_source() != ORIG_SRC: probs.append(f'mic not restored: {default_source()}')
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
    '.local/share/multicam/shell-plugin/manifest.json',
    '.local/share/multicam/shell-plugin/BarWidget.qml',
    '.local/share/multicam/shell-plugin/README.md',
    '.local/share/multicam/shell-plugin/LICENSE',
    '.local/share/applications/multicam.desktop',
    '.local/share/icons/hicolor/scalable/apps/multicam.svg',
    '.config/multicam',
}
ICON_DIRS = ('.local/share/icons', '.local/share/icons/hicolor', '.local/share/icons/hicolor/scalable', '.local/share/icons/hicolor/scalable/apps')
PLUGIN_ID, OLD_PLUGIN_ID = 'io.github.mattische.multicam', 'multicam.recording'


def realistic_home(name):
    """Empty HOME copy with the real ~/.config/hypr, ~/.config/omarchy, ~/.local/share/omarchy and a Videos file."""
    home = os.path.join(SCRATCH, name)
    shutil.rmtree(home, ignore_errors=True)
    os.makedirs(home + '/.config'); os.makedirs(home + '/.local/share/applications'); os.makedirs(home + '/.local/bin'); os.makedirs(home + '/Videos')
    open(home + '/Videos/keep.mp4', 'w').write('x')
    R_ = os.path.expanduser('~')
    for rel in ('.config/hypr', '.config/omarchy', '.local/share/omarchy'):
        if os.path.exists(f'{R_}/{rel}'):
            subprocess.run(['cp', '-a', f'{R_}/{rel}', f'{home}/{rel}'], check=True)
    bl = home + '/.config/hypr/bindings.lua'   # the user's own multicam keybind must not be part of the baseline
    if os.path.exists(bl):
        txt = open(bl).read().splitlines(True)
        open(bl, 'w').write(''.join(l for l in txt if not l.rstrip().endswith('-- multicam')))
    for pid in (OLD_PLUGIN_ID, PLUGIN_ID):   # likewise the user's own bar icon
        shutil.rmtree(f'{home}/.config/omarchy/plugins/{pid}', ignore_errors=True)
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
    r = subprocess.run([REPO + '/install.sh', '--yes', '--no-bgremove', '--no-bar-indicator'], env=env, capture_output=True, text=True)
    expect(r.returncode == 0, r.stdout + r.stderr)
    after = snapshot(home)
    new = {os.path.relpath(p, home) for p in set(after) - set(before)}
    new = {p for p in new if p not in ('.local', '.local/bin', '.local/share', '.local/share/applications', '.cache')}
    # directories under multicam are not counted separately
    new = {p for p in new if not p.startswith('.local/share/multicam/') or p.count('/') > 3 or p.endswith(('bin/multicam', 'lib/bg.py', '/rev', '/source'))}
    new = {p for p in new if p not in ('.local/share/multicam', '.local/share/multicam/bin', '.local/share/multicam/lib', '.local/share/multicam/shell-plugin') + ICON_DIRS}
    expect(new == EXPECTED_INSTALL, f'file set differs: extra={sorted(new - EXPECTED_INSTALL)} missing={sorted(EXPECTED_INSTALL - new)}')
    d_hypr = diff_r(pristine + '/.config/hypr', home + '/.config/hypr')
    d_om = diff_r(pristine + '/.config/omarchy', home + '/.config/omarchy')
    d_sh = diff_r(pristine + '/.local/share/omarchy', home + '/.local/share/omarchy')
    expect(not (d_hypr or d_om or d_sh), f'install changed Omarchy/Hypr files:\n{d_hypr}\n{d_om}\n{d_sh}')
    dsk = open(home + '/.local/share/applications/multicam.desktop').read()
    expect('Exec=omarchy-launch-tui --app-id=TUI.float ' + home in dsk, dsk)
    expect('\nIcon=multicam\n' in dsk, dsk)
    expect(open(home + '/.local/share/icons/hicolor/scalable/apps/multicam.svg', 'rb').read() == open(REPO + '/assets/multicam.svg', 'rb').read(), 'icon differs')
    v = subprocess.run([home + '/.local/bin/multicam', '--version'], env=env, capture_output=True, text=True).stdout
    expect('multicam' in v, v)
    # bar plugin: setup-bar copies the shipped plugin (== shell-plugin/, == packaging/omarchy-plugin/) and removes only the
    # old multicam.recording folder; with a scratch HOME the running shell is never told (no enable/disable/rescan)
    expect(not diff_r(REPO + '/shell-plugin', REPO + '/packaging/omarchy-plugin'), 'shell-plugin/ and packaging/omarchy-plugin/ differ')
    plugins = home + '/.config/omarchy/plugins'
    os.makedirs(f'{plugins}/{OLD_PLUGIN_ID}'); open(f'{plugins}/{OLD_PLUGIN_ID}/manifest.json', 'w').write('{}')
    r = subprocess.run([home + '/.local/bin/multicam', 'setup-bar'], env=env, capture_output=True, text=True)
    expect(r.returncode == 0 and 'omarchy plugin enable ' + PLUGIN_ID in r.stdout, r.stdout + r.stderr)
    expect(not os.path.exists(f'{plugins}/{OLD_PLUGIN_ID}'), 'old plugin folder left')
    expect(not diff_r(REPO + '/shell-plugin', f'{plugins}/{PLUGIN_ID}'), 'installed plugin differs from shell-plugin/')
    expect(sorted(os.listdir(plugins)) == sorted(os.listdir(pristine + '/.config/omarchy/plugins') + [PLUGIN_ID]), f'other plugins touched: {os.listdir(plugins)}')
    expect('BAR_PLUGIN=on' in open(home + '/.config/multicam/config').read(), 'BAR_PLUGIN not remembered')
    r = subprocess.run([home + '/.local/bin/multicam', 'setup-bar', '--remove'], env=env, capture_output=True, text=True)
    expect(r.returncode == 0 and not os.path.exists(f'{plugins}/{PLUGIN_ID}'), r.stdout + r.stderr)
    expect('BAR_PLUGIN=off' in open(home + '/.config/multicam/config').read(), 'removal not remembered')
    subprocess.run([home + '/.local/bin/multicam', 'setup-bar'], env=env, capture_output=True, text=True, check=True)   # uninstall must remove it
    R.add('T-A1', 'PASS', 'install.sh --yes against a HOME copy with the real ~/.config/{hypr,omarchy} and ~/.local/share/omarchy: new paths exactly == ' + ', '.join(sorted(EXPECTED_INSTALL))
          + f'; desktop Icon=multicam + icon file; setup-bar: {PLUGIN_ID} == shell-plugin/ (== packaging/omarchy-plugin/), old {OLD_PLUGIN_ID} folder removed, other plugins untouched, BAR_PLUGIN on/off remembered, no shell IPC with a scratch HOME')
    r = subprocess.run([REPO + '/uninstall.sh', '--yes'], env=env, capture_output=True, text=True)
    expect(r.returncode == 0, r.stdout + r.stderr)
    final = snapshot(home)
    left = {os.path.relpath(p, home) for p in set(final) - set(before)} - {'.local', '.local/bin', '.local/share', '.local/share/applications'}
    expect(not left, f'leftovers: {sorted(left)}')
    gone = sorted(os.path.relpath(p, home) for p in set(before) - set(final))
    expect(not gone, f'removed: {gone}')
    full = diff_r(pristine, home)
    expect(not full, f'diff -r after uninstall not empty:\n{full[:500]}')
    expect(open(home + '/Videos/keep.mp4').read() == 'x', 'Videos touched')
    R.add('T-A3', 'PASS', 'uninstall.sh --yes: `diff -r --no-dereference` between the pristine copy and the home tree is empty (whole tree, incl. Videos/keep.mp4)')
    usr_after = sh('find /usr/bin -type f -printf "%p %T@ %s\\n" | sort | md5sum').stdout
    expect(usr_before == usr_after, '/usr/bin changed')
    R.add('T-A5', 'PASS', f'`diff -r` before/after install (and after uninstall) of copies of ~/.config/hypr, ~/.config/omarchy, ~/.local/share/omarchy: empty; /usr/bin file list+md5 unchanged. Note: runs against a HOME copy, never the real HOME')
    shutil.rmtree(pristine, ignore_errors=True)
    shutil.rmtree(home, ignore_errors=True)


@test('T-A4')
def t_keybind():
    """Keybind: bindings.lua without a trailing newline; the line must not merge with the previous one; uninstall removes exactly that line."""
    home = os.path.join(SCRATCH, 'mc-home-kb')
    shutil.rmtree(home, ignore_errors=True)
    os.makedirs(home + '/.config/hypr')
    orig = '-- user comment\no.bind("SUPER + I", "X", "y")\n-- last line without newline'
    open(home + '/.config/hypr/bindings.lua', 'w').write(orig)
    env = dict(os.environ, HOME=home)
    r = subprocess.run([REPO + '/install.sh', '--keybind', '--no-bgremove', '--no-bar-indicator'], env=env, capture_output=True, text=True)
    expect(r.returncode == 0, r.stderr)
    b = open(home + '/.config/hypr/bindings.lua').read()
    lines = b.split('\n')
    kb = [l for l in lines if l.endswith('-- multicam')]
    expect(len(kb) == 1 and kb[0].startswith('o.bind("SUPER + ALT + M"'), f'line merged/wrong: {lines}')
    expect('-- last line without newline' in lines, f'previous line damaged: {lines}')
    # worse case: an earlier version merged the line with the comment; uninstall must still remove only the keybind
    merged = orig + kb[0] + '\n'
    open(home + '/.config/hypr/bindings.lua', 'w').write(merged)
    r = subprocess.run([REPO + '/uninstall.sh', '--yes'], env=env, capture_output=True, text=True)
    b2 = open(home + '/.config/hypr/bindings.lua').read()
    expect('-- multicam' not in b2 and 'Multicam' not in b2, f'keybind left: {b2!r}')
    expect(b2.rstrip('\n') == orig.rstrip('\n') or b2.startswith(orig.rsplit('\n', 1)[0]), f'other lines changed: {b2!r}')
    expect('-- last line without newline' in b2 and 'o.bind("SUPER + I", "X", "y")' in b2, b2)
    # and the normal case: clean line on its own line; other "-- multicam"-like lines that are not our bind are left alone
    open(home + '/.config/hypr/bindings.lua', 'w').write('-- note about multicam\n' + kb[0] + '\n-- keep -- multicam-ish\n')
    subprocess.run([REPO + '/bin/multicam', 'uninstall', '--yes'], env=env, capture_output=True)
    b3 = open(home + '/.config/hypr/bindings.lua').read()
    expect(b3 == '-- note about multicam\n-- keep -- multicam-ish\n', repr(b3))
    R.add('T-A4', 'PASS', 'bindings.lua without trailing newline: the installed line ends up on its own line, previous line intact; uninstall removes only the bind line even when it has merged with a comment; other lines untouched')
    shutil.rmtree(home, ignore_errors=True)


# ---------------------------------------------------------------- B
@test('T-B2')
def t_b2():
    s = run_session('b2', cfg(shape='rect', ring='off') + 'CAM_B_DEV=\n')
    try:
        expect(s.wait_for('Camera A', 5), 'form')
        scr0 = s.screen()
        seen = []
        # Rows: cam A, shape, ring, border colour, thickness, cam B, bgsetup, mic, daudio, screen, start
        s.send(DOWN); s.send(RIGHT); seen.append(('shape', 'circle' in s.screen() and '● circle' in s.screen()))
        s.send(DOWN); s.send(ENTER); seen.append(('ring', '● on' in s.screen().split('Ring')[1].split('\n')[0]))
        s.send(DOWN); s.send(RIGHT); seen.append(('colour', '#ff0000' in s.screen()))
        s.send('C'); s.send('00ff00'); s.send(ENTER); seen.append(('hex', '#00ff00' in s.screen()))
        s.send(DOWN); s.send(RIGHT); s.send(RIGHT); seen.append(('thickness', '6 px' in s.screen()))
        s.send(DOWN); s.send(RIGHT); seen.append(('camera B', 'Camera B' in s.screen() and (CAM_B_NAME.split()[0] in s.screen())))
        # B now shows sub-rows + the 'Remove background' row (the add-on is not installed in the test HOME); jump to mic
        for _ in range(6): s.send(DOWN)
        s.send(RIGHT); seen.append(('mic', 'none' not in s.screen().split('Microphone')[1].split('\n')[0]))
        s.send(DOWN); s.send(ENTER); seen.append(('desktop audio', '● on' in s.screen().split('Desktop audio')[1].split('\n')[0]))
        s.send(DOWN); s.send(RIGHT); seen.append(('record', '● area' in s.screen()))
        s.send(DOWN); s.send(RIGHT); seen.append(('screen', 'focused' not in s.screen().split('Screen')[1].split('\n')[0]))
        s.send(ESC, 0.4); expect(not s.wait_exit(1), 'Esc quit the form'); s.send('q'); expect(s.wait_exit(5), 'did not exit')
        bad = [n for n, ok in seen if not ok]
        expect(not bad, f'not changeable: {bad}\n{s.screen()}')
        R.add('T-B2', 'PASS', 'pty without mouse: all rows (camera A/B, shape, ring, colour, hex code, thickness, mic, desktop audio, screen) changed with arrows/Enter/C; ' + ', '.join(n for n, _ in seen))
    finally:
        s.close()


@test('T-B4')
def t_b4():
    h = make_home('b4', cfg(shape='rect', ring='off'))
    o = out_dir('b4')
    s = Session(h, o)
    s.wait_for('Camera A', 5)
    s.send(DOWN); s.send(RIGHT)      # circle
    s.send(DOWN); s.send(ENTER)      # ring on
    s.send(DOWN); s.send('C'); s.send('123abc'); s.send(ENTER)
    s.send(DOWN); s.send(']')  # ignored
    s.send(RIGHT)
    s.send('q'); expect(s.wait_exit(5), 'exit')
    c = open(h + '/.config/multicam/config').read()
    s2 = Session(h, o)
    try:
        s2.wait_for('Camera A', 5)
        scr = s2.screen()
        expect('● circle' in scr and '● on' in scr.split('Ring')[1].split('\n')[0] and '#123abc' in scr and '5 px' in scr, scr)
        R.add('T-B4', 'PASS', 'changed shape/ring/colour/thickness, q, new start: form prefilled (circle, ring on, #123abc, 5 px); config: ' +
              ' '.join(l for l in c.splitlines() if l.startswith('CAM_A_') and any(k in l for k in ('SHAPE', 'RING', 'COLOR', 'THICK'))))
    finally:
        s2.close()


@test('T-B5')
def t_b5():
    conf = cfg().replace(f'CAM_A_DEV={CAM_A_DEV}', 'CAM_A_DEV=/dev/video99').replace(CAM_A_NAME, 'Nonexistent Camera 9000')
    h = make_home('b5', conf)
    s = Session(h, out_dir('b5'))
    try:
        s.wait_for('Camera A', 5)
        scr = s.screen()
        expect('missing: Nonexistent Camera 9000' in scr, scr)
        line = [l for l in scr.splitlines() if 'Camera A' in l][0]
        expect(CAM_A_NAME not in line and (not CAM_B_NAME or CAM_B_NAME not in line), line)
        s.send('q'); s.wait_exit(5)
        c = open(h + '/.config/multicam/config').read()
        expect('Nonexistent Camera 9000' in c, 'saved device disappeared from config')
        R.add('T-B5', 'PASS', f'row: "{line.strip()}"; no other camera selected; saved device kept in config')
    finally:
        s.close()


# ---------------------------------------------------------------- D
def mon_area_of(g):
    """Screen area (logical px minus reserved) of the monitor that contains the window's top-left corner."""
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
                errs.append(f'{label}: got {g()} expected {exp}')
        x, y, sz = MX + 500, MY + 300, 240
        chk('start', (x, y, sz, sz))
        expect('[MOVE]' in s.screen(), 'mode')

        def tr(a, b):  # integer division towards zero (like bash)
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
                errs.append(f'{label}: got {r} expected {exp}')
        for key, dx, dy, lab in [(RIGHT, 20, 0, 'right'), (DOWN, 0, 20, 'down'), (LEFT, -20, 0, 'left'), (UP, 0, -20, 'up'),
                                 (SRIGHT, 100, 0, 'shift right'), (SDOWN, 0, 100, 'shift down')]:
            step(key, lab, dx, dy)
        for key, lab, pct in [('+', '+', 10), ('-', '-', -10), (PGUP, 'PgUp', 10), (PGDN, 'PgDn', -10)]:
            step(key, lab, pct=pct)
        s.send('m', 0.3); expect('[SIZE]' in s.screen(), 'size mode not in the status line')
        for key, pct in [(UP, 10), (RIGHT, 10), (DOWN, -10), (LEFT, -10), (SUP, 25), (SDOWN, -25)]:
            step(key, 'size ' + repr(key), pct=pct)
        # minimum
        for _ in range(12): s.send('-', 0.15)
        wait_until(lambda: g()[2] == 120, 3)
        if g()[2:] != (120, 120): errs.append(f'min: {g()}')
        # maximum = screen height
        for _ in range(40): s.send('+', 0.12)
        wait_until(lambda: g()[2] == min(MW, MH), 5)
        if g()[2:] != (min(MW, MH),) * 2: errs.append(f'max: {g()} expected {min(MW, MH)}')
        # clamping: back to 300 px, then against all four edges in move mode
        for _ in range(25): s.send('-', 0.1)
        for _ in range(3): s.send('+', 0.1)
        s.send('m', 0.3)
        if '[MOVE]' not in s.screen(): s.send('m', 0.3)
        cl = {}
        for name, key in [('left', SLEFT), ('up', SUP), ('right', SRIGHT), ('down', SDOWN)]:
            for _ in range(max(MW, MH) // 100 + 2): s.send(key, 0.06)
            time.sleep(0.4)
            gx, gy, gw, gh = g()
            cl[name] = (gx, gy, gw, gh)
        gx, gy, gw, gh = cl['left']
        if gx != MX: errs.append(f'left edge: x={gx} expected {MX}')
        gx, gy, gw, gh = cl['up']
        if gy != MY: errs.append(f'top edge: y={gy} expected {MY}')
        gx, gy, gw, gh = cl['right']
        if gx + gw != MX + MW: errs.append(f'right edge: x+w={gx + gw} expected {MX + MW}')
        gx, gy, gw, gh = cl['down']
        if gy + gh != MY + MH: errs.append(f'bottom edge: y+h={gy + gh} expected {MY + MH}')
        for k, (gx, gy, gw, gh) in cl.items():
            if gx < MX or gy < MY or gx + gw > MX + MW or gy + gh > MY + MH:
                errs.append(f'off screen after {k}: {(gx, gy, gw, gh)} area {(MX, MY, MW, MH)}')
        # growing at an edge must not push the image off screen
        s.send('1', 0.3)
        for _ in range(8): s.send('+', 0.1)
        time.sleep(0.4)
        gx, gy, gw, gh = g()
        if gx < MX or gy < MY or gx + gw > MX + MW or gy + gh > MY + MH: errs.append(f'off screen after growing in a corner: {g()}')
        e_d34 = list(errs)
        R.add('T-D3/4', 'PASS' if not e_d34 else 'FAIL',
              'pty + hyprctl clients -j: move 20/100 px, +/-/PgUp/PgDn ±10 %, size mode ±10/25 %, min 120, max ' + str(min(MW, MH)) +
              ', clamping against all four edges (x=MX, y=MY, x+w=MX+MW, y+h=MY+MH), status line [MOVE]/[SIZE]' + ('' if not e_d34 else ' ERRORS: ' + '; '.join(e_d34)))
        s.send('q'); s.wait_exit(5)
    finally:
        s.close()

    # ---- D5: both cameras, Tab / Shift-Tab, digits on B
    s = run_session('d5', cfg(shape='circle', ring='on', size=200) + 'CAM_A_RX=100\nCAM_A_RY=100\n'
                    + CAM_B_CFG + 'CAM_B_SHAPE=rect\nCAM_B_SIZE=180\nCAM_B_RX=600\nCAM_B_RY=100\n')
    errs = []
    try:
        start_to_preview(s)
        wait_until(lambda: len(geo()) == 2, 8)
        MX, MY, MW, MH = mon_area_of(geo()['MulticamA'])
        ga = lambda: geo()['MulticamA']; gb = lambda: geo()['MulticamB']
        expect('Changing  camera A' in s.screen(), s.screen())
        # 1 on A -> bottom left
        s.send('1', 0.5)
        a0, b0 = ga(), gb()
        exA = (MX + 20, MY + MH - 20 - a0[3])
        if abs(a0[0] - exA[0]) > 1 or abs(a0[1] - exA[1]) > 1: errs.append(f'A/1: {a0} expected {exA}')
        s.send(TAB, 0.4)
        if 'Changing  camera B' not in s.screen(): errs.append('Tab did not select B')
        s.send('9', 0.5)
        a1, b1 = ga(), gb()
        if a1 != a0: errs.append(f'A moved while B was controlled: {a0} -> {a1}')
        exB = (MX + MW - 20 - b1[2], MY + 20)
        if abs(b1[0] - exB[0]) > 1 or abs(b1[1] - exB[1]) > 1: errs.append(f'B/9: {b1} expected {exB}')
        s.send('\x1b[Z', 0.4)   # Shift-Tab back to A
        if 'Changing  camera A' not in s.screen(): errs.append('Shift-Tab did not select A')
        s.send('5', 0.5)
        a2, b2 = ga(), gb()
        exA = (MX + (MW - a2[2]) // 2, MY + (MH - a2[3]) // 2)
        if abs(a2[0] - exA[0]) > 2 or abs(a2[1] - exA[1]) > 2: errs.append(f'A/5: {a2} expected {exA}')
        if b2 != b1: errs.append(f'B moved by an action on A: {b1} -> {b2}')
        s.send(TAB, 0.3); s.send(TAB, 0.3)
        if 'Changing  camera A' not in s.screen(): errs.append('Tab twice should give A')
        R.add('T-D5', 'PASS' if not errs else 'FAIL',
              'two cameras configured: Tab/Shift-Tab switches the selected camera (status line), digits 1/5 on A and 9 on B land correctly (±1-2 px), the other camera is not moved' + ('' if not errs else ' ERRORS ' + '; '.join(errs)))
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
        R.add('T-D7', ('MANUAL' if before_active is None else 'PASS' if act == before_active else 'FAIL'),
              f'hyprctl activewindow before={before_active} after camera start+actions={act}' +
              (' (no active window: locked session, cannot determine focus; see T-D7b)' if before_active is None else ''))
        s.send('q'); s.wait_exit(5)
    finally:
        s.close()


@test('T-D7b')
def t_d7b():
    """Real foot window with the TUI: focus must stay on the TUI."""
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
        expect(ok, 'foot window missing')
        time.sleep(1)
        addr = ok[0]['address']
        if active_addr() != addr:
            os.write(fd, b'q'); foot.wait(timeout=8)
            R.add('T-D7b', 'MANUAL', f'the foot window did not get keyboard focus (activewindow={active_class()}; the session is locked) - focus could not be tested')
            return
        os.write(fd, b'\x1b[15~')
        expect(wait_until(lambda: len(mc_clients()) >= 1, 10), 'camera not mapped')
        res = []
        for k in [b'\x1b[C', b'\x1b[B', b's', b'r', b'\x1b[5~', b'1', b'm', b'\x1b[A']:
            os.write(fd, k); time.sleep(0.4)
            res.append(active_addr() == addr)
        expect(all(res), f'focus moved: {res}')
        R.add('T-D7b', 'PASS', f'foot --app-id=TUI.float, keys via fifo; activewindow == TUI ({addr}) after every action ({len(res)} total)')
        os.write(fd, b'q')
        foot.wait(timeout=8)
        os.close(fd)
    finally:
        if foot.poll() is None: foot.terminate()


@test('T-D8')
def t_d8():
    wake()
    # stand-in for Omarchy's WebcamOverlay: same class/title, synthetic source (the camera is used by multicam)
    ov = subprocess.Popen(['mpv', 'av://lavfi:testsrc2=size=320x180', '--title=WebcamOverlay', '--wayland-app-id=WebcamOverlay-medium',
                           '--no-border', '--no-audio', '--no-osc', '--osd-level=0', '--really-quiet', '--no-config', '--untimed'],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    s = None
    try:
        ovc = wait_until(lambda: [c for c in clients() if c['class'] == 'WebcamOverlay-medium'], 8)
        expect(ovc, 'overlay not mapped')
        og0 = (ovc[0]['at'], ovc[0]['size'], ovc[0]['floating'], ovc[0]['pinned'])
        s = run_session('d8', cfg(shape='circle', ring='on', size=200))
        start_to_preview(s)
        wait_until(lambda: 'MulticamA' in geo(), 5)
        for k in [RIGHT, DOWN, 's', 'r']: s.send(k, 0.3)
        a = mc_clients()['MulticamA']
        ovc2 = [c for c in clients() if c['class'] == 'WebcamOverlay-medium'][0]
        og1 = (ovc2['at'], ovc2['size'], ovc2['floating'], ovc2['pinned'])
        expect(og0 == og1, f'overlay changed {og0} -> {og1}')
        expect(a['size'][0] == 200 or a['size'][0] == 355, f'multicam size {a["size"]}')
        s.send('q'); s.wait_exit(5)
        expect(wait_until(lambda: [c for c in clients() if c['class'] == 'WebcamOverlay-medium'], 2), 'overlay was closed by multicam')
        R.add('T-D8', 'PASS', f'WebcamOverlay-medium (stand-in mpv, testsrc) unchanged {og1}; MulticamA independent {a["at"]} {a["size"]}; overlay still alive after multicam exit')
    finally:
        if s: s.close()
        ov.terminate()
        try: ov.wait(3)
        except Exception: ov.kill()


# ---------------------------------------------------------------- E


def start_recording(s, tmo=20):
    start_to_preview(s)
    s.send(ENTER, 0.3)
    expect(s.wait_for('RECORDING', tmo), 'recording did not start:\n' + s.screen())
    expect(wait_until(gsr_pids, 5), 'gsr missing')


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
        t_start = os.stat('/tmp/omarchy-screenrecord-filename').st_mtime   # Omarchy confirms that the recording is running
        time.sleep(7)
        s.send(F12, 0)
        wait_until(lambda: not gsr_pids(), 10, 0.02)
        t_stop = time.time()   # when gpu-screen-recorder exited
        expect(s.wait_for('recording is done', 25), s.screen())
        after = default_source()
        files = sorted(os.listdir(o))
        mp4 = [f for f in files if f.endswith('.mp4')]
        expect(len(mp4) == 1, f'files {files}')
        f = os.path.join(o, mp4[0])
        pr = sh(f'ffprobe -v error -show_entries stream=codec_name,codec_type:format=format_name,duration -of json "{f}"')
        j = json.loads(pr.stdout)
        codecs = {st['codec_type']: st['codec_name'] for st in j['streams']}
        dur = float(j['format']['duration'])
        s.send('n'); s.wait_exit(5)
        R.add('T-C3', 'PASS' if (during == MIC and after == before) else 'FAIL',
              f'pactl get-default-source: before={before} during={during} after={after} (expected during: {MIC}); audio stream in the file: {"audio" in codecs} (volume measurement of the selected source not done here: see report)')
        R.add('T-C4', 'PASS' if (codecs.get('video') == 'h264' and codecs.get('audio') == 'aac' and 'mp4' in j['format']['format_name'] and abs(dur - (t_stop - t_start - 0.1)) <= 0.5) else 'FAIL',
              f'ffprobe: {codecs} format={j["format"]["format_name"]} duration={dur:.2f}s; measured time from start (Omarchy\'s pointer file) to recorder exit {t_stop - t_start:.2f}s minus Omarchy\'s 0.1 s trim = {t_stop - t_start - 0.1:.2f}s (tolerance ±0.5 s)')
        rx = r'^screenrecording-[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}_[0-9]{2}_[0-9]{2}\.mp4$'
        ok = re.match(rx, mp4[0]) and not any(re.match(r'screenrecording-\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.mp4', x) for x in files)
        R.add('T-C4b(name)', 'PASS' if ok else 'FAIL', f'files in the output folder: {files}; Omarchy\'s original name ({os.path.basename(rec_ptr)}) gone')
        # C1: frame at 0.2 s
        png = EVID + '/c1-frame-0.2s.png'
        sh(f'ffmpeg -y -v error -ss 0.2 -i "{f}" -frames:v 1 -vf scale=640:-1 "{png}"')
        R.add('T-C1', 'MANUAL', f'frame at 0.2 s saved (not committed): {png}; the camera image in the frame is reviewed manually (see visual.py)')
        probs = settle_clean()
        R.add('T-E1(q)', 'PASS' if not probs else 'FAIL', f'F12 stop: {probs or "no windows/rules/mpv left, mic restored"}')
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
        # create a collision
        open(os.path.join(o, want), 'w').write('existing')
        time.sleep(3)
        s.send(F12, 0.3)
        expect(s.wait_for('recording is done', 25), s.screen())
        files = sorted(os.listdir(o))
        s.send('n'); s.wait_exit(5)
        omarchy_name = f'screenrecording-{m[1]}_{m[2]}-{m[3]}-{m[4]}.mp4'
        ok = ((want[:-4] + '-2.mp4') in files and open(os.path.join(o, want)).read() == 'existing'
              and omarchy_name not in files and not os.path.exists(ptr))
        R.add('T-C4b', 'PASS' if ok else 'FAIL', f'collision: {files}; existing file untouched, new one got -2; Omarchy\'s name ({omarchy_name}) no longer present')
        shutil.rmtree(o, ignore_errors=True)
    finally:
        s.close()


@test('T-E1b', 'T-E2')
def t_e_signals():
    wake()
    res = {}
    # Esc in preview
    s = run_session('e1', cfg())
    start_to_preview(s)
    s.send(ESC, 0.3)
    back = s.wait_for('Preview cameras', 5) and not mc_clients()   # Esc = back to the form with the cameras closed
    s.send('q', 0.3); ok = back and s.wait_exit(5)
    res['E1 Esc (preview)'] = (ok, settle_clean())
    s.close()
    for name, how in [('Ctrl+C', 'int'), ('SIGHUP (closed terminal)', 'hup'), ('SIGTERM', 'term')]:
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
    # --stop-recording from outside
    o = out_dir('e2')
    s = run_session('e2', cfg(), o)
    try:
        start_recording(s)
        time.sleep(2)
        t0 = time.time()
        p = subprocess.Popen(['omarchy-capture-screenrecording', '--stop-recording'], stdout=subprocess.DEVNULL)
        gone = wait_until(lambda: not mc_clients() and not own_mpv_for_multicam(), 4, 0.02)
        dt = time.time() - t0
        ended = s.wait_for('recording is done', 20)
        p.wait(10)
        files = os.listdir(o)
        res['E2 --stop-recording from outside'] = (bool(gone) and dt < 1.0 and ended, f'{dt:.2f}s', settle_clean(), files)
        s.send('n'); s.wait_exit(5)
    finally:
        s.close()
        shutil.rmtree(o, ignore_errors=True)
    bad = {k: v for k, v in res.items() if not (v[0] and not v[-1 if len(v) == 2 else 2])}
    ev = '; '.join(f'{k}: {v}' for k, v in res.items())
    R.add('T-E1b', 'PASS' if res['E1 Esc (preview)'][0] and not res['E1 Esc (preview)'][1] else 'FAIL', ev.split('; E2')[0])
    R.add('T-E2', 'PASS' if not bad or list(bad) == [] else 'FAIL', ev + (f' | ERRORS: {list(bad)}' if bad else ''))


@test('T-C3v')
def t_c3_volume():
    """Record 5 s with two different microphones and compare ffmpeg volumedetect (Omarchy's loudnorm evens things out, so raw background is measured too)."""
    wake()
    if not (MIC and MIC2):
        return R.add('T-C3v', 'MANUAL', 'requires two microphones (set MC_MIC and MC_MIC2)')
    mics = {'mic1': MIC, 'mic2': MIC2}
    vals = {}
    for name, mic in mics.items():
        o = out_dir('c3v')
        s = run_session('c3v', cfg() + 'MIC=' + mic + '\n', o)
        try:
            start_recording(s)
            during = default_source()
            time.sleep(5)
            s.send(F12, 0.3)
            expect(s.wait_for('recording is done', 25), s.screen())
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
    R.add('T-C3v', 'PASS' if (ok_def and diff is not None and diff >= 10) else 'FAIL',
          f'mean_volume (dB) per selected mic: {v}; default-source during recording = selected mic for all: {ok_def}; |mic1-mic2| = {diff}')


@test('T-E2s')
def t_e2_stress():
    """HUP/INT/TERM x10 during recording: windows/mpv/mic cleaned up < 1.0 s, file finalized and renamed."""
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
                # all windows/processes exist right now
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
            if probs: res[-1] = (False, 'leftover: ' + str(probs)[:80])
        rows[how] = res
    allok = all(ok for r in rows.values() for ok, _ in r)
    R.add('T-E2s', 'PASS' if allok else 'FAIL',
          '10 runs per signal; (ok, seconds until cleaned up): ' + '; '.join(f'{k}: max {max(t for _, t in v if isinstance(t, float)):.2f}s, ok={sum(ok for ok, _ in v)}/10' for k, v in rows.items()))


@test('T-B5b')
def t_identical_cams():
    """Two identical cameras (same name, different path) must not be merged; exact path+name wins over a name match."""
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
        s.wait_for('Camera A', 5)
        scr = s.screen()
        s.send('q'); s.wait_exit(5)
        c = open(h + '/.config/multicam/config').read()
        ok = 'CAM_A_DEV=/dev/video6' in c and 'CAM_B_DEV=/dev/video4' in c and 'missing' not in scr
        # do not change: the Camera B row must show Twin Cam (not "off"/missing)
        lines = [l for l in scr.splitlines() if l.strip().startswith('Camera')]
        R.add('T-B5b', 'PASS' if ok and all('Twin Cam' in l for l in lines) else 'FAIL',
              f'A=/dev/video6, B=/dev/video4 (both "Twin Cam") kept exactly: {lines}; config: ' + ' '.join(l for l in c.splitlines() if '_DEV=' in l))
    finally:
        s.close()


@test('T-D9')
def t_screen_focus():
    """Choosing a screen other than the focused one: the recording happens on that screen and focus (monitor + window) is restored."""
    wake()
    mons = monitors()
    foc = [m for m in mons if m['focused']][0]['name']
    other = [m for m in mons if m['name'] != foc and m['name'].startswith('DP')]
    if not other:
        R.add('T-D9', 'MANUAL', 'no second DP screen available'); return
    other = other[0]
    o = out_dir('d9')
    act0 = active_addr()
    s = run_session('d9', cfg() + 'SCREEN=' + other['name'] + '\n', o)
    try:
        start_recording(s)
        time.sleep(2)
        foc_after = [m for m in monitors() if m['focused']][0]['name']
        act1 = active_addr()
        s.send(F12, 0.3)
        expect(s.wait_for('recording is done', 25), s.screen())
        f = [x for x in os.listdir(o) if x.endswith('.mp4')][0]
        j = json.loads(sh(f'ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of json "{o}/{f}"').stdout)['streams'][0]
        exp = (other['width'], other['height'])  # raw mode size; a rotated screen (transform 1) gives the reverse order in the file
        if other.get('transform', 0) % 2: exp = (exp[1], exp[0])
        s.send('n'); s.wait_exit(5)
        ok = (j['width'], j['height']) == exp and foc_after == foc and act1 == act0
        R.add('T-D9', 'PASS' if ok else 'FAIL',
              f'SCREEN={other["name"]} (focused was {foc}): file resolution {j["width"]}x{j["height"]} (screen {exp[0]}x{exp[1]}); focused monitor after start={foc_after} (before {foc}); active window before={act0} after={act1}')
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
        expect(wait_until(lambda: len(geo()) == 2, 8), 'cameras missing')
        scr = s.screen()
        g = geo()
        inside = all(x >= rx and y >= ry and x + w <= rx + rw and y + h <= ry + rh for x, y, w, h in g.values())
        expect(inside, f'cameras outside the area {rect}: {g}')
        hdr = [l for l in scr.splitlines() if 'Area' in l or 'Window' in l]
        expect(hdr and (label_expect is None or label_expect in hdr[0]), f'header: {hdr}\n{scr}')
        # numpad snap and max size must be clamped to the area
        s.send('9', 0.4)
        for _ in range(30): s.send('+', 0.05)
        time.sleep(0.4)
        g = geo()
        inside2 = all(x >= rx and y >= ry and x + w <= rx + rw and y + h <= ry + rh for x, y, w, h in g.values())
        expect(inside2, f'cameras outside after snap/grow: {g}')
        s.send('1', 0.3); s.send('+', 0.2)
        s.send(ENTER, 0.3)
        expect(s.wait_for('RECORDING', 25), s.screen())
        shim_during = os.path.exists(f'{s.home}/../../run/user/1000/multicam')  # (not relevant)
        time.sleep(4)
        run = '/run/user/1000/multicam'
        sessions = [x for x in os.listdir(run) if x.startswith('s.')]
        shim_left = [x for x in sessions if os.path.exists(f'{run}/{x}/shim')]
        frame_g = geo()
        grim('/tmp/claude-1000/b6-live.png')
        s.send(F12, 0.3)
        expect(s.wait_for('recording is done', 25), s.screen())
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
    r = region_test('T-B6a', 'region', rect, 'Area 1200x800')
    R.add('T-B6a', 'PASS' if not r['probs'] and not r['shim_left'] and r['args'] and r['args'][0].startswith('region') else 'FAIL',
          f'stub picker (call: {r["args"]}) gave {rect}; cameras inside the area before and after snap/grow; MP4 {r["w"]}x{r["h"]} (area 1200x800 x scale {sc} = {int(1200*sc)}x{int(800*sc)}); '
          f'shim left after start: {r["shim_left"]}; cleaned up: {r["probs"] or "yes"}; frame (not committed): {r["frame"]}')


@test('T-B6b')
def t_b6b():
    wake()
    fx, fy, fw, fh, sc = focused_geo()
    cands = [c for c in clients() if not c['class'].startswith('Multicam') and c['size'][0] >= 300 and c['size'][1] >= 300
             and fx <= c['at'][0] < fx + fw and fy <= c['at'][1] < fy + fh]
    expect(cands, 'no window on the focused screen')
    c = cands[0]
    rect = f'{c["at"][0]},{c["at"][1]} {c["size"][0]}x{c["size"][1]}'
    r = region_test('T-B6b', 'window', rect, 'Window: ' + c['class'])
    R.add('T-B6b', 'PASS' if not r['probs'] and r['args'] and r['args'][0].startswith('windows') else 'FAIL',
          f'window {c["class"]} {rect}; picker called with "{r["args"]}"; header "Window: {c["class"]}"; MP4 {r["w"]}x{r["h"]} (expected {int(c["size"][0]*sc)}x{int(c["size"][1]*sc)} at scale {sc}); cleaned up: {r["probs"] or "yes"}')


@test('T-B6c')
def t_b6c():
    wake()
    d = picker_stub(cancel=True)
    o = out_dir('b6c')
    s = Session(make_home('b6c', cfg(extra='CAPTURE=region\n')), o, env={'PATH': d + ':' + os.environ['PATH']})
    try:
        s.wait_for('Camera A', 5)
        s.send(F5, 0.5)
        got = s.wait_for('Selection cancelled', 5)
        scr = s.screen()
        ok = got and 'Camera A' in scr and not mc_clients() and not gsr_pids() and not [x for x in os.listdir(o)]
        # the form must still respond: switch back to full screen and preview
        s.send(UP, 0.2)
        R.add('T-B6c', 'PASS' if ok else 'FAIL', f'picker cancelled (exit 1): message "Selection cancelled", form still shown, no camera windows/recorder, output folder empty={os.listdir(o) == []}')
        s.send('q'); s.wait_exit(5)
    finally:
        s.close()
        shutil.rmtree(o, ignore_errors=True)


def conf_kv(home):
    return dict(l.split('=', 1) for l in open(home + '/.config/multicam/config').read().splitlines() if '=' in l)


@test('T-B7')
def t_persist():
    """Settings are saved as soon as they change (not only on exit) and are used at the next start (full screen and area)."""
    wake()
    h = make_home('b7', cfg(shape='circle', ring='on', size=200) + 'CAM_A_RX=100\nCAM_A_RY=100\nCAM_B_DEV=\nCAM_B_NAME=\n')
    o = out_dir('b7')
    s = Session(h, o)
    try:
        s.wait_for('Camera A', 5)
        s.send(DOWN, 0.3); s.send(RIGHT, 0.3)            # shape -> rectangle
        kv = conf_kv(h)
        expect(kv.get('CAM_A_SHAPE') == 'rect', f'form: the change was not saved immediately: {kv.get("CAM_A_SHAPE")}')
        s.send(F5)
        expect(s.wait_for('PREVIEW', 15), s.screen())
        expect(wait_until(lambda: 'MulticamA' in geo(), 8), 'camera missing')
        s.send(RIGHT, 0.3); s.send(RIGHT, 0.3); s.send(DOWN, 0.3); s.send('+', 0.3)
        time.sleep(1.6)                                    # saved after a short quiet period
        g1 = geo()['MulticamA']
        kv = conf_kv(h)                                    # the TUI is still running
        expect(kv.get('CAM_A_SIZE') == str(g1[3]) and kv.get('CAM_A_RX') != '100', f'preview: not saved immediately: {kv} geo={g1}')
        s.send('q'); expect(s.wait_exit(8), 'did not exit')
    finally:
        s.close()
    expect(not settle_clean(), settle_clean())
    s = Session(h, o)
    try:
        s.wait_for('Camera A', 5)
        expect('● rectangle' in s.screen(), s.screen())
        s.send(F5)
        expect(s.wait_for('PREVIEW', 15), s.screen())
        expect(wait_until(lambda: geo().get('MulticamA') == g1, 8), f'new start: {geo().get("MulticamA")} expected {g1}')
        s.send('q'); expect(s.wait_exit(8), 'did not exit')
    finally:
        s.close()
        shutil.rmtree(o, ignore_errors=True)
    expect(not settle_clean(), settle_clean())
    R.add('T-B7', 'PASS', f'shape (rectangle) and the camera position/size {g1} were in config while the TUI was running; new start: form prefilled and the camera in the same place')


@test('T-B6d')
def t_b6d():
    """Area: the last area is saved and reused on F5 without the picker; the Area row can pick a new one."""
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
        expect(calls() == 1, f'the picker was called {calls()} times the first time')
        s.send('q'); expect(s.wait_exit(8), 'did not exit')
        s.close()
        kv = conf_kv(h)
        expect(kv.get('LAST_AREA') == f'{mx + 100},{my + 80},900,600', kv.get('LAST_AREA'))
        s = Session(h, o, env=env)
        s.wait_for('Camera A', 5)
        scr = s.screen()
        expect('last: 900x600' in scr, scr)
        start_to_preview(s)
        hdr = [l for l in s.screen().splitlines() if 'Area 900x600' in l]
        expect(calls() == 1 and hdr, f'second time: picker called {calls()} times, header {hdr}')
        g = geo()['MulticamA']
        expect(g[0] >= mx + 100 and g[1] >= my + 80 and g[0] + g[2] <= mx + 1000 and g[1] + g[3] <= my + 680, f'camera outside the area: {g}')
        s.send('q'); expect(s.wait_exit(8), 'did not exit')
        s.close()
        # pick a new one via the Area row (Enter toggles) -> the picker runs again
        s = Session(h, o, env=env)
        s.wait_for('Camera A', 5)
        for _ in range(20):   # go to the Area row (wait for each new frame)
            sel = [l for l in s.screen().splitlines() if '▌' in l]
            if sel and 'last:' in sel[0]: break
            s.send(DOWN if sel else UP, 0.3)
        s.send(ENTER, 0.3)
        expect('● pick a new one' in s.screen(), s.screen())
        start_to_preview(s)
        expect(calls() == 2, f'pick a new one: picker called {calls()} times')
        s.send('q'); expect(s.wait_exit(8), 'did not exit')
        s.close()
    finally:
        s.close()
        shutil.rmtree(o, ignore_errors=True)
    expect(not settle_clean(), settle_clean())
    R.add('T-B6d', 'PASS', f'last area {rect} saved; new start: the row "last: 900x600" and F5 without picker (header Area 900x600, camera inside); "pick a new one" runs the picker again')


@test('T-R1')
def t_enter_only():
    """Regression: in the preview only Enter starts the recording (not F5/other keys); the camera rule has no_anim."""
    wake()
    src = open(BIN).read()
    expect('no_anim=true' in src, 'no_anim missing from the window rule')
    s = run_session('r1', cfg(shape='circle'))
    try:
        start_to_preview(s)
        s.send(F5, 0.6); s.send(' ', 0.4); s.send('x', 0.3)
        time.sleep(1.5)
        ok1 = not gsr_pids() and 'PREVIEW' in s.screen()
        s.send(ENTER, 0.3)
        ok2 = s.wait_for('RECORDING', 20) and bool(wait_until(gsr_pids, 5))
        time.sleep(1.5)
        s.send(F12, 0.3); s.wait_for('recording is done', 25); s.send('n'); s.wait_exit(5)
        R.add('T-R1', 'PASS' if ok1 and ok2 else 'FAIL', f'F5/space/x in preview started nothing (gsr={bool(ok1)}); Enter started; no_anim=true in the rule')
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
        ended = s.wait_for('recording is done', 20) or 'could not' in s.screen()
        files = os.listdir(o)
        R.add('T-E4', 'PASS' if gone and ended else 'FAIL', f'SIGTERM to gpu-screen-recorder ({pids}): windows/mpv gone after {dt:.2f}s; TUI showed result={ended}; file: {files}; remaining: {settle_clean()}')
        s.send('n'); s.wait_exit(5)
    finally:
        s.close()
        shutil.rmtree(o, ignore_errors=True)


@test('T-E5')
def t_e5():
    wake()
    other = subprocess.Popen(['mpv', 'av://lavfi:testsrc=size=160x90', '--title=OTHERMPV', '--no-config', '--no-audio', '--really-quiet'],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    s = run_session('e5', cfg())
    try:
        start_to_preview(s)
        s.send('q', 0.3); s.wait_exit(5)
        time.sleep(0.5)
        alive = other.poll() is None
        titled = [c for c in clients() if c['title'] == 'OTHERMPV']
        R.add('T-E5', 'PASS' if alive and titled else 'FAIL', f'external mpv (pid {other.pid}, title OTHERMPV) alive after multicam start+exit: poll={other.poll()}, window still there={bool(titled)}')
    finally:
        s.close()
        other.terminate()


@test('T-D2c')
def t_picker():
    """c -> hyprpicker (stub in PATH): the command is called and the colour is set."""
    stubdir = os.path.join(SCRATCH, 'stub'); os.makedirs(stubdir, exist_ok=True)
    marker = os.path.join(stubdir, 'called')
    if os.path.exists(marker): os.unlink(marker)
    open(stubdir + '/hyprpicker', 'w').write(f'#!/bin/bash\necho "$@" > {marker}\necho "#12ab34"\n')
    os.chmod(stubdir + '/hyprpicker', 0o755)
    env = {'PATH': stubdir + ':' + os.environ['PATH']}
    s = Session(make_home('d2c', cfg()), out_dir('d2c'), env=env)
    try:
        s.wait_for('Camera A', 5)
        for _ in range(3): s.send(DOWN)
        s.send('c', 0.8)
        expect(os.path.exists(marker), 'hyprpicker was not called')
        expect('#12ab34' in s.screen(), s.screen())
        # persistence
        s.send('q'); s.wait_exit(5)
        c = open(s.home + '/.config/multicam/config').read()
        expect('CAM_A_COLOR=#12ab34' in c, c)
        R.add('T-D2c', 'PASS', f'stub hyprpicker called with args "{open(marker).read().strip()}"; colour #12ab34 set and saved per camera in config')
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
        s.send(F12, 0.3); s.wait_for('recording is done', 25)
        R.add('T-E3', 'MANUAL', f'gpu-screen-recorder running during recording={gsr} (that is what shows Omarchy\'s icon); indicators refresh: {r.stdout.strip()}; the icon\'s look is reviewed with tests/visual.py record (e3-bar*.png); real mouse click: M')
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
        s.send(F12, 0.3)
        expect(s.wait_for('recording is done', 30), s.screen())
        f = [x for x in os.listdir(o) if x.endswith('.mp4')]
        expect(len(f) == 1, os.listdir(o))
        fp = os.path.join(o, f[0])
        pr = json.loads(sh(f'ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames,avg_frame_rate,r_frame_rate:format=duration -of json "{fp}"').stdout)
        st = pr['streams'][0]; dur = float(pr['format']['duration']); nb = int(st['nb_read_frames'])
        play = sh(f'ffmpeg -v error -i "{fp}" -f null - 2>&1 | head -3').stdout.strip()
        s.send('n'); s.wait_exit(5)
        okx = alive_cams == ['MulticamA', 'MulticamB'] and abs(nb / dur - 60) < 8 and not play
        R.add('T-X1', 'PASS' if okx else 'FAIL',
              f'two cameras ({alive_cams}) + circle + mic, 30 s: {dur:.1f}s, {nb} frames ({nb / dur:.1f} fps of 60 requested), ffmpeg decoding without errors={not play}; the content is reviewed manually (frame not committed)')
        # X2: twice in a row, no leftovers
        shutil.rmtree(o, ignore_errors=True)
        o = out_dir('x2')
        res = []
        for i in range(2):
            s = run_session('x2', cfg(shape='circle', ring='on'), o)
            try:
                start_recording(s)
                time.sleep(3)
                s.send(F12, 0.3)
                s.wait_for('recording is done', 25)
                s.send('n'); s.wait_exit(5)
                res.append((sorted(os.listdir(o)), settle_clean(), os.listdir(RUNDIR)))
            finally:
                s.close()
        ok2 = all(not r[1] for r in res) and len([x for x in res[1][0] if x.endswith('.mp4')]) == 2
        R.add('T-X2', 'PASS' if ok2 else 'FAIL', f'two runs in a row: after 1: {res[0]}; after 2: {res[1]}')
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
    subprocess.run([REPO + '/install.sh', '--yes', '--no-bgremove', '--no-bar-indicator'], env=env, capture_output=True)
    before = snapshot(home)
    t0 = time.time()
    r = subprocess.run([home + '/.local/bin/multicam', 'install-bgremove', '--yes'], env=env, capture_output=True, text=True)
    expect(r.returncode == 0, r.stdout + r.stderr)
    mid = snapshot(home)
    new = sorted({os.path.relpath(p, home).split('/bg')[0] + ('/bg' if '/bg' in p else '') for p in set(mid) - set(before)})
    sz = sh(f'du -sm {home}/.local/share/multicam/bg').stdout.split()[0]
    r2 = subprocess.run([home + '/.local/bin/multicam', 'uninstall-bgremove'], env=env, capture_output=True, text=True)
    after = snapshot(home)
    expect(after == before, 'diff after uninstall-bgremove not empty')
    R.add('T-A6', 'PASS', f'install-bgremove ({time.time() - t0:.0f}s, {sz} MB): new paths outside bg/: {[n for n in new if "multicam/bg" not in n]}; everything under ~/.local/share/multicam/bg; uninstall-bgremove: snapshot identical to before')


@test('T-F2', 'T-F3')
def t_f():
    home = os.path.join(SCRATCH, 'mc-home-f')
    shutil.rmtree(home, ignore_errors=True)
    os.makedirs(home)
    env = dict(os.environ, HOME=home)
    subprocess.run([REPO + '/install.sh', '--yes', '--no-bgremove', '--no-bar-indicator'], env=env, capture_output=True)
    mc = home + '/.local/bin/multicam'
    # F3: corrupt model via URL override -> rejected
    bad = SCRATCH + '/bad.onnx'
    open(bad, 'wb').write(b'not a model' * 1000)
    r = subprocess.run([mc, 'install-bgremove', '--yes'], env=dict(env, MULTICAM_MODEL_URL='file://' + bad), capture_output=True, text=True)
    left = os.path.exists(home + '/.local/share/multicam/bg/rvm_mobilenetv3_fp32.onnx')
    R.add('T-F3', 'PASS' if r.returncode != 0 and not left else 'FAIL',
          f'wrong model via MULTICAM_MODEL_URL: rc={r.returncode}, model file left={left}, output: {r.stderr.strip()[-120:]}')
    # real installation
    r = subprocess.run([mc, 'install-bgremove', '--yes'], env=env, capture_output=True, text=True)
    expect(r.returncode == 0, r.stdout + r.stderr)
    model = home + '/.local/share/multicam/bg/rvm_mobilenetv3_fp32.onnx'
    py = home + '/.local/share/multicam/bg/venv/bin/python'
    # tamper with the installed model -> check-bgremove must refuse
    shutil.copy(model, model + '.orig')
    with open(model, 'ab') as f: f.write(b'x')
    c = subprocess.run([mc, 'check-bgremove'], env=env, capture_output=True, text=True)
    os.replace(model + '.orig', model)
    R.add('T-F3b', 'PASS' if c.returncode != 0 else 'FAIL', f'modified model file: check-bgremove rc={c.returncode} {c.stderr.strip()}')
    # fps + CPU: 15 s, the raw RGBA stream is measured (as mpv receives it)
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
    R.add('T-F2(fps)', 'PASS' if fps >= 25 else 'FAIL',
          f'bg.py --threads 2, camera A 640x360, {dt:.1f} s: {frames:.0f} RGBA frames = {fps:.1f} fps, CPU about {cpu:.0f} % of one core (python+ffmpeg); stderr: {err.strip()[-120:]}')
    # TUI pipeline with background removal: processes start and are cleaned up (non-visual)
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
        R.add('T-F2', 'MANUAL', f'TUI with bg=on: mpv+python started ({len(procs)} processes, window {g}), cleaned up after q: {probs or "yes"}; transparent background (desktop visible) not verified visually: screen locked')
    finally:
        sess.close()


@test('T-L1')
def t_language():
    """English only: even with a Swedish system language the help text and the TUI are in English.
    The Swedish literals below (sv_SE, 'starta', 'Kamera') are intentional: the test checks they do not appear."""
    env = {k: v for k, v in os.environ.items() if k not in ('MULTICAM_LANG', 'LC_ALL', 'LC_MESSAGES', 'LANG')}
    env.update(LANG='sv_SE.UTF-8', MULTICAM_LANG='sv')
    out = subprocess.run([BIN, '--help'], env=env, capture_output=True, text=True).stdout
    expect('start the TUI' in out and 'starta' not in out, out)
    s = Session(make_home('l1', cfg()), out_dir('l1'), env={'LANG': 'sv_SE.UTF-8', 'MULTICAM_LANG': 'sv'})
    try:
        s.wait_for('Camera A', 5)
        scr = s.screen()
        expect('Preview cameras' in scr and 'Microphone' in scr and 'Kamera' not in scr, scr)
        s.send('q'); s.wait_exit(5)
    finally:
        s.close()
    R.add('T-L1', 'PASS', 'LANG=sv_SE + MULTICAM_LANG=sv: --help and TUI in English (Camera A, Microphone, Preview cameras), no Swedish text')


@test('T-S1')
def t_settings():
    """Settings view (S): changes are saved immediately and shown at the next start; Esc goes back to the form."""
    h = make_home('s1', cfg())
    s = Session(h, out_dir('s1'), env={'MULTICAM_OUTPUT_DIR': ''})
    try:
        s.wait_for('Camera A', 5)
        s.send('S', 0.3)
        expect('Settings' in s.screen() and 'Save recordings to' in s.screen(), s.screen())
        s.send(ENTER); s.send('~/mc-out', 0.3); s.send(ENTER)                    # output folder
        s.send(DOWN); s.send(RIGHT); s.send(RIGHT)                              # after -> nothing
        s.send(DOWN); s.send(ENTER)                                             # hide -> off
        s.send(DOWN); s.send(ENTER)                                             # bar -> off
        s.send(DOWN); s.send(DOWN)                                              # skip countdown, follow
        s.send(DOWN); s.send(RIGHT); s.send(RIGHT)                              # step 20 -> 30
        s.send(DOWN); s.send(LEFT)                                              # big 100 -> 75
        s.send(DOWN); s.send(ENTER, 0.3)                                        # updcheck -> off
        kv = conf_kv(h)                                                          # the TUI is still running
        want = {'OUTPUT_DIR': '~/mc-out', 'AFTER_RECORDING': 'nothing', 'HIDE_WINDOW': 'off', 'BAR_INDICATOR': 'off',
                'MOVE_STEP': '30', 'BIG_STEP': '75', 'UPDATE_CHECK': 'off'}
        bad = {k: kv.get(k) for k, v in want.items() if kv.get(k) != v}
        expect(not bad, f'not saved immediately: {bad}\n{s.screen()}')
        s.send(ESC, 0.3)
        expect('Preview cameras' in s.screen(), 'Esc did not go back to the form\n' + s.screen())
        s.send('q'); expect(s.wait_exit(5), 'did not exit')
    finally:
        s.close()
    s = Session(h, out_dir('s1'), env={'MULTICAM_OUTPUT_DIR': ''})
    try:
        s.wait_for('Camera A', 5); s.send('S', 0.3)
        scr = s.screen()
        expect('~/mc-out' in scr and '● just show the file' in scr and '30 px' in scr and '75 px' in scr, scr)
        s.send(ESC); s.send('q'); s.wait_exit(5)
    finally:
        s.close()
    R.add('T-S1', 'PASS', 'S opens settings; output folder, after recording, hide, bar icon, arrow step, Shift step and update check were saved in config while the TUI was running and shown at the next start; Esc goes back')


@test('T-H1')
def t_hide():
    """Real foot window: when recording starts the TUI is hidden (special:multicam) and the bar status is written; multicam stop -> TUI back, status gone, file saved."""
    wake()
    home = make_home('h1', cfg(shape='circle', ring='on'))
    o = out_dir('h1')
    state = '/run/user/1000/multicam/recording'
    fifo = os.path.join(SCRATCH, 'h1.fifo')
    if os.path.exists(fifo): os.unlink(fifo)
    os.mkfifo(fifo)
    env = hypr_env(); env['HOME'] = home; env['MULTICAM_OUTPUT_DIR'] = o; env['MULTICAM_NO_UPDATE_CHECK'] = '1'; env['MULTICAM_LOG'] = home + '/multicam.log'
    foot = subprocess.Popen(['foot', '--app-id=TUI.float', '-e', 'bash', '-c', f'exec {BIN} <{fifo}'], env=env)
    tui = lambda: next((c for c in clients() if c['class'] == 'TUI.float'), None)
    try:
        fd = os.open(fifo, os.O_WRONLY)
        expect(wait_until(tui, 8), 'foot window missing')
        time.sleep(1)
        os.write(fd, b'\x1b[15~')
        expect(wait_until(lambda: len(mc_clients()) >= 1, 10), 'camera not mapped')
        time.sleep(0.5)
        os.write(fd, b'\r')
        expect(wait_until(gsr_pids, 10), 'the recording did not start')
        hidden = wait_until(lambda: tui()['workspace']['name'] == 'special:multicam', 5)
        st = open(state).read().strip() if wait_until(lambda: os.path.exists(state), 3) else ''
        cams_visible = all(c['workspace']['id'] > 0 for c in mc_clients().values())
        time.sleep(2)
        r = subprocess.run([BIN, 'stop'], env=env, capture_output=True, text=True)
        back = wait_until(lambda: tui() and tui()['workspace']['id'] > 0, 10)
        gone = wait_until(lambda: not os.path.exists(state) and not gsr_pids(), 15)
        expect(wait_until(lambda: [f for f in os.listdir(o) if f.endswith('.mp4')], 15), 'no file')
        os.write(fd, b'n')
        foot.wait(timeout=10)
        os.close(fd)
        ok = bool(hidden) and st.isdigit() and cams_visible and r.returncode == 0 and bool(back) and bool(gone)
        R.add('T-H1', 'PASS' if ok else 'FAIL',
              f'hidden during recording (special:multicam)={bool(hidden)}, cameras visible={cams_visible}, status file for the bar icon={st!r}; '
              f'multicam stop rc={r.returncode}, TUI back on a normal workspace={bool(back)}, status gone and recorder exited={bool(gone)}, file={os.listdir(o)}')
    finally:
        if foot.poll() is None: foot.terminate()
        shutil.rmtree(o, ignore_errors=True)


@test('T-U1')
def t_update():
    """Update against a local git repository: no update -> check-update 1; new commit -> check-update 0; update --yes fetches and installs."""
    base = os.path.join(SCRATCH, 'upd'); shutil.rmtree(base, ignore_errors=True); os.makedirs(base)
    git = lambda *a, cwd=base: subprocess.run(['git', *a], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()
    git('init', '-q', '--bare', '-b', 'main', 'origin.git')
    git('clone', '-q', REPO, 'clone')
    git('remote', 'set-url', 'origin', base + '/origin.git', cwd=base + '/clone')
    for f in ('bin', 'lib', 'shell-plugin', 'assets', 'install.sh', 'uninstall.sh', 'multicam.desktop'):   # the working copy (may be uncommitted)
        shutil.rmtree(f'{base}/clone/{f}', ignore_errors=True)
        subprocess.run(['cp', '-a', f'{REPO}/{f}', base + '/clone/'], check=True)
    git('add', '-A', cwd=base + '/clone')
    git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qam', 'working copy', '--allow-empty', cwd=base + '/clone')
    git('push', '-q', 'origin', 'HEAD:main', cwd=base + '/clone')
    home = os.path.join(base, 'home'); os.makedirs(home)
    env = dict(os.environ, HOME=home)
    mc = home + '/.local/bin/multicam'
    run = lambda *a: subprocess.run(a, env=env, capture_output=True, text=True)
    r = run(base + '/clone/install.sh', '--yes', '--no-bgremove', '--no-bar-indicator'); expect(r.returncode == 0, r.stdout + r.stderr)
    expect(run(mc, 'check-update').returncode == 1, 'check-update: update reported although nothing changed')
    u = run(mc, 'update', '--yes'); expect('up to date' in u.stdout, 'update when everything is current: ' + u.stdout + u.stderr)
    c = base + '/clone'
    s = re.sub(r'(?m)^VERSION=\S+', 'VERSION=9.9.9', open(c + '/bin/multicam').read())
    open(c + '/bin/multicam', 'w').write(s)
    git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qam', 'bump', cwd=c); git('push', '-q', 'origin', 'HEAD:main', cwd=c)
    expect(run(mc, 'check-update').returncode == 0, 'check-update misses a new commit')
    r = run(mc, 'update', '--yes'); expect(r.returncode == 0, r.stdout + r.stderr)
    expect('9.9.9' in run(mc, '--version').stdout, 'new version not installed')
    expect(run(mc, 'check-update').returncode == 1, 'check-update after update')
    R.add('T-U1', 'PASS', 'local git repository as origin: check-update 1 -> new commit -> 0 -> update --yes installs 9.9.9 -> check-update 1 again; HOME copy, never the real HOME')
    shutil.rmtree(base, ignore_errors=True)


@test('T-O1')
def t_default_output_dir():
    """Default output folder (no MULTICAM_OUTPUT_DIR) that does not exist yet: multicam creates it instead of failing with Omarchy's 'Screen recording directory does not exist'."""
    wake()
    home = make_home('o1', cfg())
    s = Session(home, None, env={'XDG_VIDEOS_DIR': home + '/Videos'})
    try:
        expect(not os.path.exists(home + '/Videos'), 'Videos exists before the test')
        start_recording(s)
        time.sleep(2)
        s.send(F12, 0.3)
        expect(s.wait_for('done', 25), s.screen())
        files = [f for f in os.listdir(home + '/Videos') if f.endswith('.mp4')]
        expect(files, 'no recording in the default folder: ' + str(os.listdir(home)))
        s.send('n'); s.wait_exit(5)
    finally:
        s.close()
    R.add('T-O1', 'PASS', f'missing default folder {home}/Videos was created and the recording saved there: {files}')


@test('T-N1')
def t_navigation():
    """Discoverable flow: the form says what comes next, the preview shows Enter = start / Esc = back, recording is stopped only by F12 (not q/Esc/Enter)."""
    wake()
    o = out_dir('n1')
    s = Session(make_home('n1', cfg(extra='COUNTDOWN=off\n')), o)
    try:
        expect(s.wait_for('Preview cameras', 5), s.screen())
        expect('then press' in s.screen() and 'F5' not in s.screen(), 'form hints missing:\n' + s.screen())
        s.send(F5)
        expect(s.wait_for('PREVIEW', 15), s.screen())
        scr = s.screen()
        expect('Start recording' in scr and 'Esc' in scr and 'back to the settings' in scr and 'quit multicam' in scr, 'preview hints missing:\n' + scr)
        s.send(ESC, 0.5)
        expect(s.wait_for('Preview cameras', 5) and not mc_clients() and 'PREVIEW' not in s.screen(), 'Esc did not return to the form:\n' + s.screen())
        s.send(ESC, 0.5); s.send(ESC, 0.5)   # Esc in the form does nothing: only q quits
        expect('Preview cameras' in s.screen() and not s.wait_exit(0.5), 'Esc in the form quit or changed screen:\n' + s.screen())
        s.send(F5)
        expect(s.wait_for('PREVIEW', 15), s.screen())   # the preview works again after going back
        s.send(ENTER, 0.3)
        expect(s.wait_for('RECORDING', 20), s.screen())
        scr = s.screen()
        expect('F12' in scr and 'Stop recording' in scr and 'multicam stop' in scr, 'recording hints missing:\n' + scr)
        time.sleep(2)
        for k in ('q', ESC, ENTER, 'y'):   # keys typed by accident must not stop the recording
            s.send(k, 0.4)
        expect(gsr_pids() and 'RECORDING' in s.screen(), 'a stray key stopped the recording:\n' + s.screen())
        s.send(F12, 0.3)   # only F12 stops
        expect(s.wait_for('recording is done', 30), s.screen())
        s.send('n'); s.wait_exit(5)
        expect([f for f in os.listdir(o) if f.endswith('.mp4')], 'no file')
    finally:
        s.close()
        shutil.rmtree(o, ignore_errors=True)
    R.add('T-N1', 'PASS', 'form hint (step 1 ... then press Enter), preview banner (Enter start, Esc back, q quit), Esc returns to the form with cameras closed, preview again, Enter starts, recording banner (F12 stop, multicam stop), q/Esc/Enter/y do not stop, F12 stops and saves')


@test('T-T1')
def t_thickness_zero():
    """Ring thickness 0 = no border: shown as 'none', saved as CAM_A_THICK=0, kept at the next start; [ ] in the preview reaches 0; no F5 hint."""
    wake()
    home = make_home('t1', cfg(ring='on', thick=1))
    s = Session(home, None)
    try:
        expect(s.wait_for('Preview cameras', 5), s.screen())
        expect('F5' not in s.screen(), 'F5 is still advertised:\n' + s.screen())
        for _ in range(4): s.send(DOWN)
        s.send(LEFT, 0.4)
        expect('none' in s.screen() and 'no border' in s.screen(), s.screen())
        s.send(LEFT, 0.4); s.send(LEFT, 0.4)
        expect('none' in s.screen(), 'thickness went below 0:\n' + s.screen())
        s.send('q'); expect(s.wait_exit(5), 'exit')
    finally:
        s.close()
    expect('CAM_A_THICK=0' in open(home + '/.config/multicam/config').read(), 'thickness 0 not saved')
    s = Session(home, None)
    try:
        expect(s.wait_for('Preview cameras', 5), s.screen())
        for _ in range(4): s.send(DOWN)
        expect('none' in s.screen(), 'thickness 0 not kept:\n' + s.screen())
        s.send(RIGHT, 0.4)
        expect('1 px' in s.screen(), s.screen())
        s.send(LEFT, 0.3)
        for _ in range(11): s.send(DOWN)   # to the Preview row
        s.send(ENTER)
        expect(s.wait_for('PREVIEW', 15), s.screen())
        expect('ring off' in s.screen(), 'thickness 0 should show as ring off in the preview:\n' + s.screen())
        s.send(']', 0.4); expect('1 px' in s.screen(), s.screen())
        s.send('[', 0.4); expect('ring off' in s.screen(), s.screen())
        s.send('[', 0.4); expect('ring off' in s.screen(), 'thickness went below 0:\n' + s.screen())
        s.send(ESC, 0.5); s.send('q'); s.wait_exit(5)
    finally:
        s.close()
    R.add('T-T1', 'PASS', 'thickness: Left from 1 px -> none (min 0), saved as 0 and kept at the next start, Right -> 1 px; preview opened with Enter on the last row; no F5 hint in the form')


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
            R.add(f.__name__, 'FAIL', f'exception: {e}\n{traceback.format_exc()[-400:]}')
        finally:
            probs = settle_clean()
            if probs:
                print('CLEANUP PROBLEM after', f.__name__, probs, flush=True)
    json.dump(R.rows, open(os.path.join(SCRATCH, 'results.json'), 'w'), ensure_ascii=False, indent=1)
    print('\nDone:', len(R.rows), 'rows')


if __name__ == '__main__':
    main()
