#!/usr/bin/env python3
"""Tests for the 1.4 features: countdown before recording (F-C*) and window capture that follows the window (F-F*).
Run: tests/features.py [F-ID ...]  (no arguments: all). Temporary files only in $SCRATCH; frames are sampled as single
pixel values and never saved."""
import sys
from mclib import *

os.makedirs(SCRATCH, exist_ok=True)
R = Report()
TESTS = {}


def test(*ids):
    def deco(f):
        for i in ids:
            TESTS[i] = f
        TESTS.setdefault('_order', []).append(f)
        return f
    return deco


def expect(cond, msg):
    if not cond:
        raise AssertionError(msg)


def conf_kv(home):
    return dict(l.split('=', 1) for l in open(os.path.join(home, '.config/multicam/config')).read().splitlines() if '=' in l)


def stop_and_finish(s, tmo=60):
    s.send(F12, 0.3)
    expect(s.wait_for('recording is done', tmo), 'no result:\n' + s.screen())
    s.send('n'); s.wait_exit(5)


def leftovers():
    p = []
    if mc_clients(): p.append(f'windows: {list(mc_clients())}')
    if own_mpv_for_multicam(): p.append(f'processes: {own_mpv_for_multicam()}')
    if gsr_pids(): p.append('gpu-screen-recorder still running')
    w = sh("pgrep -af -- '--watch /run/user/1000/multicam'").stdout.strip()
    if w: p.append(f'watcher: {w}')
    ff = sh("pgrep -af 'ffmpeg.*-follow.mp4'").stdout.strip()
    if ff: p.append(f'ffmpeg: {ff}')
    return p


# ---------------------------------------------------------------- countdown
@test('F-C1')
def t_countdown_setting():
    """Settings view: Countdown and Follow window are saved immediately and shown at the next start."""
    h = make_home('fc1', cfg())
    s = Session(h, out_dir('fc1'))
    try:
        s.wait_for('Camera A', 5)
        s.send('S', 0.3)
        scr = s.screen()
        expect('Countdown' in scr and '● 3 s' in scr and 'Follow window' in scr, scr)
        for _ in range(4): s.send(DOWN, 0.1)
        s.send(RIGHT, 0.3)
        kv = conf_kv(h); expect(kv.get('COUNTDOWN') == '5', f'COUNTDOWN={kv.get("COUNTDOWN")}')
        s.send(RIGHT, 0.2); s.send(RIGHT, 0.3)
        kv = conf_kv(h); expect(kv.get('COUNTDOWN') == 'off', f'COUNTDOWN={kv.get("COUNTDOWN")} (3 -> 5 -> 10 -> off)')
        s.send(LEFT, 0.3)
        s.send(DOWN, 0.1); s.send(ENTER, 0.3)
        kv = conf_kv(h); expect(kv.get('COUNTDOWN') == '10' and kv.get('FOLLOW_WINDOW') == 'off', str(kv))
        s.send(ESC, 0.3); s.send('q'); expect(s.wait_exit(5), 'did not quit')
    finally:
        s.close()
    s = Session(h, out_dir('fc1'))
    try:
        s.wait_for('Camera A', 5); s.send('S', 0.3)
        scr = s.screen()
        cd = [l for l in scr.splitlines() if 'Countdown' in l]
        fw = [l for l in scr.splitlines() if 'Follow window' in l]
        expect(cd and '● 10 s' in cd[0] and fw and '○ off' in fw[0], scr)
        s.send(ESC); s.send('q'); s.wait_exit(5)
    finally:
        s.close()
    R.add('F-C1', 'PASS', 'settings: Countdown 3 -> 5 -> 10 -> off -> 10 and Follow window on -> off written to config at once '
          '(COUNTDOWN=10, FOLLOW_WINDOW=off) and shown at the next start')


