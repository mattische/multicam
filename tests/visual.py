#!/usr/bin/env python3
"""Visual tests (require an unlocked screen; a human/agent must look at the PNG files in $SCRATCH/evidence/; they are never committed because they show the camera image and the screen).
Run: tests/visual.py [shapes|record|bg|tui]. Writes downscaled PNGs and prints what was saved."""
import sys
from mclib import *

E = os.path.join(SCRATCH, 'evidence') + '/'
os.makedirs(E, exist_ok=True)


def crop_save(name, g, margin=20, width=320):
    grim('/tmp/claude-1000/crop.png', geometry=f'{g[0] - margin},{g[1] - margin} {g[2] + 2 * margin}x{g[3] + 2 * margin}')
    sh(f'ffmpeg -y -v error -i /tmp/claude-1000/crop.png -vf scale={width}:-1 {E}{name}.png')


def shapes():
    cases = [('circle', 'on', '#ff0000', 8, 'd1-circle-ring-red8'), ('rect', 'on', '#00ff00', 8, 'd1-rect-ring-green8'),
             ('circle', 'off', '#0000ff', 8, 'd1-circle-noring'), ('circle', 'on', '#ffee00', 2, 'd2-circle-thick2'),
             ('circle', 'on', '#ffee00', 12, 'd2-circle-thick12')]
    for shape, ring, col, th, name in cases:
        s = Session(make_home('vis', cfg(shape=shape, ring=ring, color=col, size=300, thick=th) + 'CAM_A_RX=300\nCAM_A_RY=300\n'), out_dir('vis'))
        try:
            start_to_preview(s); wait_until(lambda: 'MulticamA' in geo(), 5); time.sleep(1.5)
            crop_save(name, geo()['MulticamA'])
            print('saved', name)
            s.send('q'); s.wait_exit(5)
        finally:
            s.close()


def record():
    o = out_dir('vc')
    conf = cfg(shape='circle', ring='on', size=260) + 'CAM_A_RX=100\nCAM_A_RY=500\n' + CAM_B_CFG + 'CAM_B_SHAPE=rect\nCAM_B_RING=on\nCAM_B_COLOR=#00aaff\nCAM_B_SIZE=200\nCAM_B_RX=500\nCAM_B_RY=500\n'
    s = Session(make_home('vc', conf), o)
    try:
        start_to_preview(s); wait_until(lambda: len(geo()) == 2, 8)
        mon = [m for m in monitors() if m['focused']][0]
        L = int(mon['width'] / mon['scale'])
        s.send(ENTER, 0.3); s.wait_for('RECORDING', 15); time.sleep(3)
        grim('/tmp/claude-1000/bar.png', geometry=f"{mon['x']},{mon['y']} {L}x34")
        sh('omarchy-capture-screenrecording --stop-recording')
        s.wait_for('recording is done', 25); time.sleep(1)
        grim('/tmp/claude-1000/bar2.png', geometry=f"{mon['x']},{mon['y']} {L}x34")
        fp = os.path.join(o, [x for x in os.listdir(o) if x.endswith('.mp4')][0])
        for t, n in [('0.2', 'c1-frame-0.2s'), ('4', 'x1-frame-4s')]:
            sh(f'ffmpeg -y -v error -ss {t} -i "{fp}" -frames:v 1 -vf scale=800:-1 {E}{n}.png')
        for f, n in [('bar', 'e3-bar'), ('bar2', 'e3-bar2')]:
            sh(f'ffmpeg -y -v error -i /tmp/claude-1000/{f}.png -vf "crop=700:34:in_w/2-350:0,scale=1400:-1" {E}{n}.png')
        print('saved c1-frame-0.2s, x1-frame-4s, e3-bar (during recording), e3-bar2 (after stop)')
        s.send('n'); s.wait_exit(5)
    finally:
        s.close(); shutil.rmtree(o, ignore_errors=True)


def bg():
    home = sys.argv[2] if len(sys.argv) > 2 else os.path.join(SCRATCH, 'mc-home-f')
    open(home + '/.config/multicam/config', 'w').write(cfg(shape='rect', ring='off', size=400).replace('CAM_A_BG=off', 'CAM_A_BG=on') + 'CAM_A_RX=300\nCAM_A_RY=300\n')
    s = Session(home, out_dir('fbg'))
    try:
        start_to_preview(s); wait_until(lambda: 'MulticamA' in geo() and len(own_mpv_for_multicam()) >= 2, 15); time.sleep(4)
        crop_save('f2-bg-transparent', geo()['MulticamA'], 30, 480)
        print('saved f2-bg-transparent')
        s.send('q'); s.wait_exit(5)
    finally:
        s.close()


def tui():
    """Real terminal via omarchy-launch-tui + wtype; aborts if focus is not on the TUI window."""
    h = make_home('d7w', cfg(shape='circle', ring='on', size=200) + 'CAM_A_RX=200\nCAM_A_RY=300\n')
    subprocess.Popen(['omarchy-launch-tui', '--app-id=TUI.float', 'env', f'HOME={h}', BIN], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    w = wait_until(lambda: [c for c in clients() if c['class'] == 'TUI.float'], 10)
    time.sleep(1.5)
    addr = w[0]['address']
    try:
        def key(*k):
            assert active_addr() == addr, f'focus not on TUI before {k}'
            subprocess.run(['wtype'] + list(k)); time.sleep(0.5)
        key('-k', 'F5'); wait_until(lambda: 'MulticamA' in geo(), 10); time.sleep(1)
        res = [('after camera start', active_addr() == addr)]
        for n, k in [('right', ('-k', 'Right')), ('down', ('-k', 'Down')), ('s', ('s',)), ('r', ('r',)), ('PgUp', ('-k', 'Page_Up')), ('1', ('1',)), ('m', ('m',)), ('up', ('-k', 'Up'))]:
            key(*k); res.append((n, active_addr() == addr))
        print(res)
        key('q'); time.sleep(1.5)
    finally:
        for c in clients():
            if c['class'] == 'TUI.float' and c['address'] == addr:
                sh(f"hyprctl dispatch 'hl.dsp.window.close({{ window = \"address:{addr}\" }})'")


if __name__ == '__main__':
    wake()
    for n in (sys.argv[1:2] or ['shapes', 'record', 'tui']):
        globals()[n]()