@test('F-C2')
def t_countdown_cancel():
    """Countdown shows big digits and the seconds left; Esc cancels back to the preview, nothing is recorded."""
    wake()
    s = Session(make_home('fc2', cfg(extra='COUNTDOWN=5\n')), out_dir('fc2'))
    try:
        start_to_preview(s)
        s.send(ENTER, 0.2)
        expect(s.wait_for('Recording starts in 5 s', 3), s.screen())
        scr = s.screen()
        big = sum(1 for l in scr.splitlines() if '████' in l)
        expect(big >= 5, f'no big digits ({big} lines):\n{scr}')
        expect(s.wait_for('Recording starts in 4 s', 2.5), 'the countdown does not tick:\n' + s.screen())
        t = time.time()
        s.send(ESC, 0.3)
        expect(s.wait_for('Countdown cancelled', 3) and 'PREVIEW' in s.screen(), s.screen())
        time.sleep(max(0, 5.5 - (time.time() - t)))   # past the end of the cancelled countdown
        none = not gsr_pids()
        expect(none and 'PREVIEW' in s.screen(), f'recording started after Esc (gsr={gsr_pids()})')
        # q also cancels
        s.send(ENTER, 0.2); expect(s.wait_for('Recording starts in', 3), s.screen())
        s.send('q', 0.3); expect(s.wait_for('Countdown cancelled', 3), s.screen())
        time.sleep(1); expect(not gsr_pids(), 'recording started after q')
        s.send('q'); s.wait_exit(5)
        R.add('F-C2', 'PASS', f'Enter -> "Recording starts in 5 s" with {big} lines of big block digits, ticks to 4 s; Esc and q cancel back '
              'to PREVIEW ("Countdown cancelled"), no gpu-screen-recorder 5.5 s after Enter')
    finally:
        s.close()


def time_to_record(name, countdown):
    wake()
    o = out_dir(name)
    s = Session(make_home(name, cfg(extra=f'COUNTDOWN={countdown}\n')), o)
    try:
        start_to_preview(s)
        time.sleep(0.5)
        t = time.time()
        s.send(ENTER, 0)
        expect(wait_until(gsr_pids, 15, 0.02), 'recording did not start:\n' + s.screen())
        dt = time.time() - t
        expect(s.wait_for('RECORDING', 10), s.screen())
        time.sleep(1)
        stop_and_finish(s)
        files = [f for f in os.listdir(o) if f.endswith('.mp4')]
        return dt, files
    finally:
        s.close()
        shutil.rmtree(o, ignore_errors=True)


@test('F-C3')
def t_countdown_timing():
    dt, files = time_to_record('fc3', 3)
    ok = 3.0 <= dt <= 4.5 and len(files) == 1
    R.add('F-C3', 'PASS' if ok else 'FAIL', f'COUNTDOWN=3: Enter -> gpu-screen-recorder after {dt:.2f} s (expected 3.0-4.5: 3 s + the start script, see F-C4); file: {files}')


@test('F-C4')
def t_countdown_off():
    dt, files = time_to_record('fc4', 'off')
    ok = dt < 1.5 and len(files) == 1
    R.add('F-C4', 'PASS' if ok else 'FAIL', f'COUNTDOWN=off: Enter -> gpu-screen-recorder after {dt:.2f} s (expected < 1.5); file: {files}')


# ---------------------------------------------------------------- follow window
def picker_stub(rect):
    d = os.path.join(SCRATCH, 'fpickstub'); os.makedirs(d, exist_ok=True)
    open(d + '/omarchy-capture-region', 'w').write(f'#!/bin/bash\necho "{rect}"\n')
    os.chmod(d + '/omarchy-capture-region', 0o755)
    return d


def pixel(f, t, x, y):
    """RGB of one pixel at time t (nothing is written to disk)."""
    r = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', f, '-frames:v', '1', '-vf', f'crop=2:2:{x}:{y},format=rgb24',
                        '-f', 'rawvideo', '-'], capture_output=True)
    return tuple(r.stdout[:3]) if len(r.stdout) >= 3 else None


def green(p):
    return p is not None and p[1] > 120 and p[0] < 90 and p[2] < 90


def hd(cmd):
    return sh(['hyprctl', 'dispatch', cmd])


def follow_case(tid, close=False):
    wake()
    # Omarchy's screensaver is a fullscreen window that would cover the test window (it ends on any input anyway)
    if any(c['class'] == 'org.omarchy.screensaver' for c in clients()):
        sh(['pkill', '-f', '^foot --app-id=org[.]omarchy[.]screensaver']); time.sleep(0.5)
    m = [x for x in monitors() if x['focused']][0]
    sc = m['scale']
    mw, mh = int(m['width'] / sc), int(m['height'] / sc)
    W, H = 500, 400
    x0, y0 = m['x'] + 100, m['y'] + 100
    dx, dy = min(800, mw - W - 200), min(500, mh - H - 200)   # farther than the window size: no overlap with the old rectangle
    sh(['hyprctl', 'eval', f'if MCFT_ == nil then MCFT_ = hl.window_rule({{name="mcft", match={{class="^MCFollowTest$"}}, float=true, pin=true, '
        f'no_anim=true, no_initial_focus=true, tag="-default-opacity", opacity="1 1", border_size=0, size={{{W},{H}}}}}) else MCFT_:set_enabled(true) end'])
    win = subprocess.Popen(['foot', '--app-id=MCFollowTest', '-o', 'colors-dark.background=00c800', '-o', 'colors-dark.alpha=1.0',
                            '-o', 'cursor.blink=no', 'sleep', '120'], env=hypr_env(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    o = out_dir('ff1')
    s = None
    try:
        c = wait_until(lambda: next((x for x in clients() if x['class'] == 'MCFollowTest'), None), 8)
        expect(c, 'test window did not map')
        sel = 'class:^MCFollowTest$'
        hd(f'hl.dsp.window.move({{ window = "{sel}", x = {x0}, y = {y0} }})')
        c = wait_until(lambda: next((x for x in clients() if x['class'] == 'MCFollowTest' and x['at'] == [x0, y0]), None), 3)
        expect(c and c['size'] == [W, H], f'test window geometry: {c and (c["at"], c["size"])}')
        d = picker_stub(f'{x0},{y0} {W}x{H}')
        s = Session(make_home('ff1', cfg(shape='circle', size=120, extra='CAPTURE=window\nCOUNTDOWN=off\nFOLLOW_WINDOW=on\n'
                                         'CAM_A_ARX=20\nCAM_A_ARY=20\nCAM_A_ASIZE=120\n')),
                    o, env={'PATH': d + ':' + os.environ['PATH']})
        start_to_preview(s)
        expect('follows the window' in s.screen(), s.screen())
        expect(wait_until(lambda: len(geo()) == 1, 8), 'camera missing')
        s.send(ENTER, 0.3)
        expect(wait_until(gsr_pids, 15), 'recording did not start:\n' + s.screen())
        expect(s.wait_for('RECORDING', 10), s.screen())
        args = sh("pgrep -af '^gpu-screen-recorder'").stdout
        time.sleep(2.5)
        g1 = geo()['MulticamA']
        t_move = time.time()
        hd(f'hl.dsp.window.move({{ window = "{sel}", x = {x0 + dx}, y = {y0 + dy} }})')
        moved = wait_until(lambda: geo().get('MulticamA', g1)[:2] == (g1[0] + dx, g1[1] + dy), 3, 0.05)
        lag = time.time() - t_move
        g2 = geo()['MulticamA']
        if close:   # window closed mid-recording: the crop keeps its last position, the recording goes on
            time.sleep(1); win.terminate(); win.wait(3)
            expect(wait_until(lambda: not any(x['class'] == 'MCFollowTest' for x in clients()), 3), 'test window still open')
        time.sleep(2.5)
        t0 = time.time()
        s.send(F12, 0.3)
        seen = s.wait_for('Processing', 30)
        pct = re.findall(r'Processing…\s+(\d+) %', s.screen())
        expect(s.wait_for('recording is done', 120), 'no result:\n' + s.screen())
        failed = 'Following the window failed' in s.screen()
        proc = time.time() - t0
        s.send('n'); s.wait_exit(5)
        files = [f for f in os.listdir(o) if f.endswith('.mp4')]
        expect(len(files) == 1, f'files: {os.listdir(o)}')
        f = os.path.join(o, files[0])
        j = json.loads(sh(f'ffprobe -v error -show_entries stream=codec_type,codec_name,width,height:format=duration -of json "{f}"').stdout)
        v = [x for x in j['streams'] if x['codec_type'] == 'video'][0]
        dur = float(j['format']['duration'])
        ew, eh = int(W * sc) // 2 * 2, int(H * sc) // 2 * 2
        cx, cy = v['width'] // 2, v['height'] // 2
        before, after = pixel(f, 1.0, cx, cy), pixel(f, dur - 0.8, cx, cy)
        corner = pixel(f, dur - 0.8, v['width'] - 12, v['height'] - 12)
        s = None
        ok = (v['width'], v['height']) == (ew, eh) and green(before) and bool(moved) and seen and not failed and (close or green(after) and green(corner))
        R.add(tid, 'PASS' if ok else 'FAIL', ('window CLOSED 1 s after the move; ' if close else '') +
              f'monitor {m["name"]} scale {sc}; recorder: {args.strip()[:120]}; window {W}x{H} @ {x0},{y0} moved by {dx},{dy} after 2.5 s; '
              f'MP4 {v["width"]}x{v["height"]} {v["codec_name"]} {dur:.1f} s (expected {ew}x{eh}); centre pixel at 1.0 s {before}, '
              f'at {dur - 0.8:.1f} s {after}, bottom-right {corner} (green = window content); camera A {g1[:2]} -> {g2[:2]} '
              f'(delta {g2[0] - g1[0]},{g2[1] - g1[1]}, followed after {lag:.2f} s); "Processing…" shown={seen} (progress {pct[-1] if pct else "-"} %); '
              f'stop -> result in {proc:.1f} s')
        lo = wait_until(lambda: not leftovers(), 5) or leftovers()
        R.add(tid + '(clean)', 'PASS' if lo is True else 'FAIL', f'after the result: {"nothing left (windows, mpv, gsr, watcher, ffmpeg)" if lo is True else lo}')
    finally:
        if s: s.close()
        if win.poll() is None: win.terminate()
        try: win.wait(3)
        except Exception: win.kill()
        sh(['hyprctl', 'eval', 'if MCFT_ then MCFT_:set_enabled(false) end'])
        shutil.rmtree(o, ignore_errors=True)


@test('F-F1')
def t_follow():
    """Window mode + follow: a solid green test window is moved mid-recording; the result is cropped to the window
    (size x scale) and shows the window before and after the move; the camera moves by the same delta."""
    follow_case('F-F1')


@test('F-F2')
def t_follow_closed():
    """As F-F1, but the window is closed during the recording: the result is still cropped (last position), no failure."""
    follow_case('F-F2', close=True)


def main():
    names = sys.argv[1:]
    todo = []
    for f in ([TESTS[n] for n in names if n in TESTS] if names else TESTS.get('_order', [])):
        if f not in todo: todo.append(f)
    for f in todo:
        try:
            f()
        except Exception as e:
            import traceback
            R.add(f.__name__, 'FAIL', f'exception: {e}\n{traceback.format_exc()[-400:]}')
    shutil.rmtree(os.path.join(SCRATCH, 'fpickstub'), ignore_errors=True)
    for n in ('fc1', 'fc2', 'fc3', 'fc4', 'ff1'):
        shutil.rmtree(os.path.join(SCRATCH, 'home-' + n), ignore_errors=True)
        shutil.rmtree(os.path.join(SCRATCH, 'out-' + n), ignore_errors=True)
    print('\nDone:', len(R.rows), 'rows,', sum(1 for r in R.rows if r[1] != 'PASS'), 'not passed')


if __name__ == '__main__':
    main()
